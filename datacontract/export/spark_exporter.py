import json
from typing import List, Optional

from pyspark.sql import types

from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, SchemaProperty

from datacontract.export.exporter import Exporter


class SparkExporter(Exporter):
    """
    Exporter class for exporting data contracts to Spark schemas.
    """

    def export(
        self,
        data_contract: OpenDataContractStandard,
        schema_name,
        server,
        sql_server_type,
        export_args,
    ) -> dict[str, types.StructType]:
        """
        Export the given data contract to Spark schemas.

        Args:
            data_contract (OpenDataContractStandard): The data contract specification.
            schema_name: The name of the schema to export, or 'all' for all schemas.
            server: Not used in this implementation.
            sql_server_type: Not used in this implementation.
            export_args: Additional arguments for export.

        Returns:
            dict[str, types.StructType]: A dictionary mapping model names to their corresponding Spark schemas.
        """
        return to_spark(data_contract)


def to_spark(contract: OpenDataContractStandard) -> str:
    """
    Converts an OpenDataContractStandard into a Spark schema string.

    Args:
        contract (OpenDataContractStandard): The data contract specification containing models.

    Returns:
        str: A string representation of the Spark schema for each model in the contract.
    """
    result = []
    if contract.schema_:
        for schema_obj in contract.schema_:
            result.append(f"{schema_obj.name} = {print_schema(to_spark_schema(schema_obj))}")
    return "\n\n".join(result)


def to_spark_dict(contract: OpenDataContractStandard) -> dict[str, types.StructType]:
    """
    Convert a data contract specification to Spark schemas.

    Args:
        contract (OpenDataContractStandard): The data contract specification.

    Returns:
        dict[str, types.StructType]: A dictionary mapping model names to their corresponding Spark schemas.
    """
    result = {}
    if contract.schema_:
        for schema_obj in contract.schema_:
            result[schema_obj.name] = to_spark_schema(schema_obj)
    return result


def to_spark_schema(schema_obj: SchemaObject) -> types.StructType:
    """
    Convert a schema object to a Spark schema.

    Args:
        schema_obj (SchemaObject): The schema object to convert.

    Returns:
        types.StructType: The corresponding Spark schema.
    """
    return to_struct_type(schema_obj.properties or [])


def to_struct_type(properties: List[SchemaProperty]) -> types.StructType:
    """
    Convert a list of properties to a Spark StructType.

    Args:
        properties (List[SchemaProperty]): The properties to convert.

    Returns:
        types.StructType: The corresponding Spark StructType.
    """
    struct_fields = [to_struct_field(prop) for prop in properties]
    return types.StructType(struct_fields)


def _get_type(prop: SchemaProperty) -> Optional[str]:
    """Get the logical type from a schema property."""
    return prop.logicalType


def _get_logical_type_option(prop: SchemaProperty, key: str):
    """Get a logical type option value."""
    if prop.logicalTypeOptions is None:
        return None
    return prop.logicalTypeOptions.get(key)


def to_struct_field(prop: SchemaProperty) -> types.StructField:
    """
    Convert a property to a Spark StructField.

    Args:
        prop (SchemaProperty): The property to convert.

    Returns:
        types.StructField: The corresponding Spark StructField.
    """
    data_type = to_spark_data_type(prop)
    metadata = to_spark_metadata(prop)
    return types.StructField(name=prop.name, dataType=data_type, nullable=not prop.required, metadata=metadata)


def to_spark_data_type(prop: SchemaProperty) -> types.DataType:
    """
    Convert a property to a Spark DataType.

    Args:
        prop (SchemaProperty): The property to convert.

    Returns:
        types.DataType: The corresponding Spark DataType.
    """
    logical_type = _get_type(prop)
    physical_type = prop.physicalType.lower() if prop.physicalType else None

    # Check for null type
    if logical_type is None and physical_type is None:
        return types.NullType()
    if physical_type == "null":
        return types.NullType()

    # Handle array type
    if logical_type == "array":
        if prop.items:
            return types.ArrayType(to_spark_data_type(prop.items))
        return types.ArrayType(types.StringType())

    # Handle object/struct type
    if logical_type == "object" or physical_type in ["object", "record", "struct"]:
        if prop.properties:
            return types.StructType(to_struct_type(prop.properties))
        return types.StructType([])

    # Handle map type (check physical type)
    if physical_type == "map":
        # For ODCS, maps might be represented differently - check for keys/values properties
        # For now, default to string -> string map
        return types.MapType(types.StringType(), types.StringType())

    # Handle variant type
    if physical_type == "variant":
        return types.VariantType()

    # Check physical type first for specific SQL types
    if physical_type:
        if physical_type in ["string", "varchar", "text", "char", "nvarchar"]:
            return types.StringType()
        if physical_type in ["decimal", "numeric"]:
            precision = _get_logical_type_option(prop, "precision") or 38
            scale = _get_logical_type_option(prop, "scale") or 0
            return types.DecimalType(precision=precision, scale=scale)
        if physical_type in ["integer", "int", "int32"]:
            return types.IntegerType()
        if physical_type in ["long", "bigint", "int64"]:
            return types.LongType()
        if physical_type in ["float", "real", "float32"]:
            return types.FloatType()
        if physical_type in ["double", "float64"]:
            return types.DoubleType()
        if physical_type in ["boolean", "bool"]:
            return types.BooleanType()
        if physical_type in ["timestamp", "timestamp_tz"]:
            return types.TimestampType()
        if physical_type == "timestamp_ntz":
            return types.TimestampNTZType()
        if physical_type == "date":
            return types.DateType()
        if physical_type in ["bytes", "binary", "bytea"]:
            return types.BinaryType()

    # Fall back to logical type
    match logical_type:
        case "string":
            return types.StringType()
        case "number":
            precision = _get_logical_type_option(prop, "precision") or 38
            scale = _get_logical_type_option(prop, "scale") or 0
            return types.DecimalType(precision=precision, scale=scale)
        case "integer":
            return types.LongType()
        case "boolean":
            return types.BooleanType()
        case "date":
            return types.DateType()
        case "timestamp":
            return types.TimestampType()
        case _:
            return types.StringType()  # default if no condition is met


def to_spark_metadata(prop: SchemaProperty) -> dict[str, str]:
    """
    Convert a property to a Spark metadata dictionary.

    Args:
        prop (SchemaProperty): The property to convert.

    Returns:
        dict: dictionary that can be supplied to Spark as metadata for a StructField
    """
    metadata = {}
    if prop.description:
        metadata["comment"] = prop.description

    return metadata


def print_schema(dtype: types.DataType) -> str:
    """
    Converts a PySpark DataType schema to its equivalent code representation.

    Args:
        dtype (types.DataType): The PySpark DataType schema to be converted.

    Returns:
        str: The code representation of the PySpark DataType schema.
    """

    def indent(text: str, level: int) -> str:
        """
        Indents each line of the given text by a specified number of levels.

        Args:
            text (str): The text to be indented.
            level (int): The number of indentation levels.

        Returns:
            str: The indented text.
        """
        return "\n".join([f"{'    ' * level}{line}" for line in text.split("\n")])

    def repr_column(column: types.StructField) -> str:
        """
        Converts a PySpark StructField to its code representation.

        Args:
            column (types.StructField): The StructField to be converted.

        Returns:
            str: The code representation of the StructField.
        """
        name = f'"{column.name}"'
        data_type = indent(print_schema(column.dataType), 1)
        nullable = indent(f"{column.nullable}", 1)
        if column.metadata:
            metadata = indent(f"{json.dumps(column.metadata)}", 1)
            return f"StructField({name},\n{data_type},\n{nullable},\n{metadata}\n)"
        else:
            return f"StructField({name},\n{data_type},\n{nullable}\n)"

    def format_struct_type(struct_type: types.StructType) -> str:
        """
        Converts a PySpark StructType to its code representation.

        Args:
            struct_type (types.StructType): The StructType to be converted.

        Returns:
            str: The code representation of the StructType.
        """
        fields = ",\n".join([indent(repr_column(field), 1) for field in struct_type.fields])
        return f"StructType([\n{fields}\n])"

    if isinstance(dtype, types.StructType):
        return format_struct_type(dtype)
    elif isinstance(dtype, types.ArrayType):
        return f"ArrayType({print_schema(dtype.elementType)})"
    elif isinstance(dtype, types.MapType):
        return f"MapType(\n{indent(print_schema(dtype.keyType), 1)}, {print_schema(dtype.valueType)})"
    elif isinstance(dtype, types.DecimalType):
        return f"DecimalType({dtype.precision}, {dtype.scale})"
    else:
        dtype_str = str(dtype)
        return dtype_str if dtype_str.endswith("()") else f"{dtype_str}()"
