"""Map an ibis dtype to the coarse category used by ``field_type`` checks."""

from __future__ import annotations


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
