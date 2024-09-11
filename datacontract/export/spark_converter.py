from pyspark.sql import types
from datacontract.model.data_contract_specification import (
    DataContractSpecification,
    Model,
    Field,
)
from datacontract.export.exporter import Exporter


class SparkExporter(Exporter):
    """
    Exporter class for exporting data contracts to Spark schemas.
    """

    def export(
        self,
        data_contract: DataContractSpecification,
        model,
        server,
        sql_server_type,
        export_args,
    ) -> dict[str, types.StructType]:
        """
        Export the given data contract to Spark schemas.

        Args:
            data_contract (DataContractSpecification): The data contract specification.
            model: Not used in this implementation.
            server: Not used in this implementation.
            sql_server_type: Not used in this implementation.
            export_args: Additional arguments for export.

        Returns:
            dict[str, types.StructType]: A dictionary mapping model names to their corresponding Spark schemas.
        """
        return to_spark(data_contract)


def to_spark(contract: DataContractSpecification) -> str:
    """
    Converts a DataContractSpecification into a Spark schema string.

    Args:
        contract (DataContractSpecification): The data contract specification containing models.

    Returns:
        str: A string representation of the Spark schema for each model in the contract.
    """
    return "\n\n".join(
        f"{model_name} = {print_schema(to_spark_schema(model))}" for model_name, model in contract.models.items()
    )


def to_spark_dict(contract: DataContractSpecification) -> dict[str, types.StructType]:
    """
    Convert a data contract specification to Spark schemas.

    Args:
        contract (DataContractSpecification): The data contract specification.

    Returns:
        dict[str, types.StructType]: A dictionary mapping model names to their corresponding Spark schemas.
    """
    return {model_name: to_spark_schema(model) for model_name, model in contract.models.items()}


def to_spark_schema(model: Model) -> types.StructType:
    """
    Convert a model to a Spark schema.

    Args:
        model (Model): The model to convert.

    Returns:
        types.StructType: The corresponding Spark schema.
    """
    return to_struct_type(model.fields)


def to_struct_type(fields: dict[str, Field]) -> types.StructType:
    """
    Convert a dictionary of fields to a Spark StructType.

    Args:
        fields (dict[str, Field]): The fields to convert.

    Returns:
        types.StructType: The corresponding Spark StructType.
    """
    struct_fields = [to_struct_field(field, field_name) for field_name, field in fields.items()]
    return types.StructType(struct_fields)


def to_struct_field(field: Field, field_name: str) -> types.StructField:
    """
    Convert a field to a Spark StructField.

    Args:
        field (Field): The field to convert.
        field_name (str): The name of the field.

    Returns:
        types.StructField: The corresponding Spark StructField.
    """
    data_type = to_data_type(field)
    return types.StructField(name=field_name, dataType=data_type, nullable=not field.required)


def to_data_type(field: Field) -> types.DataType:
    """
    Convert a field to a Spark DataType.

    Args:
        field (Field): The field to convert.

    Returns:
        types.DataType: The corresponding Spark DataType.
    """
    field_type = field.type
    if field_type is None or field_type in ["null"]:
        return types.NullType()
    if field_type == "array":
        return types.ArrayType(to_data_type(field.items))
    if field_type in ["object", "record", "struct"]:
        return types.StructType(to_struct_type(field.fields))
    if field_type == "map":
        return types.MapType(to_data_type(field.keys), to_data_type(field.values))
    if field_type in ["string", "varchar", "text"]:
        return types.StringType()
    if field_type in ["number", "decimal", "numeric"]:
        return types.DecimalType(precision=field.precision, scale=field.scale)
    if field_type in ["integer", "int"]:
        return types.IntegerType()
    if field_type == "long":
        return types.LongType()
    if field_type == "float":
        return types.FloatType()
    if field_type == "double":
        return types.DoubleType()
    if field_type == "boolean":
        return types.BooleanType()
    if field_type in ["timestamp", "timestamp_tz"]:
        return types.TimestampType()
    if field_type == "timestamp_ntz":
        return types.TimestampNTZType()
    if field_type == "date":
        return types.DateType()
    if field_type == "bytes":
        return types.BinaryType()
    return types.BinaryType()


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
        return "\n".join([f'{"    " * level}{line}' for line in text.split("\n")])

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
