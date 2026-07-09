"""Recover Snowflake structured-type nesting that ibis collapses.

ibis reflects a Snowflake structured ``OBJECT(a INT, b TEXT)`` as
``map<string, json>`` (indistinguishable from an untyped ``OBJECT``) and
``ARRAY(NUMBER)`` as ``array<json>``, discarding the nested field and element
types. Snowflake still exposes them through ``SHOW COLUMNS``, whose ``data_type``
column is a recursive JSON tree. This module reads that tree and rebuilds a
``SchemaProperty`` so the ``field_type`` check can verify nested types.

Best-effort: any failure returns ``None`` so the caller falls back to the
collapsed ibis dtype.
"""

from __future__ import annotations

import json
import logging
from typing import Optional

from open_data_contract_standard.model import SchemaProperty, Server

logger = logging.getLogger(__name__)

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


def _to_property(node: dict) -> Optional[SchemaProperty]:
    """Convert one ``data_type`` JSON node to a ``SchemaProperty``.

    Returns ``None`` when the node carries no structure the contract can be
    verified against: an untyped/empty ``OBJECT`` or ``ARRAY``, a ``MAP`` (dynamic
    keys), a ``VARIANT``, or an unmapped leaf token.
    """
    node_type = node.get("type")
    if node_type == "OBJECT":
        fields = node.get("fields")
        if not fields:
            return None  # untyped/semi-structured OBJECT
        properties = []
        for field in fields:
            child = _to_property(field.get("fieldType") or {})
            name = field.get("fieldName")
            if name and child is not None:
                properties.append(
                    SchemaProperty(
                        name=name,
                        logicalType=child.logicalType,
                        items=child.items,
                        properties=child.properties,
                    )
                )
        return SchemaProperty(logicalType="object", properties=properties or None)
    if node_type == "ARRAY":
        element = node.get("elementType")
        if not element:
            return None  # untyped/semi-structured ARRAY
        return SchemaProperty(logicalType="array", items=_to_property(element))
    if node_type == "MAP":
        return None  # dynamic keys can't be matched to named contract properties
    logical = _LEAF_TYPES.get(node_type)
    return SchemaProperty(logicalType=logical) if logical else None


def _has_nesting(prop: Optional[SchemaProperty]) -> bool:
    """True only when the property is a structured OBJECT/ARRAY worth substituting."""
    return prop is not None and (bool(prop.properties) or prop.items is not None)


def fetch_structured_types(con, server: Server, model: str) -> Optional[dict[str, SchemaProperty]]:
    """Return ``{column_name_lower: SchemaProperty}`` for the Snowflake columns of
    ``model`` whose declared structured type carries nested detail.

    Columns without recoverable nesting (scalars, plain VARIANT/OBJECT/ARRAY,
    MAP) are omitted, so the caller keeps the collapsed ibis dtype for them.
    """
    identifier = ".".join(part for part in (server.database, server.schema_, model) if part)
    try:
        cursor = con.raw_sql(f"SHOW COLUMNS IN TABLE {identifier}")
    except Exception as e:
        logger.debug("SHOW COLUMNS failed for %s: %s", identifier, e)
        return None
    try:
        rows = list(cursor.fetchall())
    except Exception as e:
        logger.debug("could not read SHOW COLUMNS rows for %s: %s", identifier, e)
        return None
    finally:
        try:
            cursor.close()
        except Exception:
            pass

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
        if _has_nesting(prop):
            result[str(column_name).lower()] = prop
    return result or None
