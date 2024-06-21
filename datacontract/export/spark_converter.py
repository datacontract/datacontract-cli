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
        self, data_contract: DataContractSpecification, model, server, sql_server_type, export_args
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


def to_spark(contract: DataContractSpecification) -> dict[str, types.StructType]:
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
    if field_type in ["string", "varchar", "text"]:
        return types.StringType()
    if field_type in ["number", "decimal", "numeric"]:
        return types.DecimalType()
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
