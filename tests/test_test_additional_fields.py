"""A schema with the custom property `additionalProperties: false` fails on data with fields it does not declare."""

import pytest

from datacontract.data_contract import DataContract
from datacontract.model.run import ResultEnum

PROPERTIES = """      - name: order_id
        logicalType: string
      - name: quantity
        logicalType: integer"""


def _contract(
    path, file_format, switch="\n    customProperties:\n      - property: additionalProperties\n        value: false"
):
    return f"""apiVersion: v3.2.0
kind: DataContract
id: orders
name: orders
version: 1.0.0
status: active
servers:
  - server: local
    type: local
    format: {file_format}
    path: {path}
schema:
  - name: orders{switch}
    properties:
{PROPERTIES}
"""


def _csv(tmp_path, header):
    data = tmp_path / "orders.csv"
    data.write_text(f"{header}\nA1|3\n" if header.count("|") == 1 else f"{header}\nA1|3|x\n")
    return data


def _check(run):
    return next(c for c in run.checks if c.type == "model_no_additional_fields")


def test_a_field_the_contract_does_not_declare_fails(tmp_path):
    run = DataContract(data_contract_str=_contract(_csv(tmp_path, "order_id|quantity|note"), "csv")).test()
    print(run.pretty())
    check = _check(run)
    assert check.result == ResultEnum.failed
    assert check.reason == "Fields not in the contract: note"
    assert check.diagnostics["additional_fields"] == ["note"]
    assert [c.type for c in run.checks if c.result != ResultEnum.passed] == ["model_no_additional_fields"]


def test_exactly_the_declared_fields_pass(tmp_path):
    run = DataContract(data_contract_str=_contract(_csv(tmp_path, "order_id|quantity"), "csv")).test()
    assert _check(run).result == ResultEnum.passed
    assert run.result == ResultEnum.passed


def test_field_names_compare_case_insensitively(tmp_path):
    run = DataContract(data_contract_str=_contract(_csv(tmp_path, "ORDER_ID|Quantity"), "csv")).test()
    assert _check(run).result == ResultEnum.passed


def test_without_the_custom_property_additional_fields_are_allowed(tmp_path):
    run = DataContract(data_contract_str=_contract(_csv(tmp_path, "order_id|quantity|note"), "csv", switch="")).test()
    assert not [c for c in run.checks if c.type == "model_no_additional_fields"]
    assert run.result == ResultEnum.passed


@pytest.mark.parametrize("value", ["'false'", "False"])
def test_the_value_may_be_text(tmp_path, value):
    switch = f"\n    customProperties:\n      - property: additionalProperties\n        value: {value}"
    run = DataContract(data_contract_str=_contract(_csv(tmp_path, "order_id|quantity|note"), "csv", switch)).test()
    assert _check(run).result == ResultEnum.failed


def test_a_json_record_with_an_undeclared_key_fails(tmp_path):
    data = tmp_path / "orders.json"
    data.write_text('[{"order_id": "A1", "quantity": 3, "note": "x"}]')
    run = DataContract(data_contract_str=_contract(data, "json")).test()
    assert _check(run).reason == "Fields not in the contract: note"


def test_the_check_reads_no_rows(tmp_path):
    contract = _contract(_csv(tmp_path, "order_id|quantity|note"), "csv")
    run = DataContract(data_contract_str=contract, metadata_only=True).test()
    assert _check(run).result == ResultEnum.failed


def test_a_database_table_with_an_undeclared_column_fails(tmp_path):
    import duckdb

    database = tmp_path / "orders.duckdb"
    with duckdb.connect(str(database)) as con:
        con.sql("CREATE TABLE orders (order_id VARCHAR, quantity INTEGER, note VARCHAR)")
        con.sql("INSERT INTO orders VALUES ('A1', 3, 'x')")
    contract = _contract(tmp_path, "csv").replace(
        f"    type: local\n    format: csv\n    path: {tmp_path}", f"    type: duckdb\n    database: {database}"
    )
    run = DataContract(data_contract_str=contract).test()
    print(run.pretty())
    assert _check(run).reason == "Fields not in the contract: note"
