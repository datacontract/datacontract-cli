import pytest
import yaml

from datacontract.data_contract import DataContract


def document(prop):
    return {
        "apiVersion": "v3.2.0",
        "kind": "DataContract",
        "id": "test",
        "version": "1",
        "status": "active",
        "schema": [{"name": "orders", "properties": [{"name": "field", **prop}]}],
    }


def lint(prop, **kwargs):
    return DataContract(data_contract_str=yaml.safe_dump(document(prop)), **kwargs).lint()


@pytest.mark.parametrize(
    "options", [None, {}, {"dimensions": 0}, {"dimensions": -1}, {"dimensions": 1.5}, {"dimensions": "3"}]
)
@pytest.mark.parametrize("all_errors", [False, True])
def test_vector_requires_positive_integer_dimensions(options, all_errors):
    prop = {"logicalType": "vector"}
    if options is not None:
        prop["logicalTypeOptions"] = options
    assert lint(prop, all_errors=all_errors).result == "failed"


@pytest.mark.parametrize("nesting", ["property", "object", "array", "map_key", "map_value"])
@pytest.mark.parametrize("value", ["a", 1, True, None])
def test_duplicate_enum_values_fail_regardless_of_labels(nesting, value):
    prop = {"logicalType": "string", "enum": [{"value": value, "label": "First"}, {"value": value, "label": "Second"}]}
    if nesting == "object":
        prop = {"logicalType": "object", "properties": [{"name": "inner", **prop}]}
    elif nesting == "array":
        prop = {"logicalType": "array", "items": prop}
    elif nesting.startswith("map_"):
        side = nesting.removeprefix("map_")
        prop = {
            "logicalType": "map",
            "map": {"key": {"logicalType": "string"}, "value": {"logicalType": "string"}, side: prop},
        }
    run = lint(prop)
    assert run.result == "failed"
    assert any("duplicates enum[0].value" in c.reason for c in run.checks if c.reason)


def test_numeric_enum_values_compare_by_value():
    assert lint({"enum": [{"value": 1, "label": "Integer"}, {"value": 1.0, "label": "Float"}]}).result == "failed"


def test_distinct_json_types_and_labels_are_valid():
    assert lint({"enum": [{"value": 1}, {"value": "1"}, {"value": True}, {"value": None}]}).result == "passed"
    assert lint({"logicalType": "vector", "logicalTypeOptions": {"dimensions": 3}}).result == "passed"


def test_all_errors_combines_schema_and_enum_violations():
    doc = document({"logicalType": "vector"})
    doc["schema"][0]["properties"].append(
        {"name": "status", "enum": [{"value": "a", "label": "First"}, {"value": "a", "label": "Second"}]}
    )
    run = DataContract(data_contract_str=yaml.safe_dump(doc), all_errors=True).lint()
    assert run.result == "failed"
    reasons = [c.reason for c in run.checks]
    assert any("logicalTypeOptions" in reason for reason in reasons)
    assert any("duplicates enum" in reason for reason in reasons)


@pytest.mark.parametrize("prop", [{"enum": [{"value": "a"}, {"value": "a"}]}, {"logicalType": "vector"}])
def test_custom_schema_remains_the_source_of_truth(tmp_path, prop):
    schema = tmp_path / "custom.json"
    schema.write_text('{"type":"object"}')
    assert lint(prop, schema_location=str(schema)).result == "passed"


@pytest.mark.parametrize(
    "prop",
    [
        {"logicalType": "array", "items": {"logicalType": "vector"}},
        {"logicalType": "map", "map": {"key": {"logicalType": "string"}, "value": {"logicalType": "vector"}}},
    ],
)
def test_nested_vectors_also_require_dimensions(prop):
    assert lint(prop).result == "failed"


def test_older_physical_only_properties_still_lint():
    doc = document({"physicalType": "VARCHAR"})
    doc["apiVersion"] = "v3.1.0"
    assert DataContract(data_contract_str=yaml.safe_dump(doc)).lint().result == "passed"
