"""Map an ibis dtype to the coarse category used by ``field_type`` checks."""

from __future__ import annotations

from ibis.expr.datatypes import DataType
from open_data_contract_standard.model import SchemaProperty


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


def ibis_dtype_to_schema_property(dtype: DataType) -> SchemaProperty | None:
    """Map an ibis DataType to a SchemaProperty for structural type comparison.

    Returns a ``SchemaProperty`` with ``logicalType`` set to one of the 9 ODCS
    categories, recursively populating ``properties`` for structs and ``items``
    for arrays. Returns ``None`` for unsupported types (binary, map, null, etc.)
    so the caller can skip comparison rather than raising a false failure.
    """
    try:
        if dtype.is_boolean():
            return SchemaProperty(logicalType="boolean")
        if dtype.is_integer():
            return SchemaProperty(logicalType="integer")
        if dtype.is_decimal() or dtype.is_floating():
            return SchemaProperty(logicalType="number")
        if dtype.is_string():
            return SchemaProperty(logicalType="string")
        if dtype.is_timestamp():
            return SchemaProperty(logicalType="timestamp")
        if dtype.is_date():
            return SchemaProperty(logicalType="date")
        if dtype.is_time():
            return SchemaProperty(logicalType="time")
        if dtype.is_struct():
            properties = []
            for field_name, ftype in dtype.fields.items():
                child = ibis_dtype_to_schema_property(ftype)
                if child is not None:
                    properties.append(
                        SchemaProperty(
                            name=field_name,
                            logicalType=child.logicalType,
                            items=child.items,
                            properties=child.properties,
                        )
                    )
            return SchemaProperty(
                logicalType="object", properties=properties if properties else None
            )
        if dtype.is_array():
            element = ibis_dtype_to_schema_property(dtype.value_type)
            return SchemaProperty(logicalType="array", items=element)
    except AttributeError:
        return None
    return None
