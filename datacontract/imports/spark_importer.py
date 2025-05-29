import logging

from databricks.sdk import WorkspaceClient
from pyspark.sql import DataFrame, SparkSession, types

from datacontract.imports.importer import Importer
from datacontract.model.data_contract_specification import (
    DataContractSpecification,
    Field,
    Model,
    Server,
)

logger = logging.getLogger(__name__)


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
        dataframe = import_args.get("dataframe", None)
        description = import_args.get("description", None)
        return import_spark(data_contract_specification, source, dataframe, description)


def import_spark(
    data_contract_specification: DataContractSpecification,
    source: str,
    dataframe: DataFrame | None = None,
    description: str | None = None,
) -> DataContractSpecification:
    """
    Imports schema(s) from Spark into a Data Contract Specification.

    Args:
        data_contract_specification (DataContractSpecification): The contract spec to update.
        source (str): Comma-separated Spark table/view names.
        dataframe (DataFrame | None): Optional Spark DataFrame to import.
        description (str | None): Optional table-level description.

    Returns:
        DataContractSpecification: The updated contract spec with imported models.
    """
    spark = SparkSession.builder.getOrCreate()
    data_contract_specification.servers["local"] = Server(type="dataframe")

    if dataframe is not None:
        if not isinstance(dataframe, DataFrame):
            raise TypeError("Expected 'dataframe' to be a pyspark.sql.DataFrame")
        data_contract_specification.models[source] = import_from_spark_df(
            spark, source, dataframe, description
        )
        return data_contract_specification

    if not source:
        raise ValueError("Either 'dataframe' or a valid 'source' must be provided")

    for table_name in map(str.strip, source.split(",")):
        df = spark.read.table(table_name)
        data_contract_specification.models[table_name] = import_from_spark_df(
            spark, table_name, df, description
        )

    return data_contract_specification



def import_from_spark_df(spark: SparkSession, source: str, df: DataFrame, description: str) -> Model:
    """
    Converts a Spark DataFrame into a Model.

    Args:
        spark: SparkSession
        source: A comma-separated string of Spark temporary views to read.
        df: The Spark DataFrame to convert.
        description: Table level comment

    Returns:
        Model: The generated data contract model.
    """
    model = Model()
    schema = df.schema

    if description is None:
        model.description = _table_comment_from_spark(spark, source)
    else: 
        model.description = description

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
    elif isinstance(spark_type, types.VariantType):
        return "variant"
    else:
        raise ValueError(f"Unsupported Spark type: {spark_type}")


def _table_comment_from_spark(spark: SparkSession, source: str):
    """
    Attempts to retrieve the table-level comment from a Spark table using multiple fallback methods.

    Args:
        spark (SparkSession): The active Spark session.
        source (str): The name of the table (without catalog or schema).

    Returns:
        str or None: The table-level comment, if found.
    """

    # Get Current Catalog and Schema from Spark Session
    try:
        current_catalog = spark.sql("SELECT current_catalog()").collect()[0][0]
    except Exception:
        current_catalog = "hive_metastore"  # Fallback for non-Unity Catalog clusters
    try:
        current_schema = spark.catalog.currentDatabase()
    except Exception:
        current_schema = spark.sql("SELECT current_database()").collect()[0][0]

    # Get table comment if it exists
    table_comment = ""
    source = f"{current_catalog}.{current_schema}.{source}"
    try:
        # Initialize WorkspaceClient for Unity Catalog API calls
        workspace_client = WorkspaceClient()
        created_table = workspace_client.tables.get(full_name=f"{source}")
        table_comment = created_table.comment
        logger.info(f"'{source}' table comment retrieved using 'WorkspaceClient.tables.get({source})'")
        return table_comment
    except Exception:
        pass

    # Fallback to Spark Catalog API for Hive Metastore or Non-UC Tables
    try:
        table_comment = spark.catalog.getTable(f"{source}").description
        logger.info(f"'{source}' table comment retrieved using 'spark.catalog.getTable({source}).description'")
        return table_comment
    except Exception:
        pass

    # Final Fallback Using DESCRIBE TABLE EXTENDED
    try:
        rows = spark.sql(f"DESCRIBE TABLE EXTENDED {source}").collect()
        for row in rows:
            if row.col_name.strip().lower() == "comment":
                table_comment = row.data_type
                break
        logger.info(f"'{source}' table comment retrieved using 'DESCRIBE TABLE EXTENDED {source}'")
        return table_comment
    except Exception:
        pass

    logger.info(f"{source} table comment could not be retrieved")

    return None
