"""Unit tests for reading Spark's type JSON without pyspark.

The expectations are pyspark's own output: every `simple_string` case below was
checked against `DataType.simpleString()` for the matching pyspark type, so a
drift in this table is a drift from Spark.
"""

import pytest

from datacontract.imports.spark_type_json import (
    logical_type,
    property_from_field_json,
    property_from_type_json,
    simple_string,
)

STRUCT_LIST = {
    "type": "array",
    "elementType": {
        "type": "struct",
        "fields": [
            {"name": "key", "type": "string", "nullable": True, "metadata": {}},
            {"name": "value", "type": "long", "nullable": True, "metadata": {}},
        ],
    },
    "containsNull": True,
}


@pytest.mark.parametrize(
    "type_json, expected",
    [
        ("string", "string"),
        ("byte", "tinyint"),
        ("short", "smallint"),
        # the integer family is where Spark's JSON name and its simpleString differ
        ("integer", "int"),
        ("long", "bigint"),
        ("float", "float"),
        ("double", "double"),
        ("decimal(10,2)", "decimal(10,2)"),
        ("boolean", "boolean"),
        ("binary", "binary"),
        ("date", "date"),
        ("timestamp", "timestamp"),
        ("timestamp_ntz", "timestamp_ntz"),
        ("void", "void"),
        ("varchar(20)", "varchar(20)"),
        ("char(5)", "char(5)"),
        ({"type": "array", "elementType": "string", "containsNull": True}, "array<string>"),
        ({"type": "map", "keyType": "string", "valueType": "long", "valueContainsNull": True}, "map<string,bigint>"),
        (STRUCT_LIST, "array<struct<key:string,value:bigint>>"),
    ],
)
def test_simple_string_matches_spark(type_json, expected):
    assert simple_string(type_json) == expected


@pytest.mark.parametrize(
    "type_json, expected",
    [
        ("string", "string"),
        ("varchar(20)", "string"),
        ("void", "string"),
        ("byte", "integer"),
        ("short", "integer"),
        ("integer", "integer"),
        ("long", "integer"),
        ("float", "number"),
        ("double", "number"),
        ("decimal(10,2)", "number"),
        ("boolean", "boolean"),
        ("date", "date"),
        ("timestamp", "date"),
        ("timestamp_ntz", "date"),
        ("binary", "array"),
        ({"type": "array", "elementType": "string", "containsNull": True}, "array"),
        ({"type": "map", "keyType": "string", "valueType": "long", "valueContainsNull": True}, "map"),
        ({"type": "struct", "fields": []}, "object"),
    ],
)
def test_logical_type(type_json, expected):
    assert logical_type(type_json) == expected


def test_an_unknown_type_is_rejected():
    """Reported rather than guessed at: the caller degrades the column to its flat type."""
    with pytest.raises(ValueError, match="Unsupported Spark type"):
        logical_type("interval day to second")


def test_a_struct_becomes_nested_properties():
    field = {
        "name": "id_struct",
        "type": {"type": "struct", "fields": [{"name": "value", "type": "long", "nullable": True, "metadata": {}}]},
        "nullable": True,
        "metadata": {"comment": "the identifier"},
    }

    prop = property_from_field_json(field)

    assert prop.name == "id_struct"
    assert prop.logicalType == "object"
    assert prop.physicalType == "struct<value:bigint>"
    assert prop.description == "the identifier"
    assert [(p.name, p.logicalType, p.physicalType) for p in prop.properties] == [("value", "integer", "bigint")]


def test_an_array_of_structs_nests_through_items():
    prop = property_from_type_json("struct_list", STRUCT_LIST)

    assert prop.logicalType == "array"
    assert prop.physicalType == "array<struct<key:string,value:bigint>>"
    assert prop.items.name == "items"
    assert prop.items.logicalType == "object"
    assert [p.name for p in prop.items.properties] == ["key", "value"]


def test_a_non_nullable_field_is_required():
    field = {"name": "id", "type": "long", "nullable": False, "metadata": {}}

    assert property_from_field_json(field).required is True


def test_a_nullable_field_leaves_required_unset():
    """ODCS treats an absent `required` as optional, so it stays absent rather than false."""
    field = {"name": "id", "type": "long", "nullable": True, "metadata": {}}

    assert property_from_field_json(field).required is None
