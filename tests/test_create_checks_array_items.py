"""The ODCS array constraints become checks.

`minItems`, `maxItems` and `uniqueItems` measure the elements of one row's
array, so they are invalid_count checks like the other logicalTypeOptions
rather than a count over rows.
"""

from open_data_contract_standard.model import (
    OpenDataContractStandard,
    SchemaObject,
    SchemaProperty,
    Server,
)

from datacontract.engines.checks.check_spec import MetricType
from datacontract.engines.checks.create_checks import create_checks


def checks_for(options: dict):
    prop = SchemaProperty(name="tags", logicalType="array", logicalTypeOptions=options)
    schema = SchemaObject(name="orders", physicalType="table", properties=[prop])
    contract = OpenDataContractStandard(version="1", kind="DataContract", apiVersion="v3.1.0", id="x", schema=[schema])
    return create_checks(contract, Server(server="s", type="postgres"))


def by_type(checks, check_type):
    return next((c for c in checks if c.type == check_type), None)


def test_min_items_becomes_a_check():
    check = by_type(checks_for({"minItems": 2}), "field_min_items")

    assert check is not None
    assert check.metric == MetricType.INVALID_COUNT
    assert check.valid_min_items == 2
    assert check.field == "tags"


def test_max_items_becomes_a_check():
    check = by_type(checks_for({"maxItems": 5}), "field_max_items")

    assert check.valid_max_items == 5


def test_unique_items_becomes_a_check():
    check = by_type(checks_for({"uniqueItems": True}), "field_unique_items")

    assert check.valid_unique_items is True


def test_unique_items_false_asserts_nothing():
    """`uniqueItems: false` is the default, and a check for it would always pass."""
    assert by_type(checks_for({"uniqueItems": False}), "field_unique_items") is None


def test_an_array_without_options_gets_no_item_checks():
    types = {c.type for c in checks_for({})}

    assert not {t for t in types if "items" in t}


def test_each_constraint_is_its_own_check():
    """One rule per check, so a report says which constraint failed."""
    checks = checks_for({"minItems": 1, "maxItems": 3, "uniqueItems": True})
    item_checks = [c for c in checks if "items" in c.type]

    assert sorted(c.type for c in item_checks) == [
        "field_max_items",
        "field_min_items",
        "field_unique_items",
    ]
