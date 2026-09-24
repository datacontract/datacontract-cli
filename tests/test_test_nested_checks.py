"""Checks on nested properties run on the servers read through DuckDB."""

import json
from pathlib import Path

import duckdb
import pytest

from datacontract.data_contract import DataContract
from datacontract.model.run import ResultEnum

CONTRACT = """apiVersion: v3.1.0
kind: DataContract
id: nested-orders
version: 1.0.0
status: active
servers:
  - server: production
{server}
schema:
  - name: orders
    physicalType: table
    properties:
      - name: order_id
        logicalType: string
        required: true
      - name: customer
        logicalType: object
        properties:
          - name: email
            logicalType: string
            required: true
          - name: address
            logicalType: object
            properties:
              - name: city
                logicalType: string
                quality:
                  - type: sql
                    query: SELECT COUNT(*) FROM orders WHERE customer.address.city IS NULL
                    mustBe: 0
      - name: items
        logicalType: array
        items:
          logicalType: object
          properties:
            - name: sku
              logicalType: string
              required: true
"""

# The second order violates every nested rule once.
ORDERS = """SELECT * FROM (VALUES
    ('1', {'email': 'a@example.com', 'address': {'city': 'Berlin'}}, [{'sku': 'A'}]),
    ('2', {'email': NULL, 'address': {'city': NULL}}, [{'sku': 'B'}, {'sku': NULL}])
) AS t(order_id, customer, items)"""

NESTED_RULES = {
    ("customer.email", "field_required"),
    ("customer.address.city", "field_quality_sql"),
    ("items[].sku", "field_required"),
}


def _write(tmp_path, file_format, orders=ORDERS):
    if file_format == "delta":
        # written with the deltalake package from ORDERS
        path = Path(__file__).parent / "fixtures/local-delta/data/nested_orders"
        return f"    type: local\n    path: {path}\n    format: delta"
    if file_format == "duckdb":
        path = tmp_path / "orders.duckdb"
        with duckdb.connect(str(path)) as con:
            con.sql(f"CREATE TABLE orders AS {orders}")
        return f"    type: duckdb\n    database: {path}\n    schema: main"
    path = tmp_path / f"orders.{file_format}"
    if file_format == "json":
        rows = duckdb.sql(orders).fetchall()
        keys = ["order_id", "customer", "items"]
        path.write_text("\n".join(json.dumps(dict(zip(keys, row))) for row in rows))
        return f"    type: local\n    path: {path}\n    format: json\n    delimiter: new_line"
    duckdb.sql(f"COPY ({orders}) TO '{path}' (FORMAT parquet)")
    return f"    type: local\n    path: {path}\n    format: parquet"


@pytest.mark.parametrize("file_format", ["parquet", "delta", "duckdb"])
def test_nested_rules_fail_on_the_rows_that_violate_them(tmp_path, file_format):
    run = DataContract(data_contract_str=CONTRACT.format(server=_write(tmp_path, file_format))).test()

    print(run.pretty())
    assert run.result == ResultEnum.failed
    assert {(c.field, c.type) for c in run.checks if c.result in (ResultEnum.failed, ResultEnum.error)} == NESTED_RULES


def test_nested_quality_rules_fail_on_json(tmp_path):
    # JSON Schema validation already rejects a missing required field, so only the quality rule is violated here.
    orders = ORDERS.replace("{'email': NULL,", "{'email': 'b@example.com',").replace("{'sku': NULL}", "{'sku': 'C'}")
    run = DataContract(data_contract_str=CONTRACT.format(server=_write(tmp_path, "json", orders))).test()

    print(run.pretty())
    assert run.result == ResultEnum.failed
    assert {(c.field, c.type) for c in run.checks if c.result in (ResultEnum.failed, ResultEnum.error)} == {
        ("customer.address.city", "field_quality_sql")
    }


def test_rules_on_a_missing_nested_field_name_the_field(tmp_path):
    orders = """SELECT * FROM (VALUES
        ('1', {'address': {'city': 'Berlin'}}, [{'sku': 'A'}])
    ) AS t(order_id, customer, items)"""
    run = DataContract(data_contract_str=CONTRACT.format(server=_write(tmp_path, "duckdb", orders))).test()

    email_required = next(c for c in run.checks if c.field == "customer.email" and c.type == "field_required")
    assert email_required.result == ResultEnum.failed
    assert email_required.reason == "Column 'customer.email' not found"


def test_nested_rules_fail_on_iceberg(tmp_path, monkeypatch):
    pytest.importorskip("sqlalchemy")
    from pyiceberg.catalog import load_catalog

    uri = f"sqlite:///{tmp_path}/catalog.db"
    warehouse = f"file://{tmp_path}/warehouse"
    catalog = load_catalog("test", type="sql", uri=uri, warehouse=warehouse)
    catalog.create_namespace("sales")
    orders = duckdb.sql(ORDERS).to_arrow_table()
    catalog.create_table("sales.orders", schema=orders.schema).append(orders)
    monkeypatch.setenv("DATACONTRACT_ICEBERG_CATALOG_TYPE", "sql")
    server = (
        f"    type: iceberg\n    catalog: test\n    catalogUrl: {uri}\n    warehouse: {warehouse}\n    namespace: sales"
    )

    run = DataContract(
        data_contract_str=CONTRACT.replace("apiVersion: v3.1.0", "apiVersion: v3.2.0").format(server=server)
    ).test()

    print(run.pretty())
    assert {(c.field, c.type) for c in run.checks if c.result in (ResultEnum.failed, ResultEnum.error)} == NESTED_RULES


def test_types_warn_on_parquet(tmp_path):
    run = DataContract(data_contract_str=CONTRACT.format(server=_write(tmp_path, "parquet"))).test()

    warnings = [c for c in run.checks if c.result == ResultEnum.warning]
    assert {c.field for c in warnings} == {
        "order_id",
        "customer",
        "customer.email",
        "customer.address",
        "customer.address.city",
        "items",
        "items[].sku",
    }
    assert all(c.type == "field_type" for c in warnings)
    assert all(c.reason == "Checking types in parquet files is not supported yet." for c in warnings)
