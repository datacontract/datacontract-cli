"""Direct unit tests for `field_to_data_tests`.

PR A leaned on the exporter's golden-file tests for coverage. Sync introduces
new caller behavior (different ``source_name``, ``supports_constraints=False``
on properties the exporter routes through ``constraints``) that isn't exercised
from the exporter side, so we cover each row of the master mapping table here.
"""

from open_data_contract_standard.model import CustomProperty, DataQuality, Relationship, SchemaProperty

from datacontract.integration.dbt_test_mapping import field_to_data_tests


def _prop(**kwargs) -> SchemaProperty:
    return SchemaProperty(**kwargs)


def test_required_emits_not_null():
    tests = field_to_data_tests(_prop(name="x", required=True), supports_constraints=False)
    assert "not_null" in tests


def test_unique_emits_unique():
    tests = field_to_data_tests(_prop(name="x", unique=True), supports_constraints=False)
    assert "unique" in tests


def test_single_pk_emits_unique_and_not_null():
    tests = field_to_data_tests(
        _prop(name="x", primaryKey=True),
        is_primary_key=True,
        is_single_pk=True,
        supports_constraints=False,
    )
    assert "not_null" in tests
    assert "unique" in tests


def test_composite_pk_member_does_not_emit_unique():
    """Composite-PK members get not_null but not unique; uniqueness is enforced model-level."""
    tests = field_to_data_tests(
        _prop(name="x", primaryKey=True),
        is_primary_key=True,
        is_single_pk=False,
        supports_constraints=False,
    )
    assert "not_null" in tests
    assert "unique" not in tests


def test_supports_constraints_suppresses_not_null_and_unique():
    """When the caller emits these as dbt constraints, the helper must not double-emit."""
    tests = field_to_data_tests(
        _prop(name="x", required=True, unique=True),
        supports_constraints=True,
    )
    assert "not_null" not in tests
    assert "unique" not in tests


def test_enum_from_logical_type_options():
    tests = field_to_data_tests(
        _prop(name="x", logicalTypeOptions={"enum": ["a", "b"]}),
        supports_constraints=False,
    )
    assert {"accepted_values": {"values": ["a", "b"]}} in tests


def test_enum_from_custom_property_string():
    tests = field_to_data_tests(
        _prop(name="x", customProperties=[CustomProperty(property="enum", value='["a", "b"]')]),
        supports_constraints=False,
    )
    assert {"accepted_values": {"values": ["a", "b"]}} in tests


def test_enum_from_custom_property_list():
    tests = field_to_data_tests(
        _prop(name="x", customProperties=[CustomProperty(property="enum", value=["a", "b"])]),
        supports_constraints=False,
    )
    assert {"accepted_values": {"values": ["a", "b"]}} in tests


def test_enum_from_quality_invalid_values():
    tests = field_to_data_tests(
        _prop(
            name="x",
            quality=[DataQuality(metric="invalidValues", arguments={"validValues": ["a", "b"]})],
        ),
        supports_constraints=False,
    )
    assert {"accepted_values": {"values": ["a", "b"]}} in tests


def test_length_bounds_emit_no_yaml_test():
    """Length bounds previously emitted a `dbt_expectations` macro; they're now
    handled as singular SQL by `datacontract dbt sync`."""
    tests = field_to_data_tests(
        _prop(name="x", logicalTypeOptions={"minLength": 3, "maxLength": 10}),
        supports_constraints=False,
    )
    assert tests == []


def test_regex_emits_no_yaml_test():
    tests = field_to_data_tests(
        _prop(name="x", logicalTypeOptions={"pattern": "^[A-Z]+$"}),
        supports_constraints=False,
    )
    assert tests == []


def test_numeric_range_emits_no_yaml_test():
    tests = field_to_data_tests(
        _prop(
            name="x",
            logicalTypeOptions={
                "minimum": 0,
                "maximum": 100,
                "exclusiveMinimum": 0,
                "exclusiveMaximum": 100,
            },
        ),
        supports_constraints=False,
    )
    assert tests == []


def test_relationships_uses_source_name():
    tests = field_to_data_tests(
        _prop(name="order_id", relationships=[Relationship(to="customers.id")]),
        source_name="orders-contract",
        supports_constraints=False,
    )
    assert {
        "relationships": {
            "to": 'source("orders-contract", "customers")',
            "field": "id",
        }
    } in tests


def test_relationships_malformed_to_no_dot():
    """Single-segment `to` falls into the `(None, x)` branch and emits no relationship test."""
    tests = field_to_data_tests(
        _prop(name="x", relationships=[Relationship(to="customers")]),
        source_name="src",
        supports_constraints=False,
    )
    rel_tests = [t for t in tests if isinstance(t, dict) and "relationships" in t]
    assert rel_tests == []


def test_no_quality_returns_empty():
    assert field_to_data_tests(_prop(name="x"), supports_constraints=False) == []
