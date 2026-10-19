from __future__ import annotations

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
    split_type_arguments,
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
        SparkSession.builder.config("spark.sql.warehouse.dir", f"{tmp_dir.name}/spark-warehouse")
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
    table_description = description
    if table_description is None:
        table_description = _table_comment_from_spark(spark, source)

    properties = [_property_from_struct_type(field) for field in df.schema]

    return create_schema_object(
        name=source,
        physical_type="table",
        description=table_description,
        properties=properties,
    )


def _property_from_struct_type(spark_field: types.StructField, physical_type: str | None = None) -> SchemaProperty:
    """Converts a Spark StructField into an ODCS SchemaProperty.

    Spark widens char/varchar columns to string but keeps the original type string
    (e.g. `struct<varchar_field:varchar(100),n:int>`) under the field's
    `__CHAR_VARCHAR_TYPE_STRING` metadata key, which we prefer over `simpleString()`.
    """
    metadata = spark_field.metadata or {}
    prop = _type_to_property(
        spark_field.name,
        spark_field.dataType,
        not spark_field.nullable,
        physical_type or metadata.get("__CHAR_VARCHAR_TYPE_STRING"),
    )
    if metadata.get("comment"):
        prop.description = metadata["comment"]
    return prop


def _type_to_property(
    name: str, spark_type: types.DataType, required: bool = True, physical_type: str | None = None
) -> SchemaProperty:
    """Convert a Spark data type to an ODCS SchemaProperty."""
    logical_type = _data_type_from_spark(spark_type)
    physical_type = physical_type or spark_type.simpleString()
    # element/key/value/field type strings of `array<...>`, `map<...>` and `struct<...>`
    arguments = (
        split_type_arguments(physical_type[physical_type.find("<") + 1 : -1]) if physical_type.endswith(">") else []
    )

    nested_properties = None
    items_prop = None
    map_key = map_value = None

    if isinstance(spark_type, types.ArrayType):
        element_type = arguments[0] if len(arguments) == 1 else None
        items_prop = _type_to_property("items", spark_type.elementType, not spark_type.containsNull, element_type)
    elif isinstance(spark_type, types.MapType):
        key_type, value_type = arguments if len(arguments) == 2 else (None, None)
        map_key = _type_to_property("key", spark_type.keyType, True, key_type)
        map_value = _type_to_property("value", spark_type.valueType, not spark_type.valueContainsNull, value_type)
    elif isinstance(spark_type, types.StructType):
        field_types = dict(argument.split(":", 1) for argument in arguments if ":" in argument)
        nested_properties = [_property_from_struct_type(sf, field_types.get(sf.name)) for sf in spark_type.fields]

    return create_property(
        name=name,
        logical_type=logical_type,
        physical_type=physical_type,
        required=required if required else None,
        properties=nested_properties,
        items=items_prop,
        map_key=map_key,
        map_value=map_value,
    )


def _data_type_from_spark(spark_type: types.DataType) -> str:
    """Maps Spark data types to ODCS logical types."""
    if isinstance(spark_type, types.StringType):
        return "string"
    elif isinstance(spark_type, (types.IntegerType, types.ShortType, types.ByteType)):
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
        return "map"
    elif isinstance(spark_type, types.TimestampType):
        return "timestamp"
    elif isinstance(spark_type, types.TimestampNTZType):
        return "timestamp"
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
        try:
            current_schema = spark.sql("SELECT current_database()").collect()[0][0]
        except Exception:
            current_schema = "default"

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
