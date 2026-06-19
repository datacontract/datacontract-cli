"""Map an ibis dtype to the coarse category used by ``field_type`` checks."""

from __future__ import annotations

from ibis.expr.datatypes import DataType


def ibis_dtype_category(dtype) -> str:
    """Return the normalized category for an ibis ``DataType``.

    Order matters: boolean is checked before integer (some engines model bool as
    a 1-bit int), and decimal before floating.
    """
    try:
        if dtype.is_boolean():
            return "boolean"
        if dtype.is_integer():
            return "integer"
        if dtype.is_decimal():
            return "decimal"
        if dtype.is_floating():
            return "float"
        if dtype.is_string():
            return "string"
        if dtype.is_timestamp():
            return "timestamp"
        if dtype.is_date():
            return "date"
        if dtype.is_time():
            return "time"
        if dtype.is_binary():
            return "binary"
        if dtype.is_struct():
            return "struct"
        if dtype.is_array():
            return "array"
        if dtype.is_map():
            return "map"
        if dtype.is_null():
            return "null"
    except AttributeError:
        return "other"
    return "other"


def ibis_dtype_to_logical_type(dtype: DataType) -> str | None:
    """Map an ibis DataType to a flat logical type string.

    Returns one of the 9 allowed base types (``boolean``, ``integer``, ``number``,
    ``string``, ``timestamp``, ``date``, ``time``, ``object``, ``array``), with
    recursive ``<...>`` details for struct and array types.

    Returns ``None`` for unsupported types (binary, map, null, etc.) so the
    caller can omit the field from comparisons rather than raising a false failure.
    """
    try:
        if dtype.is_boolean():
            return "boolean"
        if dtype.is_integer():
            return "integer"
        if dtype.is_decimal() or dtype.is_floating():
            return "number"
        if dtype.is_string():
            return "string"
        if dtype.is_timestamp():
            return "timestamp"
        if dtype.is_date():
            return "date"
        if dtype.is_time():
            return "time"
        if dtype.is_struct():
            field_parts = []
            for name, ftype in dtype.fields.items():
                mapped = ibis_dtype_to_logical_type(ftype)
                if mapped is not None:
                    field_parts.append(f"{name}:{mapped}")
            if field_parts:
                return "object<" + ",".join(field_parts) + ">"
            return "object"
        if dtype.is_array():
            element = ibis_dtype_to_logical_type(dtype.value_type)
            if element is not None:
                return f"array<{element}>"
            return "array"
    except AttributeError:
        return None
    return None
