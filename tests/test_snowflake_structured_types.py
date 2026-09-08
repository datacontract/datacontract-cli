"""Offline guards for the Snowflake SHOW COLUMNS -> SchemaProperty parser.

The JSON payloads here are the real ``data_type`` blobs Snowflake returns from
``SHOW COLUMNS`` (captured from a live account), so these lock in the mapping
from structured-type nesting to the tree the field_type check recurses over.
"""

import json

from open_data_contract_standard.model import SchemaProperty, Server

from datacontract.engines.checks.check_spec import CheckSpec, MetricType
from datacontract.engines.checks.type_normalize import (
    UNKNOWN_LOGICAL_TYPE,
    schema_property_matches,
    schema_property_mismatch_reason,
)
from datacontract.engines.ibis import snowflake_structured_types
from datacontract.engines.ibis.ibis_check_execute import _run_physical_type
from datacontract.engines.ibis.snowflake_structured_types import _render_native, _to_property, has_nesting
from datacontract.model.run import Check, ResultEnum, Run


def _prop(data_type: str):
    return _to_property(json.loads(data_type))


def test_structured_object_becomes_named_properties():
    prop = _prop(
        '{"type":"OBJECT","fields":['
        '{"fieldName":"a","fieldType":{"type":"FIXED","precision":10,"scale":0}},'
        '{"fieldName":"b","fieldType":{"type":"TEXT","length":16777216}},'
        '{"fieldName":"c","fieldType":{"type":"BOOLEAN"}}]}'
    )
    assert prop.logicalType == "object"
    assert [(p.name, p.logicalType) for p in prop.properties] == [
        ("a", "number"),
        ("b", "string"),
        ("c", "boolean"),
    ]


def test_structured_array_becomes_typed_items():
    prop = _prop('{"type":"ARRAY","elementType":{"type":"FIXED","precision":10,"scale":0}}')
    assert prop.logicalType == "array"
    assert prop.items.logicalType == "number"


def test_nested_object_recurses():
    prop = _prop(
        '{"type":"OBJECT","fields":['
        '{"fieldName":"inner","fieldType":{"type":"ARRAY","elementType":{"type":"FIXED"}}},'
        '{"fieldName":"tag","fieldType":{"type":"TEXT"}}]}'
    )
    inner = {p.name: p for p in prop.properties}
    assert inner["inner"].logicalType == "array"
    assert inner["inner"].items.logicalType == "number"
    assert inner["tag"].logicalType == "string"


def test_every_node_carries_its_native_type():
    # A declared physicalType is checked against the column's real native type all
    # the way down the tree, so every recovered node keeps its rendered type.
    prop = _prop(
        '{"type":"OBJECT","fields":['
        '{"fieldName":"code","fieldType":{"type":"TEXT","length":10}},'
        '{"fieldName":"lines","fieldType":{"type":"ARRAY","elementType":{"type":"FIXED","precision":12,"scale":2}}}]}'
    )
    assert prop.physicalType == "OBJECT(code VARCHAR(10), lines ARRAY(NUMBER(12,2)))"
    children = {p.name: p for p in prop.properties}
    assert children["code"].physicalType == "VARCHAR(10)"
    assert children["lines"].physicalType == "ARRAY(NUMBER(12,2))"
    assert children["lines"].items.physicalType == "NUMBER(12,2)"


def test_leaf_token_mapping():
    assert _prop('{"type":"TIMESTAMP_NTZ"}').logicalType == "timestamp"
    assert _prop('{"type":"TIMESTAMP_LTZ"}').logicalType == "timestamp"
    assert _prop('{"type":"DATE"}').logicalType == "date"
    assert _prop('{"type":"TIME"}').logicalType == "time"
    assert _prop('{"type":"REAL"}').logicalType == "number"


def test_untyped_object_array_and_map_keep_their_base_type():
    # untyped OBJECT/ARRAY and MAP confirm their base type but carry no nesting.
    assert _to_property({"type": "OBJECT"}).properties is None
    assert _to_property({"type": "ARRAY"}).items is None
    assert _to_property({"type": "MAP", "keyType": {"type": "TEXT"}, "valueType": {"type": "FIXED"}}).properties is None
    assert _to_property({"type": "MAP"}).logicalType == "object"


def test_variant_and_unmapped_leaves_are_unknown_and_keep_their_token():
    for token in ("VARIANT", "BINARY", "GEOGRAPHY"):
        prop = _to_property({"type": token})
        assert prop.logicalType == UNKNOWN_LOGICAL_TYPE
        # the token names the type in the failure message
        assert prop.physicalType == token


def test_unverifiable_field_is_kept_not_dropped():
    # A VARIANT inside a structured OBJECT is a real, present field: it must not
    # vanish from properties, or the comparator reports it as missing.
    prop = _prop(
        '{"type":"OBJECT","fields":['
        '{"fieldName":"id","fieldType":{"type":"TEXT"}},'
        '{"fieldName":"extra","fieldType":{"type":"VARIANT"}}]}'
    )
    assert [(p.name, p.logicalType) for p in prop.properties] == [
        ("id", "string"),
        ("extra", UNKNOWN_LOGICAL_TYPE),
    ]
    expected = SchemaProperty(
        logicalType="object",
        properties=[
            SchemaProperty(name="id", logicalType="string"),
            SchemaProperty(name="extra", logicalType="object"),
        ],
    )
    assert not schema_property_matches(expected, prop)
    reason = schema_property_mismatch_reason(expected, prop)
    assert reason == (
        "field 'extra': has type 'VARIANT', but the contract specifies 'object'. "
        "A 'VARIANT' value has no verifiable logical type. "
        "If this is intentional, specify `physicalType: VARIANT`."
    )
    assert "missing" not in reason


def test_render_native_rebuilds_the_snowflake_type_string():
    node = json.loads(
        '{"type":"OBJECT","fields":['
        '{"fieldName":"a","fieldType":{"type":"FIXED","precision":38,"scale":0}},'
        '{"fieldName":"b","fieldType":{"type":"TEXT","length":16777216}},'
        '{"fieldName":"c","fieldType":{"type":"ARRAY","elementType":{"type":"BOOLEAN"}}}]}'
    )
    # matches Snowflake's own DESCRIBE TABLE rendering
    assert _render_native(node) == "OBJECT(a NUMBER(38,0), b VARCHAR(16777216), c ARRAY(BOOLEAN))"


def test_render_native_untyped_and_leaf_forms():
    assert _render_native({"type": "OBJECT"}) == "OBJECT"
    assert _render_native({"type": "ARRAY"}) == "ARRAY"
    assert _render_native({"type": "VARIANT"}) == "VARIANT"
    assert _render_native({"type": "REAL"}) == "FLOAT"
    assert _render_native({"type": "TEXT"}) == "VARCHAR"
    assert (
        _render_native({"type": "MAP", "keyType": {"type": "TEXT"}, "valueType": {"type": "FIXED"}})
        == "MAP(VARCHAR, NUMBER(38,0))"
    )


def _physical_type_check(expected: SchemaProperty, structured_types):
    """Run the physicalType check with no native type from the catalog."""
    spec = CheckSpec(
        key="k",
        category="schema",
        type="field_physical_type",
        name="check",
        model="m",
        field="s_obj",
        metric=MetricType.FIELD_PHYSICAL_TYPE,
        expected_category=expected.physicalType,
        expected_type_label=expected.physicalType,
        expected_physical_type=expected.physicalType,
        expected_schema_property=expected,
    )
    run = Run.create_run()
    run.checks = [Check(id="k", key="k", category="schema", type=spec.type, name=spec.name, model="m", field="s_obj")]
    _run_physical_type(
        run, None, None, {"S_OBJ": "map<string, json>"}, {"s_obj": "S_OBJ"}, None, spec, structured_types
    )
    return run.checks[0]


def test_physical_type_fallback_uses_the_recovered_structured_tree():
    tree = _prop(
        '{"type":"OBJECT","fields":['
        '{"fieldName":"a","fieldType":{"type":"FIXED","precision":38,"scale":0}},'
        '{"fieldName":"b","fieldType":{"type":"TEXT","length":16777216}}]}'
    )
    expected = SchemaProperty(
        name="s_obj",
        logicalType="object",
        # foreign to the Snowflake dialect, so the physical comparison yields "skip"
        physicalType="uniqueidentifier",
        properties=[SchemaProperty(name="a", logicalType="integer"), SchemaProperty(name="b", logicalType="string")],
    )
    assert _physical_type_check(expected, {"s_obj": tree}).result == ResultEnum.passed

    # without the tree, the collapsed ibis dtype makes a structured column look untyped
    check = _physical_type_check(expected, None)
    assert check.result == ResultEnum.failed


def test_physical_type_fallback_names_the_mismatched_nested_field():
    tree = _prop('{"type":"OBJECT","fields":[{"fieldName":"a","fieldType":{"type":"FIXED","precision":38,"scale":0}}]}')
    expected = SchemaProperty(
        name="s_obj",
        logicalType="object",
        physicalType="uniqueidentifier",
        properties=[SchemaProperty(name="a", logicalType="string")],
    )
    check = _physical_type_check(expected, {"s_obj": tree})
    assert check.result == ResultEnum.failed
    assert check.reason == "field 'a': expected type 'string' but got 'number'"


def test_physical_type_compares_against_the_recovered_native_type():
    # the catalog only reports 'OBJECT'; the recovered tree carries the real native type
    tree = _prop(
        '{"type":"OBJECT","fields":['
        '{"fieldName":"a","fieldType":{"type":"FIXED","precision":38,"scale":0}},'
        '{"fieldName":"b","fieldType":{"type":"TEXT","length":16777216}}]}'
    )
    tree.physicalType = "OBJECT(a NUMBER(38,0), b VARCHAR(16777216))"

    declared = SchemaProperty(name="s_obj", logicalType="object", physicalType=tree.physicalType)
    check = _physical_type_check(declared, {"s_obj": tree})
    assert check.result == ResultEnum.passed
    assert check.diagnostics["actual"] == "OBJECT(a NUMBER(38,0), b VARCHAR(16777216))"

    wrong = SchemaProperty(name="s_obj", logicalType="object", physicalType="OBJECT(a NUMBER(38,0))")
    check = _physical_type_check(wrong, {"s_obj": tree})
    assert check.result == ResultEnum.failed
    assert "but the column is 'OBJECT(a NUMBER(38,0), b VARCHAR(16777216))'" in check.reason


def test_fetch_keeps_unverifiable_leaves_and_drops_scalars(monkeypatch):
    rows = [
        ("t", "s", "V", '{"type":"VARIANT"}'),
        ("t", "s", "N", '{"type":"FIXED","precision":38,"scale":0}'),
        ("t", "s", "U_OBJ", '{"type":"OBJECT"}'),
        ("t", "s", "S_ARR", '{"type":"ARRAY","elementType":{"type":"TEXT"}}'),
    ]
    monkeypatch.setattr(snowflake_structured_types, "_rows", lambda con, query: rows)
    result = snowflake_structured_types.fetch_structured_types(None, Server(database="d", schema="s"), "t")

    # a VARIANT is unverifiable but must name itself; a scalar and an untyped OBJECT
    # add nothing the collapsed ibis dtype does not already say
    assert sorted(result) == ["s_arr", "v"]
    assert result["v"].logicalType == UNKNOWN_LOGICAL_TYPE
    assert result["v"].physicalType == "VARIANT"
    assert result["s_arr"].physicalType == "ARRAY(VARCHAR)"


def test_has_nesting_only_for_structured():
    assert has_nesting(_prop('{"type":"OBJECT","fields":[{"fieldName":"a","fieldType":{"type":"TEXT"}}]}'))
    assert has_nesting(_prop('{"type":"ARRAY","elementType":{"type":"TEXT"}}'))
    assert not has_nesting(_to_property({"type": "OBJECT"}))
    assert not has_nesting(_to_property({"type": "ARRAY"}))
    assert not has_nesting(_to_property({"type": "VARIANT"}))
