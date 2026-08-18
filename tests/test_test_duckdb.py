"""`type: duckdb` — a DuckDB database file as the data source.

Distinct from `type: local`, which reads *data files* (json/csv/parquet) through
DuckDB: here the database itself is the source and the contract's schema objects
are the tables inside it. ODCS carries the path to the file in the server's
`database` field.
"""

import duckdb
import pytest

from datacontract.data_contract import DataContract
from datacontract.model.run import ResultEnum

CONTRACT = """apiVersion: v3.0.2
kind: DataContract
id: orders-duckdb
name: Orders
version: 1.0.0
status: active
servers:
  - server: production
    type: duckdb
    database: {database}{schema}
schema:
  - name: {table}
    properties:
      - name: order_id
        logicalType: string
        physicalType: VARCHAR
        required: true
        unique: true
      - name: order_total
        logicalType: integer
        physicalType: INTEGER
    quality:
      - type: sql
        description: "The orders table is not empty"
        query: SELECT count(*) FROM {table}
        mustBe: 2
      - type: sql
        description: "No negative order totals, using a duckdb list function"
        query: SELECT count(*) FROM {table} WHERE NOT list_contains([100, 200], order_total)
        mustBe: 0
"""


def _contract(database, table="orders", schema=None):
    return CONTRACT.format(
        database=database,
        table=table,
        schema=f"\n    schema: {schema}" if schema else "",
    )


@pytest.fixture
def duckdb_database(tmp_path):
    """A database file with `main.orders` and a second table in a named schema."""
    database = tmp_path / "orders.duckdb"
    con = duckdb.connect(str(database))
    con.sql("CREATE TABLE orders (order_id VARCHAR NOT NULL, order_total INTEGER)")
    con.sql("INSERT INTO orders VALUES ('order-1', 100), ('order-2', 200)")
    con.sql("CREATE SCHEMA sales")
    con.sql("CREATE TABLE sales.orders (order_id VARCHAR NOT NULL, order_total INTEGER)")
    con.sql("INSERT INTO sales.orders VALUES ('sales-1', 100), ('sales-2', 200)")
    con.close()
    return database


def test_test_duckdb(duckdb_database):
    run = DataContract(data_contract_str=_contract(duckdb_database)).test()

    assert run.result == ResultEnum.passed, [check.reason for check in run.checks if check.reason]
    assert all(check.result == ResultEnum.passed for check in run.checks)


def test_test_duckdb_with_a_named_schema(duckdb_database):
    """`connect()` takes no schema, so both the table lookup and the SQL quality
    rules have to resolve against the schema the contract names."""
    run = DataContract(data_contract_str=_contract(duckdb_database, schema="sales")).test()

    assert run.result == ResultEnum.passed, [check.reason for check in run.checks if check.reason]


def test_test_duckdb_reports_a_failing_quality_rule(duckdb_database):
    contract = _contract(duckdb_database).replace("mustBe: 2", "mustBe: 99")

    run = DataContract(data_contract_str=contract).test()

    assert run.result == ResultEnum.failed
    failed = [check for check in run.checks if check.result == ResultEnum.failed]
    assert any("was 2" in (check.reason or "") for check in failed), [check.reason for check in failed]


def test_test_duckdb_reports_a_missing_column(duckdb_database):
    contract = _contract(duckdb_database).replace(
        "      - name: order_total\n        logicalType: integer\n        physicalType: INTEGER\n",
        "      - name: order_total\n        logicalType: integer\n        physicalType: INTEGER\n"
        "      - name: not_a_column\n        logicalType: string\n",
    )

    run = DataContract(data_contract_str=contract).test()

    assert run.result == ResultEnum.failed
    assert any("not_a_column" in (check.name or "") for check in run.checks)


def test_test_duckdb_without_a_database_is_reported(tmp_path):
    contract = _contract(tmp_path / "unused.duckdb").replace(f"    database: {tmp_path / 'unused.duckdb'}\n", "")

    run = DataContract(data_contract_str=contract).test()

    assert run.result != ResultEnum.passed
    assert any("database" in (check.reason or "") for check in run.checks)


def test_test_duckdb_with_a_missing_file_is_reported(tmp_path):
    run = DataContract(data_contract_str=_contract(tmp_path / "does-not-exist.duckdb")).test()

    assert run.result != ResultEnum.passed
    assert any("duckdb" in (check.reason or "").lower() for check in run.checks)


def test_the_database_can_be_configured(duckdb_database, monkeypatch):
    """`DATACONTRACT_DUCKDB_DATABASE` overrides the contract, like every other
    server type's connection options."""
    monkeypatch.setenv("DATACONTRACT_DUCKDB_DATABASE", str(duckdb_database))

    run = DataContract(data_contract_str=_contract("/does/not/exist.duckdb")).test()

    assert run.result == ResultEnum.passed, [check.reason for check in run.checks if check.reason]


def test_the_schema_can_be_configured(duckdb_database, monkeypatch):
    monkeypatch.setenv("DATACONTRACT_DUCKDB_SCHEMA", "sales")

    run = DataContract(data_contract_str=_contract(duckdb_database)).test()

    assert run.result == ResultEnum.passed, [check.reason for check in run.checks if check.reason]


def test_the_database_is_opened_read_only(duckdb_database):
    """A test reads; it must not be able to change the database it is testing."""
    contract = _contract(duckdb_database).replace(
        "        query: SELECT count(*) FROM orders\n        mustBe: 2",
        "        query: SELECT count(*) FROM orders\n        mustBe: 2\n"
        '      - type: sql\n        description: "an insert is not a query"\n'
        "        query: INSERT INTO orders VALUES ('order-3', 300)\n        mustBe: 0",
    )

    run = DataContract(data_contract_str=contract).test()

    assert run.result == ResultEnum.failed
    con = duckdb.connect(str(duckdb_database), read_only=True)
    try:
        assert con.sql("SELECT count(*) FROM orders").fetchone()[0] == 2
    finally:
        con.close()
