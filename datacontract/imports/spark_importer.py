from pyspark.sql import DataFrame, SparkSession, types
from datacontract.imports.importer import Importer
from datacontract.model.data_contract_specification import (
    DataContractSpecification,
    Model,
    Field,
    Server,
)


class SparkImporter(Importer):
    def import_source(
        self,
        data_contract_specification: DataContractSpecification,
        source: str,
        import_args: dict,
    ) -> DataContractSpecification:
        """
        Imports data from a Spark source into the data contract specification.

        Args:
            data_contract_specification: The data contract specification object.
            source: The source string indicating the Spark tables to read.
            import_args: Additional arguments for the import process.

        Returns:
            dict: The updated data contract specification.
        """
        return import_spark(data_contract_specification, source)


def import_spark(data_contract_specification: DataContractSpecification, source: str) -> DataContractSpecification:
    """
    Reads Spark tables and updates the data contract specification with their schemas.

    Args:
        data_contract_specification: The data contract specification to update.
        source: A comma-separated string of Spark temporary views to read.

    Returns:
        DataContractSpecification: The updated data contract specification.
    """
    spark = SparkSession.builder.getOrCreate()
    data_contract_specification.servers["local"] = Server(type="dataframe")
    for temp_view in source.split(","):
        temp_view = temp_view.strip()
        df = spark.read.table(temp_view)
        data_contract_specification.models[temp_view] = import_from_spark_df(df)
    return data_contract_specification


def import_from_spark_df(df: DataFrame) -> Model:
    """
    Converts a Spark DataFrame into a Model.

    Args:
        df: The Spark DataFrame to convert.

    Returns:
        Model: The generated data contract model.
    """
    model = Model()
    schema = df.schema

    for field in schema:
        model.fields[field.name] = _field_from_struct_type(field)

    return model


def _field_from_struct_type(spark_field: types.StructField) -> Field:
    """
    Converts a Spark StructField into a Field object for the data contract.

    Args:
        spark_field: The Spark StructField to convert.

    Returns:
        Field: The generated Field object.
    """
    field = Field()
    field.required = not spark_field.nullable
    field.description = spark_field.metadata.get("comment")

    return _type_from_data_type(field, spark_field.dataType)


def _type_from_data_type(field: Field, spark_type: types.DataType) -> Field:
    """
    Maps Spark data types to the Data Contract type system and updates the field.

    Args:
        field: The Field object to update.
        spark_type: The Spark data type to map.

    Returns:
        Field: The updated Field object.
    """
    field.type = _data_type_from_spark(spark_type)

    if field.type == "array":
        field.items = _type_from_data_type(Field(required=not spark_type.containsNull), spark_type.elementType)

    elif field.type == "map":
        field.keys = _type_from_data_type(Field(required=True), spark_type.keyType)
        field.values = _type_from_data_type(Field(required=not spark_type.valueContainsNull), spark_type.valueType)

    elif field.type == "struct":
        field.fields = {sf.name: _field_from_struct_type(sf) for sf in spark_type.fields}

    return field


def _data_type_from_spark(spark_type: types.DataType) -> str:
    """
    Maps Spark data types to the Data Contract type system.

    Args:
        spark_type: The Spark data type to map.

    Returns:
        str: The corresponding Data Contract type.
    """
    if isinstance(spark_type, types.StringType):
        return "string"
    elif isinstance(spark_type, (types.IntegerType, types.ShortType)):
        return "integer"
    elif isinstance(spark_type, types.LongType):
        return "long"
    elif isinstance(spark_type, types.FloatType):
        return "float"
    elif isinstance(spark_type, types.DoubleType):
        return "double"
    elif isinstance(spark_type, types.StructType):
        return "struct"
    elif isinstance(spark_type, types.ArrayType):
        return "array"
    elif isinstance(spark_type, types.MapType):
        return "map"
    elif isinstance(spark_type, types.TimestampType):
        return "timestamp"
    elif isinstance(spark_type, types.TimestampNTZType):
        return "timestamp_ntz"
    elif isinstance(spark_type, types.DateType):
        return "date"
    elif isinstance(spark_type, types.BooleanType):
        return "boolean"
    elif isinstance(spark_type, types.BinaryType):
        return "bytes"
    elif isinstance(spark_type, types.DecimalType):
        return "decimal"
    elif isinstance(spark_type, types.NullType):
        return "null"
    elif isinstance(spark_type, types.VarcharType):
        return "varchar"
    else:
        raise ValueError(f"Unsupported Spark type: {spark_type}")
