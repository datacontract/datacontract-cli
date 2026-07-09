from open_data_contract_standard.model import SchemaProperty

from datacontract.engines.checks.type_normalize import (
    UNKNOWN_LOGICAL_TYPE,
    normalize_type_name,
    schema_property_matches,
    schema_property_mismatch_reason,
)


def test_normalize_strips_length_parameters():
    assert normalize_type_name("VARCHAR2(4000)") == "string"
    assert normalize_type_name("VARCHAR2(40)") == "string"
    assert normalize_type_name("NUMBER(4,0)") == "number"
    assert normalize_type_name("CHAR(10)") == "string"


def test_normalize_oracle_string_types():
    # Oracle VARCHAR2/NVARCHAR2 (with or without length) are strings, not "other".
    assert normalize_type_name("VARCHAR2") == "string"
    assert normalize_type_name("NVARCHAR2") == "string"
    assert normalize_type_name("nvarchar2(100)") == "string"


def _opaque_object():
    # what ibis_dtype_to_schema_property produces for a Snowflake OBJECT (map)
    return SchemaProperty(logicalType="object", properties=None)


def _unknown():
    # what it produces for a Snowflake VARIANT (json)
    return SchemaProperty(logicalType=UNKNOWN_LOGICAL_TYPE)


def test_opaque_object_matches_declared_object_with_properties():
    # OBJECT column declared with nested properties: base enforced, inner skipped.
    expected = SchemaProperty(logicalType="object", properties=[SchemaProperty(name="city", logicalType="string")])
    assert schema_property_matches(expected, _opaque_object())
    assert schema_property_mismatch_reason(expected, _opaque_object()) == ""


def test_opaque_object_fails_against_wrong_base():
    expected = SchemaProperty(logicalType="array")
    assert not schema_property_matches(expected, _opaque_object())


def test_array_with_typed_items_matches_unknown_element():
    # ARRAY reflects as array<json>; a declared items type must not fail on the
    # unknown element (inner types are skipped, never asserted).
    expected = SchemaProperty(logicalType="array", items=SchemaProperty(logicalType="number"))
    actual = SchemaProperty(logicalType="array", items=_unknown())
    assert schema_property_matches(expected, actual)
    assert schema_property_mismatch_reason(expected, actual) == ""


def test_real_struct_still_descends_and_fails_on_wrong_nested_type():
    # Guard: a genuinely-typed nested structure (not opaque) is still validated.
    expected = SchemaProperty(logicalType="object", properties=[SchemaProperty(name="a", logicalType="string")])
    actual = SchemaProperty(logicalType="object", properties=[SchemaProperty(name="a", logicalType="integer")])
    assert not schema_property_matches(expected, actual)
    assert "expected type 'string'" in schema_property_mismatch_reason(expected, actual)
