import copy

import pytest
import yaml

from datacontract.data_contract import DataContract


def contract(properties):
    return DataContract(
        data_contract_str=yaml.safe_dump(
            {
                "apiVersion": "v3.2.0",
                "kind": "DataContract",
                "id": "test",
                "version": "1",
                "status": "active",
                "schema": [{"name": "orders", "properties": properties}],
            }
        )
    )


@pytest.mark.parametrize(
    "old,new,breaking",
    [
        ([{"value": "a"}, {"value": "b"}], [{"value": "a"}], True),
        ([{"value": "a"}], [{"value": "a"}, {"value": "b"}], False),
        (None, [{"value": "a"}], True),
        ([{"value": "a"}], None, False),
        ([{"id": "one", "value": "a"}], [{"id": "one", "value": "b"}], True),
        ([{"id": "one", "value": "a"}], [{"id": "renamed", "value": "a"}], False),
        ([{"value": "a", "label": "Old"}], [{"value": "a", "label": "New"}], False),
    ],
)
@pytest.mark.parametrize("nested", [False, True])
def test_enum_compatibility(old, new, breaking, nested):
    def properties(entries):
        prop = {"name": "status", "logicalType": "string"}
        if entries is not None:
            prop["enum"] = entries
        if nested:
            prop = {
                "name": "attributes",
                "logicalType": "map",
                "map": {
                    "key": {"logicalType": "string"},
                    "value": {"logicalType": "object", "properties": [prop]},
                },
            }
        return [prop]

    result = contract(properties(old)).breaking(contract(properties(new)))
    assert result.is_breaking is breaking, result.model_dump()


@pytest.mark.parametrize(
    "old,new,breaking",
    [
        ({"dimensions": 3}, {"dimensions": 4}, True),
        ({"dimensions": 3}, {"dimensions": 3, "elementType": "float32"}, False),
        ({"dimensions": 3}, {"dimensions": 3, "elementType": "float64"}, True),
        ({"dimensions": 3, "elementType": "float64"}, {"dimensions": 3}, True),
        ({"dimensions": 3, "elementType": "float32"}, {"dimensions": 3}, False),
        ({"dimensions": 3}, {"dimensions": 3, "embeddingModel": "updated"}, False),
    ],
)
def test_vector_shape_compatibility(old, new, breaking):
    def properties(options):
        return [{"name": "embedding", "logicalType": "vector", "logicalTypeOptions": options}]

    assert contract(properties(old)).breaking(contract(properties(new))).is_breaking is breaking


def test_adding_properties_with_enum_and_vector_constraints_is_not_breaking():
    original = [{"name": "id", "logicalType": "integer"}]
    added = copy.deepcopy(original) + [
        {"name": "status", "logicalType": "string", "enum": [{"value": "a"}]},
        {"name": "embedding", "logicalType": "vector", "logicalTypeOptions": {"dimensions": 3}},
    ]
    assert not contract(original).breaking(contract(added)).is_breaking


def test_enum_custom_property_change_is_metadata():
    original = [
        {
            "name": "status",
            "logicalType": "string",
            "enum": [{"value": "a", "customProperties": [{"property": "color", "value": "blue"}]}],
        }
    ]
    updated = copy.deepcopy(original)
    updated[0]["enum"][0]["customProperties"][0]["value"] = "green"
    assert not contract(original).breaking(contract(updated)).is_breaking
