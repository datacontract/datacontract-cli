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


def _untyped_object():
    # what ibis_dtype_to_schema_property produces for a Snowflake OBJECT (map)
    return SchemaProperty(logicalType="object", properties=None)


def _unknown():
    # what it produces for a Snowflake VARIANT (json)
    return SchemaProperty(logicalType=UNKNOWN_LOGICAL_TYPE, physicalType="json")


def test_untyped_object_fails_declared_object_with_properties():
    # OBJECT column declared with nested properties, but the actual column is an
    # untyped object (untyped OBJECT / MAP): the nested types can't be verified.
    expected = SchemaProperty(logicalType="object", properties=[SchemaProperty(name="city", logicalType="string")])
    assert not schema_property_matches(expected, _untyped_object())
    assert "can't be verified" in schema_property_mismatch_reason(expected, _untyped_object())


def test_bare_object_matches_untyped_object():
    # No nested properties declared: the base 'object' is confirmable, so it passes.
    expected = SchemaProperty(logicalType="object")
    assert schema_property_matches(expected, _untyped_object())
    assert schema_property_mismatch_reason(expected, _untyped_object()) == ""


def test_untyped_object_fails_against_wrong_base():
    expected = SchemaProperty(logicalType="array")
    assert not schema_property_matches(expected, _untyped_object())


def test_array_with_typed_items_fails_unknown_element():
    # ARRAY reflects as array<json>; a declared items type can't be verified
    # against the dynamically-typed element, so it fails.
    expected = SchemaProperty(logicalType="array", items=SchemaProperty(logicalType="number"))
    actual = SchemaProperty(logicalType="array", items=_unknown())
    assert not schema_property_matches(expected, actual)
    assert schema_property_mismatch_reason(expected, actual) == (
        "field '[]': has type 'json', but the contract specifies 'number'. "
        "A 'json' value has no verifiable logical type. "
        "If this is intentional, specify `physicalType: json`."
    )


def test_unverifiable_type_reports_the_same_message_at_any_depth():
    # The top-level and nested paths must not diverge: one condition, one message.
    top = schema_property_mismatch_reason(SchemaProperty(logicalType="number"), _unknown())
    nested = schema_property_mismatch_reason(
        SchemaProperty(logicalType="array", items=SchemaProperty(logicalType="number")),
        SchemaProperty(logicalType="array", items=_unknown()),
    )
    assert top == nested.replace("field '[]'", "column")
    assert "specify `physicalType: json`" in top


def test_bare_array_matches_unknown_element():
    # No items declared: the base 'array' is confirmable, so it passes.
    expected = SchemaProperty(logicalType="array")
    actual = SchemaProperty(logicalType="array", items=_unknown())
    assert schema_property_matches(expected, actual)
    assert schema_property_mismatch_reason(expected, actual) == ""


def test_real_struct_still_descends_and_fails_on_wrong_nested_type():
    # Guard: a genuinely-typed nested structure (not untyped) is still validated.
    expected = SchemaProperty(logicalType="object", properties=[SchemaProperty(name="a", logicalType="string")])
    actual = SchemaProperty(logicalType="object", properties=[SchemaProperty(name="a", logicalType="integer")])
    assert not schema_property_matches(expected, actual)
    assert "expected type 'string'" in schema_property_mismatch_reason(expected, actual)
