from __future__ import annotations

import atexit
import json
import logging
import tempfile

from databricks.sdk import WorkspaceClient
from open_data_contract_standard.model import OpenDataContractStandard, SchemaProperty

try:
    # pyspark is deliberately not a package dependency (see pyproject.toml) since a
    # Spark import only ever runs against a session the caller already built, so
    # pyspark is necessarily importable in that process. This module is still
    # importable without it (e.g. for unit-testing the pure-Python helpers below);
    # `DataFrame`/`SparkSession`/`types` are only dereferenced once real Spark
    # objects are involved.
    from pyspark.sql import DataFrame, SparkSession, types
except ImportError:
    DataFrame = SparkSession = types = None

from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import (
    create_odcs,
    create_property,
    create_schema_object,
    create_server,
)
from datacontract.imports.spark_type_json import property_from_type_json

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
    schema = df.schema

    table_description = description
    if table_description is None:
        table_description = _table_comment_from_spark(spark, source)

    properties = _table_metadata_properties(spark, source, schema)
    if properties is None:
        properties = [_property_from_struct_type(field) for field in schema]

    return create_schema_object(
        name=source,
        physical_type="table",
        description=table_description,
        properties=properties,
    )


def _table_metadata_properties(spark: SparkSession | None, source: str, schema=None):
    """Return exact table-column metadata if Spark or Databricks exposes it.

    When the database can answer with native type JSON or DESCRIBE-native strings,
    prefer those over the lossy `DataFrame.schema.simpleString()` output.
    """
    if not source:
        return None

    try:
        exact_types = _describe_table_types(spark, source)
        if not exact_types:
            return None

        if schema is not None:
            by_name = {field.name: field for field in schema}
            return [
                _property_from_type_name(by_name.get(name, None), type_name, by_name.get(name, None))
                for name, type_name in exact_types.items()
                if name in by_name
            ]

        return [
            _property_from_type_name(
                type("SparkField", (), {"name": name, "dataType": None, "nullable": True, "metadata": {}})(),
                type_name,
                None,
            )
            for name, type_name in exact_types.items()
        ]
    except Exception:
        logger.debug("Could not resolve exact Spark table metadata for %s", source, exc_info=True)

    return None


def _property_from_type_name(
    field: types.StructField | None,
    native_type: str | None,
    fallback_field: types.StructField | None,
):
    """Convert a column name + native type string into an ODCS property."""
    if native_type is None:
        return _property_from_struct_type(fallback_field or field)

    try:
        type_json = _describe_type_to_json(native_type)
        if field is not None:
            return property_from_type_json(
                field.name,
                type_json,
                required=not field.nullable,
                description=field.metadata.get("comment") if field.metadata else None,
            )
        if fallback_field is not None:
            return property_from_type_json(
                fallback_field.name,
                type_json,
                required=not fallback_field.nullable,
                description=fallback_field.metadata.get("comment") if fallback_field.metadata else None,
            )
        return property_from_type_json("column", type_json, required=True)
    except Exception:
        if field is not None:
            return _property_from_struct_type(field)
        if fallback_field is not None:
            return _property_from_struct_type(fallback_field)
        return create_property(name="column", logical_type="string", physical_type=native_type)


def _describe_table_types(spark: SparkSession | None, source: str):
    """Best-effort exact Spark/Databricks column types for a table name."""
    exact_types = {}
    try:
        table_name = _qualified_table_name(spark, source)
    except Exception:
        table_name = source

    try:
        workspace_client = WorkspaceClient()
        created_table = workspace_client.tables.get(full_name=f"{table_name}")
        columns = getattr(created_table, "columns", None) or []
        for column in columns:
            type_json = getattr(column, "type_json", None) or getattr(column, "typeJson", None)
            if not type_json:
                continue
            try:
                parsed = json.loads(type_json)
            except Exception:
                parsed = type_json
            if isinstance(parsed, dict):
                if parsed.get("name") is not None and "type" in parsed:
                    exact_types[column.name] = parsed
                    continue
                if "type" in parsed:
                    exact_types[column.name] = parsed
                    continue
            if isinstance(parsed, str):
                exact_types[column.name] = parsed
                continue
        if exact_types:
            return {name: _column_type_json_to_native(name, type_data) for name, type_data in exact_types.items()}
    except Exception:
        logger.debug("WorkspaceClient metadata unavailable for %s", source, exc_info=True)

    try:
        if spark is not None:
            rows = spark.sql(f"DESCRIBE TABLE EXTENDED {table_name}").collect()
            for row in rows:
                if not hasattr(row, "col_name"):
                    continue
                name = row.col_name.strip()
                if name in {"# col_name", "col_name", "comment", "Type", "Comment", "Created Time", "Location"}:
                    continue
                if name and name != "":
                    exact_types[name] = row.data_type
            if exact_types:
                return exact_types
    except Exception:
        logger.debug("DESCRIBE TABLE EXTENDED metadata unavailable for %s", source, exc_info=True)

    return exact_types or None


def _column_type_json_to_native(column_name: str, type_data):
    """Normalize metadata-provided type JSON into the native Spark type string."""
    if isinstance(type_data, str):
        return type_data
    if isinstance(type_data, dict):
        if type_data.get("name") is not None and "type" in type_data:
            return property_from_type_json(column_name, type_data["type"]).physicalType
        return property_from_type_json(column_name, type_data).physicalType
    return str(type_data)


# DESCRIBE (and `simpleString()`) spell the integer family differently from
# Spark's JSON type names, which `spark_type_json._PRIMITIVES` is keyed on.
_DESCRIBE_PRIMITIVE_ALIASES = {
    "tinyint": "byte",
    "smallint": "short",
    "int": "integer",
    "bigint": "long",
}


def _describe_type_to_json(type_name: str):
    """Convert native Spark DESCRIBE strings into the JSON shape expected by `property_from_type_json`."""
    type_name = type_name.strip()
    if not type_name:
        return type_name
    if "<" not in type_name and "(" not in type_name:
        # DESCRIBE spells the integer family with their `simpleString()` names
        # (bigint, int, smallint, tinyint); `property_from_type_json` expects
        # Spark's JSON type names (long, integer, short, byte).
        return _DESCRIBE_PRIMITIVE_ALIASES.get(type_name, type_name)

    if type_name.startswith("struct<") and type_name.endswith(">"):
        fields = _describe_struct_fields(type_name[7:-1])
        return {"type": "struct", "fields": fields}
    if type_name.startswith("array<") and type_name.endswith(">"):
        inner = type_name[6:-1]
        return {"type": "array", "elementType": _describe_type_to_json(inner), "containsNull": True}
    if type_name.startswith("map<") and type_name.endswith(">"):
        key, value = _split_top_level(type_name[4:-1], 2)
        return {
            "type": "map",
            "keyType": _describe_type_to_json(key),
            "valueType": _describe_type_to_json(value),
            "valueContainsNull": True,
        }
    return type_name


def _describe_struct_fields(inner: str):
    fields = []
    for raw in _split_top_level(inner, None):
        if not raw:
            continue
        name, value = raw.split(":", 1)
        fields.append(
            {"name": name.strip(), "type": _describe_type_to_json(value.strip()), "nullable": True, "metadata": {}}
        )
    return fields


def _split_top_level(text: str, limit: int | None = None):
    items = []
    current = []
    depth = 0
    for ch in text:
        if ch in "<([":
            depth += 1
        elif ch in ">)]":
            depth = max(0, depth - 1)
        elif ch == "," and depth == 0:
            if limit is not None and len(items) >= limit - 1:
                current.append(ch)
                continue
            items.append("".join(current).strip())
            current = []
            continue
        current.append(ch)
    if current or text.endswith(","):
        items.append("".join(current).strip())
    return [item for item in items if item != ""]


def _qualified_table_name(spark: SparkSession | None, source: str):
    if not source:
        return source
    if "." in source or "`" in source:
        return source
    if spark is None:
        return source
    try:
        current_catalog = spark.sql("SELECT current_catalog()").collect()[0][0]
    except Exception:
        current_catalog = "hive_metastore"
    try:
        current_schema = spark.catalog.currentDatabase()
    except Exception:
        current_schema = spark.sql("SELECT current_database()").collect()[0][0]
    return f"{current_catalog}.{current_schema}.{source}"


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
        physical_type=spark_field.dataType.simpleString(),
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
    map_key = map_value = None

    if logical_type == "array":
        items_prop = _type_to_property("items", spark_type.elementType, not spark_type.containsNull)
    elif logical_type == "map":
        map_key = _type_to_property("key", spark_type.keyType, True)
        map_value = _type_to_property("value", spark_type.valueType, not spark_type.valueContainsNull)
    elif logical_type == "object" and isinstance(spark_type, types.StructType):
        nested_properties = [_property_from_struct_type(sf) for sf in spark_type.fields]

    return create_property(
        name=name,
        logical_type=logical_type,
        physical_type=spark_type.simpleString(),
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
