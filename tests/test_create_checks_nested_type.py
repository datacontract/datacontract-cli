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
from datacontract.model.run import ResultEnum, Run


def _checks(prop: SchemaProperty, server_type: str, fmt: str | None = None):
    schema = SchemaObject(name="USERS", physicalType="table", properties=[prop])
    dc = OpenDataContractStandard(version="1", kind="DataContract", apiVersion="v3.1.0", id="x", schema=[schema])
    return create_checks(dc, Server(server="s", type=server_type, format=fmt))


def _nested(checks):
    return next(
        (c for c in checks if c.metric in (MetricType.FIELD_NESTED_TYPE, MetricType.FIELD_NESTED_PHYSICAL_TYPE)),
        None,
    )


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


def test_nested_check_fails_when_the_column_is_not_a_nested_type():
    check = _run(_SIC_CODE, "int64")

    assert check.result == ResultEnum.failed
    assert check.reason == (
        "Cannot verify the nested types of 'primary_sic_code': the column is 'int64', not a nested object"
    )
