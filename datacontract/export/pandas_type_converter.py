"""
Module for converting data contract field types to corresponding pandas data types.
"""

from typing import Optional

from open_data_contract_standard.model import SchemaProperty


def _get_type(prop: SchemaProperty) -> Optional[str]:
    """Get the type from a schema property."""
    if prop.logicalType:
        return prop.logicalType
    if prop.physicalType:
        return prop.physicalType
    return None


def convert_to_pandas_type(prop: SchemaProperty) -> str:
    """
    Convert a data contract field type to the equivalent pandas data type.

    Parameters:
    ----------
    prop : SchemaProperty
        A SchemaProperty object containing metadata about the data type of the field.

    Returns:
    -------
    str
        The corresponding pandas data type as a string.
    """
    field_type = _get_type(prop)

    if field_type is None:
        return "object"

    field_type_lower = field_type.lower()

    if field_type_lower in ["string", "varchar", "text"]:
        return "str"
    if field_type_lower in ["integer", "int"]:
        return "int32"
    if field_type_lower == "long":
        return "int64"
    if field_type_lower == "float":
        return "float32"
    if field_type_lower in ["number", "decimal", "numeric", "double"]:
        return "float64"
    if field_type_lower == "boolean":
        return "bool"
    if field_type_lower in ["timestamp", "timestamp_tz", "timestamp_ntz", "date"]:
        return "datetime64[ns]"
    if field_type_lower == "bytes":
        return "object"
    return "object"
