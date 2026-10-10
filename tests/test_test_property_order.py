"""A schema with the custom property `propertyOrder: strict` fails on data whose fields are in another order."""

from datacontract.data_contract import DataContract
from datacontract.model.run import ResultEnum

STRICT = "\n    customProperties:\n      - property: propertyOrder\n        value: strict"


def _contract(path, switch=STRICT, file_format="csv"):
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
      - name: order_id
        logicalType: string
      - name: quantity
        logicalType: integer
      - name: amount
        logicalType: number
"""


def _test(tmp_path, header, switch=STRICT, **kwargs):
    data = tmp_path / "orders.csv"
    values = {"order_id": "A1", "quantity": "3", "amount": "19.99", "note": "x"}
    data.write_text(header + "\n" + "|".join(values[name.lower()] for name in header.split("|")) + "\n")
    return DataContract(data_contract_str=_contract(data, switch), **kwargs).test()


def _check(run):
    return next(c for c in run.checks if c.type == "model_property_order")


def test_fields_in_the_declared_order_pass(tmp_path):
    run = _test(tmp_path, "order_id|quantity|amount")
    print(run.pretty())
    assert _check(run).result == ResultEnum.passed
    assert run.result == ResultEnum.passed


def test_fields_in_another_order_fail(tmp_path):
    run = _test(tmp_path, "order_id|amount|quantity")
    print(run.pretty())
    check = _check(run)
    assert check.result == ResultEnum.failed
    assert (
        check.reason == "Fields in another order: expected order_id, quantity, amount; found order_id, amount, quantity"
    )
    assert check.diagnostics["expected_order"] == ["order_id", "quantity", "amount"]
    assert check.diagnostics["actual_order"] == ["order_id", "amount", "quantity"]
    assert [c.type for c in run.checks if c.result != ResultEnum.passed] == ["model_property_order"]


def test_a_missing_field_is_left_to_the_presence_check(tmp_path):
    run = _test(tmp_path, "order_id|amount")
    failed = [(c.type, c.field) for c in run.checks if c.result != ResultEnum.passed]
    assert failed == [("field_is_present", "quantity")]


def test_an_additional_field_does_not_change_the_order(tmp_path):
    run = _test(tmp_path, "order_id|note|quantity|amount")
    assert _check(run).result == ResultEnum.passed


def test_field_names_compare_case_insensitively(tmp_path):
    run = _test(tmp_path, "ORDER_ID|Quantity|amount")
    assert _check(run).result == ResultEnum.passed


def test_without_the_custom_property_the_order_is_free(tmp_path):
    run = _test(tmp_path, "order_id|amount|quantity", switch="")
    assert not [c for c in run.checks if c.type == "model_property_order"]
    assert run.result == ResultEnum.passed


def test_with_both_custom_properties_the_file_has_exactly_the_declared_fields_in_order(tmp_path):
    switch = STRICT + "\n      - property: additionalProperties\n        value: false"
    run = _test(tmp_path, "order_id|note|amount|quantity", switch=switch)
    failed = {c.type: c.reason for c in run.checks if c.result != ResultEnum.passed}
    assert failed == {
        "model_no_additional_fields": "Fields not in the contract: note",
        "model_property_order": (
            "Fields in another order: expected order_id, quantity, amount; found order_id, amount, quantity"
        ),
    }


def test_the_check_reads_no_rows(tmp_path):
    run = _test(tmp_path, "order_id|amount|quantity", metadata_only=True)
    assert _check(run).result == ResultEnum.failed


def test_a_json_document_with_keys_in_another_order_fails(tmp_path):
    data = tmp_path / "orders.json"
    data.write_text('[{"order_id": "A1", "amount": 19.99, "quantity": 3}]')
    run = DataContract(data_contract_str=_contract(data, file_format="json")).test()
    assert _check(run).result == ResultEnum.failed
