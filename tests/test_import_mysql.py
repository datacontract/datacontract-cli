"""Tests for the MySQL importer, run against a real MySQL container."""

import pytest
import yaml
from testcontainers.mysql import MySqlContainer

from datacontract.data_contract import DataContract
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import ResultEnum

mysql = MySqlContainer("mysql:8")

SEED = [
    """CREATE TABLE orders (
        order_id VARCHAR(36) NOT NULL PRIMARY KEY COMMENT 'The order id',
        order_total DECIMAL(10,2),
        line_count INT NOT NULL,
        ordered_at TIMESTAMP NULL,
        payload JSON
    ) COMMENT='All orders'""",
    "INSERT INTO orders VALUES ('CX-263-DU', 50.00, 2, NOW(), '{\"channel\": \"web\"}')",
    "CREATE TABLE customers (id INT NOT NULL PRIMARY KEY)",
    "CREATE VIEW open_orders AS SELECT order_id FROM orders WHERE line_count > 1",
]


@pytest.fixture(scope="module", autouse=True)
def mysql_container(request):
    mysql.start()
    request.addfinalizer(mysql.stop)
    _seed()


@pytest.fixture(autouse=True)
def credentials(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_MYSQL_USERNAME", mysql.username)
    monkeypatch.setenv("DATACONTRACT_MYSQL_PASSWORD", mysql.password)


def _seed():
    import duckdb

    con = duckdb.connect()
    con.execute("INSTALL mysql; LOAD mysql;")
    con.execute(f"ATTACH '{_connection_string()}' AS seed (TYPE mysql)")
    for statement in SEED:
        con.execute(f"CALL mysql_execute('seed', '{statement.replace(chr(39), chr(39) * 2)}')")
    con.close()


def _connection_string():
    return (
        f"host=127.0.0.1 port={mysql.get_exposed_port(3306)} "
        f"user={mysql.username} password={mysql.password} database={mysql.dbname}"
    )


def _import(**kwargs):
    kwargs.setdefault("database", mysql.dbname)
    kwargs.setdefault("port", mysql.get_exposed_port(3306))
    return DataContract.import_from_source("mysql", "127.0.0.1", **kwargs)


def test_import_mysql():
    result = _import(mysql_table=["orders"])

    expected = f"""
apiVersion: v3.2.0
kind: DataContract
id: my-data-contract
name: My Data Contract
version: 1.0.0
status: draft
servers:
  - server: mysql
    type: mysql
    host: 127.0.0.1
    port: {mysql.get_exposed_port(3306)}
    database: {mysql.dbname}
schema:
  - name: orders
    physicalName: orders
    logicalType: object
    physicalType: table
    description: All orders
    properties:
      - name: order_id
        logicalType: string
        logicalTypeOptions:
          maxLength: 36
        physicalType: varchar(36)
        description: The order id
        required: true
        primaryKey: true
        primaryKeyPosition: 1
      - name: order_total
        logicalType: number
        physicalType: decimal(10,2)
        customProperties:
          - property: precision
            value: 10
          - property: scale
            value: 2
      - name: line_count
        logicalType: integer
        physicalType: int
        required: true
      - name: ordered_at
        logicalType: timestamp
        physicalType: timestamp
      - name: payload
        logicalType: string
        physicalType: json
    """

    print("Result", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)


def test_imported_contract_passes_test_without_editing():
    """The point of the native import: import, then test, no hand-editing."""
    result = _import(mysql_table=["orders"])

    run = DataContract(data_contract_str=result.to_yaml()).test()

    print(run.pretty())
    assert run.result == ResultEnum.passed


def test_import_mysql_produces_a_valid_contract():
    result = _import()

    assert DataContract(data_contract_str=result.to_yaml()).lint().result == ResultEnum.passed


def test_import_mysql_imports_all_tables_by_default():
    result = _import()

    assert [schema.name for schema in result.schema_] == ["customers", "open_orders", "orders"]


def test_a_view_is_marked_as_one():
    result = _import(mysql_table=["open_orders"])

    assert result.schema_[0].physicalType == "view"


def test_import_mysql_fails_on_an_unknown_table():
    with pytest.raises(DataContractException) as exc_info:
        _import(mysql_table=["does_not_exist"])

    assert "No tables found" in exc_info.value.reason


def test_import_mysql_requires_a_database():
    with pytest.raises(DataContractException) as exc_info:
        DataContract.import_from_source("mysql", "127.0.0.1", database=None)

    assert "database is required" in exc_info.value.reason


def test_import_mysql_requires_a_host():
    with pytest.raises(DataContractException) as exc_info:
        DataContract.import_from_source("mysql", None, database="mydb")

    assert "host is required" in exc_info.value.reason


def test_import_mysql_requires_credentials(monkeypatch):
    monkeypatch.delenv("DATACONTRACT_MYSQL_PASSWORD")

    with pytest.raises(DataContractException) as exc_info:
        _import()

    assert "DATACONTRACT_MYSQL_PASSWORD is not set" in exc_info.value.reason


def test_a_quote_in_the_database_name_is_escaped_for_both_layers(monkeypatch):
    """The statement travels inside a duckdb string literal, which consumes one
    level of quoting before MySQL sees it — escaping once hands MySQL raw quotes."""
    from datacontract.imports import mysql_importer

    executed = []

    class FakeResult:
        description = [("table_name",)]

        def fetchall(self):
            return []

    class FakeCon:
        def sql(self, statement):
            executed.append(statement)
            return FakeResult()

    mysql_importer._query(FakeCon(), "SELECT 1 WHERE table_schema = 'it''s'")

    # duckdb turns '''' back into '', which is what MySQL needs for one quote
    assert "'it''''s'" in executed[0]
