"""Offline guards for the Snowflake SHOW COLUMNS -> SchemaProperty parser.

The JSON payloads here are the real ``data_type`` blobs Snowflake returns from
``SHOW COLUMNS`` (captured from a live account), so these lock in the mapping
from structured-type nesting to the tree the field_type check recurses over.
"""

import json

from datacontract.engines.ibis.snowflake_structured_types import _has_nesting, _to_property


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


def test_leaf_token_mapping():
    assert _prop('{"type":"TIMESTAMP_NTZ"}').logicalType == "timestamp"
    assert _prop('{"type":"TIMESTAMP_LTZ"}').logicalType == "timestamp"
    assert _prop('{"type":"DATE"}').logicalType == "date"
    assert _prop('{"type":"TIME"}').logicalType == "time"
    assert _prop('{"type":"REAL"}').logicalType == "number"


def test_opaque_types_yield_no_tree():
    # plain VARIANT, untyped OBJECT/ARRAY, and MAP carry nothing to recurse into.
    assert _to_property({"type": "VARIANT"}) is None
    assert _to_property({"type": "OBJECT"}) is None
    assert _to_property({"type": "ARRAY"}) is None
    assert _to_property({"type": "MAP", "keyType": {"type": "TEXT"}, "valueType": {"type": "FIXED"}}) is None
    assert _to_property({"type": "BINARY"}) is None


def test_has_nesting_only_for_structured():
    assert _has_nesting(_prop('{"type":"OBJECT","fields":[{"fieldName":"a","fieldType":{"type":"TEXT"}}]}'))
    assert _has_nesting(_prop('{"type":"ARRAY","elementType":{"type":"TEXT"}}'))
    assert not _has_nesting(_to_property({"type": "OBJECT"}))
    assert not _has_nesting(None)
