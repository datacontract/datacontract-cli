"""
Module for converting data contract field types to corresponding pandas data types.
"""

from datacontract.model.data_contract_specification import Field


def convert_to_pandas_type(field: Field) -> str:
    """
    Convert a data contract field type to the equivalent pandas data type.

    Parameters:
    ----------
    field : Field
        A Field object containing metadata about the data type of the field.

    Returns:
    -------
    str
        The corresponding pandas data type as a string.
    """
    field_type = field.type

    if field_type in ["string", "varchar", "text"]:
        return "str"
    if field_type in ["integer", "int"]:
        return "int32"
    if field_type == "long":
        return "int64"
    if field_type == "float":
        return "float32"
    if field_type in ["number", "decimal", "numeric", "double"]:
        return "float64"
    if field_type == "boolean":
        return "bool"
    if field_type in ["timestamp", "timestamp_tz", "timestamp_ntz", "date"]:
        return "datetime64[ns]"
    if field_type == "bytes":
        return "object"
    return "object"
