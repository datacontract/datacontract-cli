"""Unit tests for reading Spark's type JSON without pyspark.

The expectations are pyspark's own output: every `simple_string` case below was
checked against `DataType.simpleString()` for the matching pyspark type, so a
drift in this table is a drift from Spark.
"""

import pytest

from datacontract.imports import spark_importer
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
        ("timestamp", "timestamp"),
        ("timestamp_ntz", "timestamp"),
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


def test_describe_native_type_parser_keeps_nested_varchar_lengths():
    struct_type = "struct<varchar_field:varchar(100)>"
    assert spark_importer._describe_type_to_json(struct_type) == {
        "type": "struct",
        "fields": [{"name": "varchar_field", "type": "varchar(100)", "nullable": True, "metadata": {}}],
    }
    assert spark_importer._describe_type_to_json("array<varchar(50)>") == {
        "type": "array",
        "elementType": "varchar(50)",
        "containsNull": True,
    }
    assert spark_importer._describe_type_to_json("map<string,varchar(30)>") == {
        "type": "map",
        "keyType": "string",
        "valueType": "varchar(30)",
        "valueContainsNull": True,
    }


def test_import_from_spark_df_prefers_exact_metadata_for_nested_varchar():
    df = type("FakeDF", (), {"schema": []})()
    metadata_prop = property_from_field_json(
        {
            "name": "payload",
            "type": {"type": "struct", "fields": [{"name": "varchar_field", "type": "varchar(100)", "nullable": True, "metadata": {}}]},
            "nullable": True,
            "metadata": {},
        }
    )

    def fake_metadata(spark, source, schema=None):
        return [metadata_prop]

    monkeypatch = pytest.MonkeyPatch()
    monkeypatch.setattr(spark_importer, "_table_metadata_properties", fake_metadata)
    try:
        result = spark_importer.import_from_spark_df(None, "orders", df, None)
    finally:
        monkeypatch.undo()

    assert result.properties[0].physicalType == "struct<varchar_field:varchar(100)>"
    assert result.properties[0].properties[0].physicalType == "varchar(100)"


def test_table_metadata_ignores_non_column_describe_rows(monkeypatch):
    field = type("FakeField", (), {"name": "id", "nullable": False, "metadata": {}})()
    schema = [field]
    monkeypatch.setattr(
        spark_importer,
        "_describe_table_types",
        lambda spark, source: {"id": "bigint", "# Partition Information": "id"},
    )

    properties = spark_importer._table_metadata_properties(None, "orders", schema)

    assert [property_.name for property_ in properties] == ["id"]
    assert properties[0].physicalType == "bigint"


def test_a_nullable_field_leaves_required_unset():
    """ODCS treats an absent `required` as optional, so it stays absent rather than false."""
    field = {"name": "id", "type": "long", "nullable": True, "metadata": {}}

    assert property_from_field_json(field).required is None
