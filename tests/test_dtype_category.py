import ibis.expr.datatypes as dt
from open_data_contract_standard.model import SchemaProperty

from datacontract.engines.checks.type_normalize import UNKNOWN_LOGICAL_TYPE, schema_property_matches
from datacontract.engines.ibis.dtype_category import (
    ibis_dtype_category,
    ibis_dtype_to_schema_property,
)


def test_uuid_maps_to_string_category():
    # SQL Server `uniqueidentifier` columns surface as ibis UUID; they must be
    # treated as strings, not "other" (regression for #1354).
    assert ibis_dtype_category(dt.UUID()) == "string"


def test_uuid_dtype_to_schema_property_is_string():
    prop = ibis_dtype_to_schema_property(dt.UUID())
    assert prop is not None
    assert prop.logicalType == "string"


def test_uuid_column_matches_string_contract_property():
    # A property declared as logicalType string (physicalType uniqueidentifier)
    # must match a column ibis reports as UUID.
    expected = SchemaProperty(logicalType="string", physicalType="uniqueidentifier")
    actual = ibis_dtype_to_schema_property(dt.UUID())
    assert schema_property_matches(expected, actual)


def test_json_maps_to_unknown_marker():
    # Snowflake VARIANT / Postgres JSONB / BigQuery JSON reflect as ibis json.
    prop = ibis_dtype_to_schema_property(dt.JSON())
    assert prop is not None
    assert prop.logicalType == UNKNOWN_LOGICAL_TYPE


def test_map_maps_to_opaque_object():
    # Snowflake OBJECT reflects as ibis map<string, json>: base confirmable,
    # inner structure unknowable (properties=None).
    prop = ibis_dtype_to_schema_property(dt.Map(dt.string, dt.JSON()))
    assert prop is not None
    assert prop.logicalType == "object"
    assert prop.properties is None


def test_array_of_json_items_are_unknown():
    # Snowflake ARRAY reflects as ibis array<json>: array base with an
    # unknown-typed element.
    prop = ibis_dtype_to_schema_property(dt.Array(dt.JSON()))
    assert prop is not None
    assert prop.logicalType == "array"
    assert prop.items is not None
    assert prop.items.logicalType == UNKNOWN_LOGICAL_TYPE
