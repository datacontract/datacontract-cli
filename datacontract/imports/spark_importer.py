import atexit
import logging
import tempfile

from databricks.sdk import WorkspaceClient
from open_data_contract_standard.model import OpenDataContractStandard, SchemaProperty
from pyspark.sql import DataFrame, SparkSession, types

from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import (
    create_odcs,
    create_property,
    create_schema_object,
    create_server,
)

logger = logging.getLogger(__name__)


class SparkImporter(Importer):
    def import_source(
        self,
        source: str,
        import_args: dict,
    ) -> OpenDataContractStandard:
        """Imports data from a Spark source into an ODCS data contract."""
        dataframe = import_args.get("dataframe", None)
        description = import_args.get("description", None)
        return import_spark(source, dataframe, description)


def import_spark(
    source: str,
    dataframe: DataFrame | None = None,
    description: str | None = None,
) -> OpenDataContractStandard:
    """Imports schema(s) from Spark into an ODCS data contract."""

    tmp_dir = tempfile.TemporaryDirectory(prefix="datacontract-cli-spark")
    atexit.register(tmp_dir.cleanup)

    spark = (
        SparkSession.builder.config("spark.sql.warehouse.dir", f"{tmp_dir}/spark-warehouse")
        .config("spark.streaming.stopGracefullyOnShutdown", "true")
        .config("spark.ui.enabled", "false")
        .getOrCreate()
    )

    odcs = create_odcs()
    odcs.servers = [create_server(name="local", server_type="dataframe")]
    odcs.schema_ = []

    if dataframe is not None:
        if not isinstance(dataframe, DataFrame):
            raise TypeError("Expected 'dataframe' to be a pyspark.sql.DataFrame")
        schema_obj = import_from_spark_df(spark, source, dataframe, description)
        odcs.schema_.append(schema_obj)
        return odcs

    if not source:
        raise ValueError("Either 'dataframe' or a valid 'source' must be provided")

    for table_name in map(str.strip, source.split(",")):
        df = spark.read.table(table_name)
        schema_obj = import_from_spark_df(spark, table_name, df, description)
        odcs.schema_.append(schema_obj)

    return odcs


def import_from_spark_df(spark: SparkSession, source: str, df: DataFrame, description: str):
    """Converts a Spark DataFrame into an ODCS SchemaObject."""
    schema = df.schema

    table_description = description
    if table_description is None:
        table_description = _table_comment_from_spark(spark, source)

    properties = []
    for field in schema:
        prop = _property_from_struct_type(field)
        properties.append(prop)

    return create_schema_object(
        name=source,
        physical_type="table",
        description=table_description,
        properties=properties,
    )


def _property_from_struct_type(spark_field: types.StructField) -> SchemaProperty:
    """Converts a Spark StructField into an ODCS SchemaProperty."""
    logical_type = _data_type_from_spark(spark_field.dataType)
    description = spark_field.metadata.get("comment") if spark_field.metadata else None
    required = not spark_field.nullable

    nested_properties = None
    items_prop = None

    if logical_type == "array":
        items_prop = _type_to_property("items", spark_field.dataType.elementType, not spark_field.dataType.containsNull)
    elif logical_type == "object" and isinstance(spark_field.dataType, types.StructType):
        nested_properties = [_property_from_struct_type(sf) for sf in spark_field.dataType.fields]

    return create_property(
        name=spark_field.name,
        logical_type=logical_type,
        physical_type=str(spark_field.dataType),
        description=description,
        required=required if required else None,
        properties=nested_properties,
        items=items_prop,
    )


def _type_to_property(name: str, spark_type: types.DataType, required: bool = True) -> SchemaProperty:
    """Convert a Spark data type to an ODCS SchemaProperty."""
    logical_type = _data_type_from_spark(spark_type)

    nested_properties = None
    items_prop = None

    if logical_type == "array":
        items_prop = _type_to_property("items", spark_type.elementType, not spark_type.containsNull)
    elif logical_type == "object" and isinstance(spark_type, types.StructType):
        nested_properties = [_property_from_struct_type(sf) for sf in spark_type.fields]

    return create_property(
        name=name,
        logical_type=logical_type,
        physical_type=str(spark_type),
        required=required if required else None,
        properties=nested_properties,
        items=items_prop,
    )


def _data_type_from_spark(spark_type: types.DataType) -> str:
    """Maps Spark data types to ODCS logical types."""
    if isinstance(spark_type, types.StringType):
        return "string"
    elif isinstance(spark_type, (types.IntegerType, types.ShortType)):
        return "integer"
    elif isinstance(spark_type, types.LongType):
        return "integer"
    elif isinstance(spark_type, types.FloatType):
        return "number"
    elif isinstance(spark_type, types.DoubleType):
        return "number"
    elif isinstance(spark_type, types.StructType):
        return "object"
    elif isinstance(spark_type, types.ArrayType):
        return "array"
    elif isinstance(spark_type, types.MapType):
        return "object"
    elif isinstance(spark_type, types.TimestampType):
        return "date"
    elif isinstance(spark_type, types.TimestampNTZType):
        return "date"
    elif isinstance(spark_type, types.DateType):
        return "date"
    elif isinstance(spark_type, types.BooleanType):
        return "boolean"
    elif isinstance(spark_type, types.BinaryType):
        return "array"
    elif isinstance(spark_type, types.DecimalType):
        return "number"
    elif isinstance(spark_type, types.NullType):
        return "string"
    elif isinstance(spark_type, types.VarcharType):
        return "string"
    elif isinstance(spark_type, types.VariantType):
        return "object"
    else:
        raise ValueError(f"Unsupported Spark type: {spark_type}")


def _table_comment_from_spark(spark: SparkSession, source: str):
    """Attempts to retrieve the table-level comment from a Spark table."""
    try:
        current_catalog = spark.sql("SELECT current_catalog()").collect()[0][0]
    except Exception:
        current_catalog = "hive_metastore"
    try:
        current_schema = spark.catalog.currentDatabase()
    except Exception:
        current_schema = spark.sql("SELECT current_database()").collect()[0][0]

    table_comment = ""
    source = f"{current_catalog}.{current_schema}.{source}"

    try:
        workspace_client = WorkspaceClient()
        created_table = workspace_client.tables.get(full_name=f"{source}")
        table_comment = created_table.comment
        logger.info(f"'{source}' table comment retrieved using 'WorkspaceClient.tables.get({source})'")
        return table_comment
    except Exception:
        pass

    try:
        table_comment = spark.catalog.getTable(f"{source}").description
        logger.info(f"'{source}' table comment retrieved using 'spark.catalog.getTable({source}).description'")
        return table_comment
    except Exception:
        pass

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
