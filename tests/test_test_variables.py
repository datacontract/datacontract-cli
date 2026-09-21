"""``datacontract test`` resolves ``${VAR}`` references when it uses a value; the contract keeps them."""

import duckdb
import pytest
import yaml

from datacontract.data_contract import DataContract
from datacontract.model.run import ResultEnum

CONTRACT = """apiVersion: v3.2.0
kind: DataContract
id: orders-variables
name: Orders
version: 1.0.0
status: active
servers:
  - server: production
    type: duckdb
    database: ${ORDERS_DB}
schema:
  - name: orders
    properties:
      - name: order_id
        logicalType: string
        physicalType: VARCHAR
        required: true
      - name: order_total
        logicalType: integer
        physicalType: INTEGER
    quality:
      - type: sql
        description: The orders table is not empty
        query: SELECT count(*) FROM ${ORDERS_TABLE:-orders}
        mustBe: 2
      - type: sql
        description: No order total above the limit
        query: SELECT count(*) FROM orders WHERE order_total > ${ORDER_TOTAL_LIMIT}
        mustBe: 0
"""


@pytest.fixture
def orders_db(tmp_path) -> str:
    path = str(tmp_path / "orders.duckdb")
    con = duckdb.connect(path)
    con.execute("CREATE TABLE orders (order_id VARCHAR, order_total INTEGER)")
    con.execute("INSERT INTO orders VALUES ('1', 100), ('2', 200)")
    con.close()
    return path


def test_references_in_server_and_queries_are_resolved(orders_db, monkeypatch):
    monkeypatch.setenv("ORDERS_DB", orders_db)
    monkeypatch.delenv("ORDERS_TABLE", raising=False)
    monkeypatch.setenv("ORDER_TOTAL_LIMIT", "500")

    run = DataContract(data_contract_str=CONTRACT).test()

    print(run.pretty())
    assert run.result == ResultEnum.passed
    sql_checks = [c for c in run.checks if c.implementation and "count(*)" in str(c.implementation)]
    assert any("FROM orders WHERE order_total > 500" in str(c.implementation) for c in sql_checks)


def test_unset_server_variable_fails_the_run_with_the_variable_name(orders_db, monkeypatch):
    monkeypatch.delenv("ORDERS_DB", raising=False)
    monkeypatch.setenv("ORDER_TOTAL_LIMIT", "500")

    run = DataContract(data_contract_str=CONTRACT).test()

    print(run.pretty())
    assert run.result == ResultEnum.failed
    failed = [c for c in run.checks if c.result == ResultEnum.failed]
    assert len(failed) == 1
    assert "ORDERS_DB" in failed[0].reason
    assert "server 'production' database" in failed[0].reason


def test_unset_query_variable_fails_only_that_check(orders_db, monkeypatch):
    monkeypatch.setenv("ORDERS_DB", orders_db)
    monkeypatch.delenv("ORDER_TOTAL_LIMIT", raising=False)

    run = DataContract(data_contract_str=CONTRACT).test()

    print(run.pretty())
    assert run.result == ResultEnum.failed
    failed = [c for c in run.checks if c.result == ResultEnum.failed]
    assert len(failed) == 1
    assert "ORDER_TOTAL_LIMIT" in failed[0].reason
    assert sum(1 for c in run.checks if c.result == ResultEnum.passed) > 0


def test_configuration_override_wins_over_a_reference_in_the_contract(orders_db, monkeypatch):
    monkeypatch.delenv("ORDERS_DB", raising=False)
    monkeypatch.setenv("DATACONTRACT_DUCKDB_DATABASE", orders_db)
    monkeypatch.setenv("ORDER_TOTAL_LIMIT", "500")

    run = DataContract(data_contract_str=CONTRACT).test()

    print(run.pretty())
    assert run.result == ResultEnum.passed


def test_export_keeps_the_references(orders_db, monkeypatch):
    monkeypatch.setenv("ORDERS_DB", orders_db)
    monkeypatch.setenv("ORDER_TOTAL_LIMIT", "500")

    data_contract = DataContract(data_contract_str=CONTRACT)
    data_contract.test()
    exported = yaml.safe_load(data_contract.export("odcs"))

    assert exported["servers"][0]["database"] == "${ORDERS_DB}"
    assert (
        exported["schema"][0]["quality"][1]["query"]
        == "SELECT count(*) FROM orders WHERE order_total > ${ORDER_TOTAL_LIMIT}"
    )


@pytest.mark.parametrize("version", ["v3.1.0", "v3.2.0"])
def test_property_and_library_values_resolve_without_changing_yaml(orders_db, monkeypatch, version):
    monkeypatch.setenv("ORDERS_DB", orders_db)
    monkeypatch.setenv("ORDER_TOTAL_LIMIT", "500")
    monkeypatch.setenv("RUNTIME_TABLE", "orders")
    monkeypatch.setenv("RUNTIME_COLUMN", "order_id")
    monkeypatch.setenv("FIRST_ORDER", "1")
    document = yaml.safe_load(CONTRACT)
    document["apiVersion"] = version
    schema = document["schema"][0]
    schema["physicalName"] = "${RUNTIME_TABLE}"
    prop = schema["properties"][0]
    prop["physicalName"] = "${RUNTIME_COLUMN}"
    prop["enum"] = [{"value": "${FIRST_ORDER}"}, {"value": "2"}]
    prop["quality"] = [
        {
            "type": "library",
            "metric": "invalidValues",
            "arguments": {"validValues": ["${FIRST_ORDER}", "2"]},
            "mustBe": 0,
        }
    ]
    schema["quality"][0]["query"] = "SELECT count(*) FROM ${model}"
    contract = DataContract(data_contract_str=yaml.safe_dump(document))
    assert contract.lint().result == ResultEnum.passed
    run = contract.test()
    assert run.result == ResultEnum.passed, run.pretty()
    assert yaml.safe_load(contract.export("odcs")) == document


def test_unset_property_variable_reports_its_path(orders_db, monkeypatch):
    monkeypatch.setenv("ORDERS_DB", orders_db)
    monkeypatch.delenv("MISSING_PHYSICAL_TABLE", raising=False)
    document = yaml.safe_load(CONTRACT)
    document["schema"][0]["physicalName"] = "${MISSING_PHYSICAL_TABLE}"
    run = DataContract(data_contract_str=yaml.safe_dump(document)).test()
    assert run.result == ResultEnum.failed
    failed = [c for c in run.checks if c.result == ResultEnum.failed]
    assert len(failed) == 1
    assert "MISSING_PHYSICAL_TABLE" in failed[0].reason
    assert "schema[0].physicalName" in failed[0].reason
