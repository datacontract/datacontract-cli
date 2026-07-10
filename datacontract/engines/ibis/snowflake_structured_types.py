"""Rebuild Snowflake structured OBJECT/ARRAY nesting, which ibis collapses, from SHOW COLUMNS."""

from __future__ import annotations

import json

from open_data_contract_standard.model import SchemaProperty, Server

from datacontract.engines.checks.type_normalize import UNKNOWN_LOGICAL_TYPE
from datacontract.engines.ibis.native_type import _quote, _rows

# SHOW COLUMNS leaf ``type`` tokens -> ODCS logical type. FIXED and REAL both map
# to "number" (the comparator treats integer/number as compatible). Tokens not
# listed (BINARY, GEOGRAPHY, VARIANT, …) carry no verifiable logical type.
_LEAF_TYPES = {
    "FIXED": "number",
    "REAL": "number",
    "TEXT": "string",
    "BOOLEAN": "boolean",
    "DATE": "date",
    "TIME": "time",
    "TIMESTAMP_NTZ": "timestamp",
    "TIMESTAMP_LTZ": "timestamp",
    "TIMESTAMP_TZ": "timestamp",
}


def _to_property(node: dict) -> SchemaProperty:
    """Convert one ``data_type`` JSON node to a ``SchemaProperty``."""
    node_type = node.get("type")
    if node_type == "OBJECT":
        fields = node.get("fields")
        if not fields:
            # untyped OBJECT: same shape as the collapsed ibis map
            return SchemaProperty(logicalType="object", properties=None)
        properties = []
        for field in fields:
            name = field.get("fieldName")
            if not name:
                continue
            child = _to_property(field.get("fieldType") or {})
            properties.append(
                SchemaProperty(
                    name=name,
                    logicalType=child.logicalType,
                    physicalType=child.physicalType,
                    items=child.items,
                    properties=child.properties,
                )
            )
        return SchemaProperty(logicalType="object", properties=properties or None)
    if node_type == "ARRAY":
        element = node.get("elementType")
        # untyped ARRAY: no element type to recurse into
        return SchemaProperty(logicalType="array", items=_to_property(element) if element else None)
    if node_type == "MAP":
        # dynamic keys can't be matched to named contract properties
        return SchemaProperty(logicalType="object", properties=None)
    logical = _LEAF_TYPES.get(node_type)
    if logical:
        return SchemaProperty(logicalType=logical)
    # VARIANT, BINARY, GEOGRAPHY, …: keep the Snowflake token for the failure message
    return SchemaProperty(logicalType=UNKNOWN_LOGICAL_TYPE, physicalType=node_type)


def has_nesting(prop: SchemaProperty) -> bool:
    """True only when the property is a structured OBJECT/ARRAY worth substituting."""
    return bool(prop.properties) or prop.items is not None


def _render_native(node: dict) -> str:
    """Render one ``data_type`` JSON node back to its Snowflake type string."""
    node_type = node.get("type")
    if node_type == "OBJECT":
        fields = node.get("fields")
        if not fields:
            return "OBJECT"
        rendered = [
            f"{field['fieldName']} {_render_native(field.get('fieldType') or {})}"
            for field in fields
            if field.get("fieldName")
        ]
        return "OBJECT({})".format(", ".join(rendered)) if rendered else "OBJECT"
    if node_type == "ARRAY":
        element = node.get("elementType")
        return "ARRAY({})".format(_render_native(element)) if element else "ARRAY"
    if node_type == "MAP":
        key, value = node.get("keyType"), node.get("valueType")
        if key and value:
            return "MAP({}, {})".format(_render_native(key), _render_native(value))
        return "MAP"
    if node_type == "FIXED":
        return "NUMBER({},{})".format(node.get("precision", 38), node.get("scale", 0))
    if node_type == "REAL":
        return "FLOAT"
    if node_type == "TEXT":
        length = node.get("length")
        return f"VARCHAR({length})" if length is not None else "VARCHAR"
    return str(node_type)


def fetch_structured_types(con, server: Server, table_name: str) -> dict[str, SchemaProperty] | None:
    """Return ``{column_name_lower: SchemaProperty}`` for the columns whose real type
    the collapsed ibis dtype does not convey: structured OBJECT/ARRAY, and leaves with
    no verifiable logical type. Other columns are omitted. Any failure returns ``None``.
    """
    quoted_table = '"{}"'.format(table_name.replace('"', '""'))
    path = ".".join(part for part in (server.database, server.schema_, quoted_table) if part)
    identifier = "IDENTIFIER('{}')".format(_quote(path))
    rows = _rows(con, f"SHOW COLUMNS IN TABLE {identifier}")
    if not rows:
        return None

    # SHOW COLUMNS columns: table_name, schema_name, column_name, data_type, ...
    result: dict[str, SchemaProperty] = {}
    for row in rows:
        column_name, data_type = row[2], row[3]
        if not column_name or not data_type:
            continue
        try:
            node = json.loads(data_type)
        except (TypeError, ValueError):
            continue
        prop = _to_property(node)
        if has_nesting(prop):
            # the real native type, for diagnostics the collapsed ibis dtype can't give
            prop.physicalType = _render_native(node)
        elif prop.logicalType != UNKNOWN_LOGICAL_TYPE:
            # scalars and untyped OBJECT/ARRAY: the collapsed ibis dtype says the same
            continue
        # an unverifiable leaf (VARIANT, GEOGRAPHY, …) keeps its Snowflake token, which
        # the ibis dtype renders as the useless 'json'
        result[str(column_name).lower()] = prop
    return result or None
