"""Nested type checks get their own check line.

A property that declares children via ``properties:`` / ``items:`` gets a second
check next to the base type check, which verifies the nested structure.
"""

import ibis
from open_data_contract_standard.model import (
    OpenDataContractStandard,
    SchemaObject,
    SchemaProperty,
    Server,
)

from datacontract.engines.checks.check_spec import MetricType
from datacontract.engines.checks.create_checks import create_checks
from datacontract.engines.ibis.ibis_check_execute import _run_nested_type, build_check_stubs
from datacontract.engines.ibis.snowflake_structured_types import _to_property
from datacontract.model.run import ResultEnum, Run


def _checks(prop: SchemaProperty, server_type: str, fmt: str | None = None):
    schema = SchemaObject(name="USERS", physicalType="table", properties=[prop])
    dc = OpenDataContractStandard(version="1", kind="DataContract", apiVersion="v3.1.0", id="x", schema=[schema])
    return create_checks(dc, Server(server="s", type=server_type, format=fmt))


def _nested(checks):
    return next((c for c in checks if c.metric == MetricType.FIELD_NESTED_TYPE), None)


def _base(checks):
    return next(
        (c for c in checks if c.metric in (MetricType.FIELD_TYPE, MetricType.FIELD_PHYSICAL_TYPE)),
        None,
    )


_SIC_CODE = SchemaProperty(
    name="primary_sic_code",
    physicalType="OBJECT",
    logicalType="object",
    properties=[
        SchemaProperty(name="code", physicalType="VARCHAR(10)", logicalType="string"),
        SchemaProperty(name="description", physicalType="VARCHAR", logicalType="string"),
    ],
)

_SIC_CODES = SchemaProperty(
    name="sic_codes",
    physicalType="ARRAY",
    logicalType="array",
    items=SchemaProperty(physicalType="STRING", logicalType="string"),
)


# ---------------------------------------------------------------------------
# emission
# ---------------------------------------------------------------------------
def test_object_with_properties_gets_a_nested_physical_type_check():
    checks = _checks(_SIC_CODE, "snowflake")

    assert _base(checks).name == "Check that field primary_sic_code has physical type OBJECT"
    nested = _nested(checks)
    assert nested.type == "field_nested_physical_type"
    assert nested.key == "USERS__primary_sic_code__field_nested_physical_type"
    assert nested.field == "primary_sic_code"
    assert nested.name == "Check that nested physical types of primary_sic_code are correct"


def test_the_expected_label_renders_the_declared_children():
    # The base check already reports the bare container type; the nested check's
    # diagnostics are only useful if they show the declared structure.
    nested = _nested(_checks(_SIC_CODE, "snowflake"))

    assert nested.expected_type_label == "OBJECT(code VARCHAR(10), description VARCHAR)"


def test_array_of_scalars_names_the_element_type():
    nested = _nested(_checks(_SIC_CODES, "snowflake"))

    assert nested.name == "Check that items of array sic_codes have physical type STRING"


def test_array_of_objects_uses_the_generic_wording():
    prop = SchemaProperty(
        name="lines",
        physicalType="ARRAY",
        items=SchemaProperty(logicalType="object", properties=[SchemaProperty(name="qty", logicalType="integer")]),
    )

    assert _nested(_checks(prop, "snowflake")).name == "Check that nested physical types of lines are correct"


def test_logical_path_gets_a_nested_type_check():
    checks = _checks(_SIC_CODE, "local", fmt="delta")

    assert _base(checks).metric == MetricType.FIELD_TYPE
    nested = _nested(checks)
    assert nested.type == "field_nested_type"
    assert nested.name == "Check that nested types of primary_sic_code are correct"


def test_logical_path_array_of_scalars_names_the_element_type():
    nested = _nested(_checks(_SIC_CODES, "local", fmt="delta"))

    assert nested.name == "Check that items of array sic_codes have type string"


def test_base_check_no_longer_compares_the_children():
    # The nested check owns the children, so the base check only compares the
    # column's own type.
    base = _base(_checks(_SIC_CODE, "local", fmt="delta"))

    assert base.expected_schema_property.logicalType == "object"
    assert not base.expected_schema_property.properties


def test_children_declared_inline_only_stay_a_single_check():
    prop = SchemaProperty(name="primary_sic_code", physicalType="OBJECT(code VARCHAR, description VARCHAR)")
    checks = _checks(prop, "snowflake")

    assert _nested(checks) is None
    assert _base(checks).expected_physical_type == "OBJECT(code VARCHAR, description VARCHAR)"


def test_both_declaration_forms_are_enforced_independently():
    prop = SchemaProperty(
        name="primary_sic_code",
        physicalType="OBJECT(code VARCHAR)",
        properties=[SchemaProperty(name="code", physicalType="VARCHAR", logicalType="string")],
    )
    checks = _checks(prop, "snowflake")

    assert _base(checks).expected_physical_type == "OBJECT(code VARCHAR)"
    assert _nested(checks) is not None


def test_array_without_items_stays_a_single_check():
    assert _nested(_checks(SchemaProperty(name="tags", logicalType="array"), "snowflake")) is None


def test_no_nested_check_on_parquet():
    # Parquet/CSV are read through a DuckDB view built from the contract's own
    # types, so the reported nested types are the declared ones.
    assert _nested(_checks(_SIC_CODE, "local", fmt="parquet")) is None


def test_no_nested_check_for_an_uninterpretable_container():
    # A vendor type outside the 9 ODCS categories has no nested structure the
    # CLI can name; the base check still compares it against the catalog.
    prop = SchemaProperty(
        name="attrs",
        physicalType="MAP(VARCHAR, VARCHAR)",
        properties=[SchemaProperty(name="a", physicalType="VARCHAR")],
    )
    checks = _checks(prop, "snowflake")

    assert _nested(checks) is None
    assert _base(checks).expected_physical_type == "MAP(VARCHAR, VARCHAR)"


def test_no_nested_check_for_a_scalar_with_items():
    prop = SchemaProperty(name="weird", logicalType="string", items=SchemaProperty(logicalType="string"))

    assert _nested(_checks(prop, "local", fmt="delta")) is None


def test_dynamically_typed_column_still_gets_a_nested_check():
    # variant / json / jsonb are objects; the check is what reports that their
    # structure cannot be read.
    prop = SchemaProperty(
        name="payload",
        physicalType="VARIANT",
        logicalType="object",
        properties=[SchemaProperty(name="code", logicalType="string")],
    )

    assert _nested(_checks(prop, "snowflake")) is not None


# ---------------------------------------------------------------------------
# execution
# ---------------------------------------------------------------------------
def _run(prop: SchemaProperty, dtype: str, server_type: str = "local", fmt: str | None = "delta"):
    specs = _checks(prop, server_type, fmt)
    run = Run.create_run()
    run.checks = build_check_stubs(specs)
    spec = _nested(specs)
    field = prop.physicalName or prop.name
    _run_nested_type(run, ibis.schema({field: dtype}), {field.lower(): field}, spec)
    return next(c for c in run.checks if c.key == spec.key)


def test_matching_nested_types_pass():
    check = _run(_SIC_CODE, "struct<code: string, description: string>")

    assert check.result == ResultEnum.passed


def test_wrong_nested_type_fails_and_names_the_path():
    check = _run(_SIC_CODE, "struct<code: int64, description: string>")

    assert check.result == ResultEnum.failed
    assert "primary_sic_code.code" in check.reason


def test_missing_nested_field_fails():
    check = _run(_SIC_CODE, "struct<code: string>")

    assert check.result == ResultEnum.failed
    assert "primary_sic_code.description" in check.reason


def test_all_nested_errors_are_reported_in_the_diagnostics():
    check = _run(_SIC_CODE, "struct<code: int64, description: int64>")

    assert "and 1 other error" in check.reason
    assert len(check.diagnostics["errors"]) == 2


def test_wrong_array_element_type_fails():
    check = _run(_SIC_CODES, "array<int64>")

    assert check.result == ResultEnum.failed
    assert "sic_codes[]" in check.reason


def test_nested_check_warns_for_a_dynamically_typed_column():
    # A json / variant / jsonb column holds a different structure per row, so the
    # declared children can be neither confirmed nor refuted.
    check = _run(_SIC_CODE, "json")

    assert check.result == ResultEnum.warning
    assert "cannot be read" in check.reason


def test_nested_check_warns_for_an_untyped_object():
    # Snowflake's untyped OBJECT reads as a map: the keys differ per row, so the
    # declared children are as unverifiable as those of a variant.
    check = _run(_SIC_CODE, "map<string, json>")

    assert check.result == ResultEnum.warning
    assert "can't be verified" in check.reason


def test_nested_check_warns_for_an_untyped_array():
    check = _run(_SIC_CODES, "array<json>")

    assert check.result == ResultEnum.warning
    assert "no verifiable logical type" in check.reason


def test_a_real_mismatch_outranks_an_unverifiable_child():
    prop = SchemaProperty(
        name="primary_sic_code",
        logicalType="object",
        properties=[
            SchemaProperty(name="code", logicalType="integer"),
            SchemaProperty(
                name="description", logicalType="object", properties=[SchemaProperty(name="x", logicalType="string")]
            ),
        ],
    )
    check = _run(prop, "struct<code: string, description: json>")

    assert check.result == ResultEnum.failed
    assert "primary_sic_code.code" in check.reason


def test_nested_check_fails_when_the_column_is_not_a_nested_type():
    check = _run(_SIC_CODE, "int64")

    assert check.result == ResultEnum.failed
    assert check.reason == "Cannot verify the nested types of 'primary_sic_code': the column is not an object"


# ---------------------------------------------------------------------------
# execution against Snowflake's structured types, where the nested native types
# are recovered from SHOW COLUMNS
# ---------------------------------------------------------------------------
_SHOW_COLUMNS_SIC_CODE = {
    "type": "OBJECT",
    "fields": [
        {"fieldName": "code", "fieldType": {"type": "TEXT", "length": 10}},
        {"fieldName": "description", "fieldType": {"type": "TEXT", "length": 16777216}},
    ],
}


def _run_snowflake(prop: SchemaProperty, data_type: dict = _SHOW_COLUMNS_SIC_CODE, dtype: str = "map<string, json>"):
    specs = _checks(prop, "snowflake")
    run = Run.create_run()
    run.checks = build_check_stubs(specs)
    spec = _nested(specs)
    field = prop.physicalName or prop.name
    structured_types = {field.lower(): _to_property(data_type)}
    _run_nested_type(run, ibis.schema({field: dtype}), {field.lower(): field}, spec, structured_types, "snowflake")
    return next(c for c in run.checks if c.key == spec.key)


def _sic_code(**children: str) -> SchemaProperty:
    return SchemaProperty(
        name="primary_sic_code",
        physicalType="OBJECT",
        properties=[SchemaProperty(name=name, physicalType=t) for name, t in children.items()],
    )


def test_a_declared_nested_physical_type_is_checked_against_the_real_one():
    assert _run_snowflake(_sic_code(code="VARCHAR(10)")).result == ResultEnum.passed


def test_an_unparameterized_nested_physical_type_matches_any_length():
    assert _run_snowflake(_sic_code(code="VARCHAR")).result == ResultEnum.passed


def test_a_logical_keyword_in_the_physical_type_is_compared_as_a_category():
    # Contracts routinely carry the logical keyword in physicalType; it names no
    # native type, so it must not be compared against 'VARCHAR(10)' as one.
    assert _run_snowflake(_sic_code(code="string")).result == ResultEnum.passed
    assert _run_snowflake(_sic_code(code="boolean")).result == ResultEnum.failed


def test_a_logical_keyword_in_the_physical_type_is_not_overruled_by_the_logical_type():
    # A property that contradicts itself is still wrong: the physicalType states a
    # category too, so the logicalType must not silently win.
    prop = SchemaProperty(
        name="primary_sic_code",
        physicalType="OBJECT",
        properties=[SchemaProperty(name="code", logicalType="string", physicalType="boolean")],
    )
    check = _run_snowflake(prop)

    assert check.result == ResultEnum.failed
    assert check.reason == "field 'primary_sic_code.code': expected type 'boolean' but got 'string'"


def test_a_too_wide_nested_physical_type_fails():
    check = _run_snowflake(_sic_code(code="VARCHAR(64)"))

    assert check.result == ResultEnum.failed
    assert (
        check.reason
        == "field 'primary_sic_code.code': expected physical type 'VARCHAR(64)' but the column is 'VARCHAR(10)'"
    )


def test_the_nested_physical_type_wins_over_the_logical_one():
    # Only some children declare a physicalType; the others stay on the coarse
    # category check.
    prop = SchemaProperty(
        name="primary_sic_code",
        physicalType="OBJECT",
        properties=[
            SchemaProperty(name="code", logicalType="string"),
            SchemaProperty(name="description", logicalType="string", physicalType="VARCHAR(5)"),
        ],
    )
    check = _run_snowflake(prop)

    assert check.result == ResultEnum.failed
    assert "primary_sic_code.description" in check.reason


def test_the_declared_element_physical_type_of_an_array_is_checked():
    prop = SchemaProperty(name="sic_codes", physicalType="ARRAY", items=SchemaProperty(physicalType="VARCHAR(64)"))
    check = _run_snowflake(prop, {"type": "ARRAY", "elementType": {"type": "TEXT", "length": 10}}, dtype="array<json>")

    assert check.result == ResultEnum.failed
    assert "sic_codes[]" in check.reason


def test_a_nested_physical_type_foreign_to_the_dialect_warns():
    # An Oracle NCLOB declared against Snowflake can be neither confirmed nor refuted.
    check = _run_snowflake(_sic_code(code="NCLOB"))

    assert check.result == ResultEnum.warning
    assert "could not be interpreted" in check.reason


def test_a_foreign_nested_physical_type_falls_back_to_the_logical_type():
    # Same as the column itself: an uninterpretable physicalType degrades to the
    # category check when the property declares a logicalType.
    prop = SchemaProperty(
        name="primary_sic_code",
        physicalType="OBJECT",
        properties=[SchemaProperty(name="code", physicalType="NCLOB", logicalType="string")],
    )

    assert _run_snowflake(prop).result == ResultEnum.passed


def test_the_mismatch_reason_does_not_repeat_the_columns_own_structure():
    # The base type check names the actual type; rendering a whole structured
    # column here would run for lines.
    check = _run(_SIC_CODE, "array<struct<sku: string, quantity: int64, price: decimal(12, 2)>>")

    assert check.result == ResultEnum.failed
    assert check.reason == "Cannot verify the nested types of 'primary_sic_code': the column is not an object"
    assert check.diagnostics["actual"] == "array<struct<sku: string, quantity: int64, price: decimal(12, 2)>>"
