import copy

import pytest
import yaml

from datacontract.data_contract import DataContract
from datacontract.model.breaking import Direction


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


def directions(old, new):
    result = old.breaking(new)
    return {entry.direction for entry in result.entries if entry.direction not in (None, Direction.UNTESTED)}


@pytest.mark.parametrize(
    "old,new,expected",
    [
        ([{"value": "a"}, {"value": "b"}], [{"value": "a"}], {Direction.TIGHTENS}),
        ([{"value": "a"}], [{"value": "a"}, {"value": "b"}], {Direction.LOOSENS}),
        (None, [{"value": "a"}], {Direction.TIGHTENS}),
        ([{"value": "a"}], None, {Direction.LOOSENS}),
        ([{"id": "one", "value": "a"}], [{"id": "one", "value": "b"}], {Direction.BOTH}),
        ([{"id": "one", "value": "a"}], [{"id": "renamed", "value": "a"}], set()),
        ([{"value": "a", "label": "Old"}], [{"value": "a", "label": "New"}], set()),
    ],
)
@pytest.mark.parametrize("nested", [False, True])
def test_enum_compatibility(old, new, expected, nested):
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

    assert directions(contract(properties(old)), contract(properties(new))) == expected


@pytest.mark.parametrize(
    "old,new,expected",
    [
        ({"dimensions": 3}, {"dimensions": 4}, {Direction.BOTH}),
        ({"dimensions": 3}, {"dimensions": 3, "elementType": "float32"}, set()),
        ({"dimensions": 3}, {"dimensions": 3, "elementType": "float64"}, {Direction.BOTH}),
        ({"dimensions": 3, "elementType": "float64"}, {"dimensions": 3}, {Direction.BOTH}),
        ({"dimensions": 3, "elementType": "float32"}, {"dimensions": 3}, set()),
        ({"dimensions": 3}, {"dimensions": 3, "embeddingModel": "updated"}, set()),
    ],
)
def test_vector_shape_compatibility(old, new, expected):
    def properties(options):
        return [{"name": "embedding", "logicalType": "vector", "logicalTypeOptions": options}]

    assert directions(contract(properties(old)), contract(properties(new))) == expected


def test_only_added_properties_are_graded_not_their_enum_and_vector_constraints():
    original = [{"name": "id", "logicalType": "integer"}]
    added = copy.deepcopy(original) + [
        {"name": "status", "logicalType": "string", "enum": [{"value": "a"}]},
        {"name": "embedding", "logicalType": "vector", "logicalTypeOptions": {"dimensions": 3}},
    ]
    assert directions(contract(original), contract(added)) == {Direction.TIGHTENS}


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
    assert directions(contract(original), contract(updated)) == set()
