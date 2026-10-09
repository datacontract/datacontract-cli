"""Type checks mirror the contract: every declared nested property gets its own lines.

A property's own type line leaves out the properties and array items that get
lines of their own, and keeps what has no path of its own: a map's key and
value, and the items of an array's items.
"""

from types import SimpleNamespace

import ibis
from open_data_contract_standard.model import (
    MapDefinition,
    OpenDataContractStandard,
    SchemaObject,
    SchemaProperty,
    Server,
)

from datacontract.engines.checks.check_spec import MetricType
from datacontract.engines.checks.create_checks import create_checks
from datacontract.engines.ibis.ibis_check_execute import (
    _run_physical_type,
    _run_present,
    _run_type,
    build_check_stubs,
)
from datacontract.engines.ibis.snowflake_structured_types import _to_property
from datacontract.model.run import ResultEnum, Run


def _checks(prop: SchemaProperty, server_type: str, fmt: str | None = None):
    schema = SchemaObject(name="USERS", physicalType="table", properties=[prop])
    dc = OpenDataContractStandard(version="1", kind="DataContract", apiVersion="v3.1.0", id="x", schema=[schema])
    return create_checks(dc, Server(server="s", type=server_type, format=fmt))


def _lines(checks):
    return {(c.field, c.type) for c in checks}


def _type_check(checks, field):
    return next(
        c for c in checks if c.field == field and c.metric in (MetricType.FIELD_TYPE, MetricType.FIELD_PHYSICAL_TYPE)
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
def test_every_declared_property_gets_its_own_lines():
    assert _lines(_checks(_SIC_CODE, "snowflake")) == {
        ("primary_sic_code", "field_is_present"),
        ("primary_sic_code", "field_physical_type"),
        ("primary_sic_code.code", "field_is_present"),
        ("primary_sic_code.code", "field_physical_type"),
        ("primary_sic_code.description", "field_is_present"),
        ("primary_sic_code.description", "field_physical_type"),
    }


def test_the_own_type_line_leaves_out_the_children():
    base = _type_check(_checks(_SIC_CODE, "local", fmt="delta"), "primary_sic_code")

    assert base.expected_schema_property.logicalType == "object"
    assert not base.expected_schema_property.properties


def test_the_items_of_an_array_get_a_type_line_but_no_presence_line():
    lines = _lines(_checks(_SIC_CODES, "snowflake"))

    assert ("sic_codes[]", "field_physical_type") in lines
    assert ("sic_codes[]", "field_is_present") not in lines
    assert not _type_check(_checks(_SIC_CODES, "snowflake"), "sic_codes").expected_schema_property.items


def test_an_array_of_objects_gets_lines_for_its_items_and_their_properties():
    prop = SchemaProperty(
        name="lines",
        physicalType="ARRAY",
        items=SchemaProperty(logicalType="object", properties=[SchemaProperty(name="qty", logicalType="integer")]),
    )

    assert {("lines[]", "field_type"), ("lines[].qty", "field_type")} <= _lines(_checks(prop, "snowflake"))


def test_children_declared_inline_only_stay_a_single_check():
    prop = SchemaProperty(name="primary_sic_code", physicalType="OBJECT(code VARCHAR, description VARCHAR)")

    assert _lines(_checks(prop, "snowflake")) == {
        ("primary_sic_code", "field_is_present"),
        ("primary_sic_code", "field_physical_type"),
    }


def test_both_declaration_forms_are_enforced_independently():
    prop = SchemaProperty(
        name="primary_sic_code",
        physicalType="OBJECT(code VARCHAR)",
        properties=[SchemaProperty(name="code", physicalType="VARCHAR", logicalType="string")],
    )
    checks = _checks(prop, "snowflake")

    assert _type_check(checks, "primary_sic_code").expected_physical_type == "OBJECT(code VARCHAR)"
    assert _type_check(checks, "primary_sic_code.code").expected_physical_type == "VARCHAR"


def test_nested_types_warn_on_parquet():
    # Parquet/CSV are read through a DuckDB view built from the contract's own
    # types, so the reported types are the declared ones.
    checks = _checks(_SIC_CODE, "local", fmt="parquet")
    nested = next(c for c in checks if c.field == "primary_sic_code.code" and c.type == "field_type")

    assert nested.preset_result == "warning"


def test_a_map_has_one_type_line_that_keeps_its_key_and_value():
    prop = SchemaProperty(
        name="attrs",
        logicalType="map",
        physicalType="MAP(VARCHAR, OBJECT(a VARCHAR))",
        map=MapDefinition(
            key=SchemaProperty(logicalType="string"),
            value=SchemaProperty(logicalType="object", properties=[SchemaProperty(name="a", logicalType="string")]),
        ),
    )
    checks = _checks(prop, "snowflake")

    assert _lines(checks) == {("attrs", "field_is_present"), ("attrs", "field_physical_type")}
    assert _type_check(checks, "attrs").expected_schema_property.map is not None


def test_value_rules_inside_a_map_warn():
    prop = SchemaProperty(
        name="attrs",
        logicalType="map",
        map=MapDefinition(
            key=SchemaProperty(logicalType="string", required=True),
            value=SchemaProperty(
                logicalType="object", properties=[SchemaProperty(name="a", logicalType="string", required=True)]
            ),
        ),
    )
    checks = _checks(prop, "duckdb")

    # a map key is never null, so its `required` holds by definition
    inside = [c for c in checks if c.field.startswith("attrs[")]
    assert [(c.field, c.type) for c in inside] == [("attrs[value].a", "field_required")]
    assert inside[0].preset_result == "warning"
    assert inside[0].preset_reason == "Checks on the key or value of a map are not supported yet."


def test_the_items_of_an_arrays_items_stay_in_its_items_line():
    prop = SchemaProperty(
        name="matrix",
        logicalType="array",
        items=SchemaProperty(logicalType="array", items=SchemaProperty(logicalType="integer")),
    )
    checks = _checks(prop, "duckdb")

    assert ("matrix[]", "field_type") in _lines(checks)
    assert _type_check(checks, "matrix[]").expected_schema_property.items.logicalType == "integer"


def test_no_lines_for_the_items_of_a_scalar():
    prop = SchemaProperty(name="weird", logicalType="string", items=SchemaProperty(logicalType="string"))

    assert _lines(_checks(prop, "local", fmt="delta")) == {("weird", "field_is_present"), ("weird", "field_type")}


# ---------------------------------------------------------------------------
# execution against the types ibis reflects
# ---------------------------------------------------------------------------
def _run(prop: SchemaProperty, dtype: str, server_type: str = "local", fmt: str | None = "delta"):
    specs = _checks(prop, server_type, fmt)
    run = Run.create_run()
    run.checks = build_check_stubs(specs)
    schema = ibis.schema({prop.name: dtype})
    for spec in specs:
        if spec.metric == MetricType.FIELD_PRESENT:
            _run_present(run, None, "USERS", schema, spec)
        elif spec.metric == MetricType.FIELD_TYPE:
            _run_type(run, schema, None, spec)
    return {(c.field, c.type): c for c in run.checks}


def test_matching_nested_types_pass():
    checks = _run(_SIC_CODE, "struct<code: string, description: string>")

    assert all(c.result == ResultEnum.passed for c in checks.values())


def test_a_wrong_nested_type_fails_on_its_own_line():
    checks = _run(_SIC_CODE, "struct<code: int64, description: string>")

    assert checks[("primary_sic_code.code", "field_type")].result == ResultEnum.failed
    assert checks[("primary_sic_code", "field_type")].result == ResultEnum.passed


def test_a_missing_nested_field_fails():
    checks = _run(_SIC_CODE, "struct<code: string>")

    assert checks[("primary_sic_code.description", "field_is_present")].result == ResultEnum.failed
    assert checks[("primary_sic_code.description", "field_type")].result == ResultEnum.failed


def test_a_wrong_array_element_type_fails():
    checks = _run(_SIC_CODES, "array<int64>")

    assert checks[("sic_codes[]", "field_type")].result == ResultEnum.failed


def test_nested_lines_warn_inside_a_dynamically_typed_column():
    # A json / variant / jsonb column holds a different structure per row, so the
    # declared children can be neither confirmed nor refuted.
    checks = _run(_SIC_CODE, "json")

    code = checks[("primary_sic_code.code", "field_is_present")]
    assert code.result == ResultEnum.warning
    assert "cannot be read" in code.reason


def test_nested_lines_warn_inside_an_untyped_object():
    # Snowflake's untyped OBJECT reads as a map of json: the keys differ per row.
    checks = _run(_SIC_CODE, "map<string, json>")

    assert checks[("primary_sic_code.code", "field_type")].result == ResultEnum.warning


def test_the_items_of_an_untyped_array_warn():
    checks = _run(_SIC_CODES, "array<json>")

    assert checks[("sic_codes[]", "field_type")].result == ResultEnum.warning


def test_a_map_line_checks_the_key_and_value_types():
    prop = SchemaProperty(
        name="attrs",
        logicalType="map",
        map=MapDefinition(key=SchemaProperty(logicalType="string"), value=SchemaProperty(logicalType="integer")),
    )

    assert _run(prop, "map<string, int64>")[("attrs", "field_type")].result == ResultEnum.passed
    assert _run(prop, "map<string, string>")[("attrs", "field_type")].result == ResultEnum.failed


def test_nested_lines_resolve_a_dotted_struct_path():
    prop = SchemaProperty(
        name="customer",
        logicalType="object",
        properties=[
            SchemaProperty(
                name="address", logicalType="object", properties=[SchemaProperty(name="city", logicalType="string")]
            )
        ],
    )
    checks = _run(prop, "struct<address: struct<city: string>>")

    assert checks[("customer.address.city", "field_type")].result == ResultEnum.passed


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

_SNOWFLAKE = SimpleNamespace(compiler=SimpleNamespace(dialect="snowflake"))


def _run_snowflake(
    prop: SchemaProperty, field: str, data_type: dict = _SHOW_COLUMNS_SIC_CODE, dtype: str = "map<string, json>"
):
    specs = _checks(prop, "snowflake")
    run = Run.create_run()
    run.checks = build_check_stubs(specs)
    structured_types = {prop.name.lower(): _to_property(data_type)}
    spec = _type_check(specs, field)
    server = Server(server="s", type="snowflake")
    _run_physical_type(run, _SNOWFLAKE, server, ibis.schema({prop.name: dtype}), {}, spec, structured_types)
    return next(c for c in run.checks if c.key == spec.key)


def _sic_code(**children: str) -> SchemaProperty:
    return SchemaProperty(
        name="primary_sic_code",
        physicalType="OBJECT",
        properties=[SchemaProperty(name=name, physicalType=t) for name, t in children.items()],
    )


def test_a_declared_nested_physical_type_is_checked_against_the_real_one():
    assert _run_snowflake(_sic_code(code="VARCHAR(10)"), "primary_sic_code.code").result == ResultEnum.passed


def test_an_unparameterized_nested_physical_type_matches_any_length():
    assert _run_snowflake(_sic_code(code="VARCHAR"), "primary_sic_code.code").result == ResultEnum.passed


def test_a_logical_keyword_in_the_physical_type_resolves_to_the_native_type():
    # Contracts routinely carry the logical keyword in physicalType. The dialect
    # decides what it names: 'string' is Snowflake's VARCHAR, 'boolean' is not.
    assert _run_snowflake(_sic_code(code="string"), "primary_sic_code.code").result == ResultEnum.passed
    assert _run_snowflake(_sic_code(code="boolean"), "primary_sic_code.code").result == ResultEnum.failed


def test_a_nested_number_does_not_match_a_float_column():
    # NUMBER is both a Snowflake type and an ODCS logical keyword; it must be
    # checked as the type, so it cannot silently pass on an approximate column.
    check = _run_snowflake(
        SchemaProperty(
            name="geo",
            physicalType="OBJECT",
            properties=[SchemaProperty(name="lat", logicalType="number", physicalType="NUMBER")],
        ),
        "geo.lat",
        data_type={"type": "OBJECT", "fields": [{"fieldName": "lat", "fieldType": {"type": "REAL"}}]},
    )

    assert check.result == ResultEnum.failed
    assert check.reason == "expected physical type 'NUMBER' but the column is 'FLOAT'"


def test_an_unparameterized_nested_number_matches_any_precision():
    check = _run_snowflake(
        SchemaProperty(
            name="order",
            physicalType="OBJECT",
            properties=[SchemaProperty(name="price", logicalType="number", physicalType="NUMBER")],
        ),
        "order.price",
        data_type={
            "type": "OBJECT",
            "fields": [{"fieldName": "price", "fieldType": {"type": "FIXED", "precision": 12, "scale": 2}}],
        },
    )

    assert check.result == ResultEnum.passed


def test_a_too_wide_nested_physical_type_fails():
    check = _run_snowflake(_sic_code(code="VARCHAR(64)"), "primary_sic_code.code")

    assert check.result == ResultEnum.failed
    assert check.reason == "expected physical type 'VARCHAR(64)' but the column is 'VARCHAR(10)'"


def test_the_declared_element_physical_type_of_an_array_is_checked():
    prop = SchemaProperty(name="sic_codes", physicalType="ARRAY", items=SchemaProperty(physicalType="VARCHAR(64)"))
    check = _run_snowflake(
        prop, "sic_codes[]", {"type": "ARRAY", "elementType": {"type": "TEXT", "length": 10}}, dtype="array<json>"
    )

    assert check.result == ResultEnum.failed


def test_a_nested_physical_type_foreign_to_the_dialect_warns():
    # An Oracle NCLOB declared against Snowflake can be neither confirmed nor refuted.
    check = _run_snowflake(_sic_code(code="NCLOB"), "primary_sic_code.code")

    assert check.result == ResultEnum.warning
    assert "could not be interpreted" in check.reason


def test_a_foreign_nested_physical_type_falls_back_to_the_logical_type():
    prop = SchemaProperty(
        name="primary_sic_code",
        physicalType="OBJECT",
        properties=[SchemaProperty(name="code", physicalType="NCLOB", logicalType="string")],
    )

    assert _run_snowflake(prop, "primary_sic_code.code").result == ResultEnum.passed


def test_a_map_line_compares_the_map_block_against_the_native_types():
    prop = SchemaProperty(
        name="attrs",
        logicalType="map",
        physicalType="MAP",
        map=MapDefinition(key=SchemaProperty(physicalType="VARCHAR"), value=SchemaProperty(physicalType="VARCHAR(5)")),
    )
    data_type = {"type": "MAP", "keyType": {"type": "TEXT"}, "valueType": {"type": "TEXT", "length": 10}}
    check = _run_snowflake(prop, "attrs", data_type, dtype="map<string, string>")

    assert check.result == ResultEnum.failed
    assert "attrs[value]" in check.reason


def test_a_nested_physical_type_falls_back_to_the_logical_type_when_the_catalog_cannot_be_read():
    prop = SchemaProperty(
        name="customer",
        physicalType="struct",
        logicalType="object",
        properties=[SchemaProperty(name="email", physicalType="varchar", logicalType="string")],
    )
    specs = _checks(prop, "athena")
    run = Run.create_run()
    run.checks = build_check_stubs(specs)
    spec = _type_check(specs, "customer.email")
    athena = SimpleNamespace(compiler=SimpleNamespace(dialect="athena"))
    schema = ibis.schema({"customer": "struct<email: string>"})

    _run_physical_type(run, athena, Server(server="s", type="athena"), schema, None, spec, None)

    assert next(c for c in run.checks if c.key == spec.key).result == ResultEnum.passed
