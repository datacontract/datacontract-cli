import logging
from typing import Any, Dict, Optional, Protocol, Union

from open_data_contract_standard.model import SchemaProperty

from datacontract.model.exceptions import DataContractException


class FieldLike(Protocol):
    """Protocol for field-like objects (DCS Field or PropertyAdapter)."""

    type: Optional[str]
    config: Optional[Dict[str, Any]]
    precision: Optional[int]
    scale: Optional[int]
    format: Optional[str]
    items: Optional["FieldLike"]
    fields: Dict[str, "FieldLike"]


def _get_type(field: Union[SchemaProperty, FieldLike]) -> Optional[str]:
    """Get the type string from a field. Prefers physicalType over logicalType."""
    if isinstance(field, SchemaProperty):
        if field.physicalType:
            return field.physicalType
        return field.logicalType
    return field.type


def _get_base_type(field: Union[SchemaProperty, FieldLike]) -> Optional[str]:
    """Get the lowercase base type from a field, stripping any parameters.
    E.g. a physicalType of 'VARCHAR(255)' returns 'varchar'."""
    field_type = _get_type(field)
    if field_type is None:
        return None
    if "(" in field_type:
        return field_type[: field_type.index("(")].strip().lower()
    return field_type.lower()


def _get_params(field: Union[SchemaProperty, FieldLike]) -> Optional[str]:
    """Get the parameter portion from a field's type, e.g. 'VARCHAR(255)' -> '255'."""
    field_type = _get_type(field)
    if field_type and "(" in field_type and field_type.endswith(")"):
        return field_type[field_type.index("(") + 1 : -1]
    return None


def _get_config(field: Union[SchemaProperty, FieldLike]) -> Optional[Dict[str, Any]]:
    """Get the config from a field, handling both ODCS and DCS."""
    if isinstance(field, SchemaProperty):
        if field.customProperties is None:
            return None
        return {cp.property: cp.value for cp in field.customProperties}
    return field.config


def _get_config_value(field: Union[SchemaProperty, FieldLike], key: str) -> Optional[Any]:
    """Get a config value from a field."""
    config = _get_config(field)
    if config is None:
        return None
    return config.get(key)


def _get_precision(field: Union[SchemaProperty, FieldLike]) -> Optional[int]:
    """Get precision from a field."""
    if isinstance(field, SchemaProperty):
        if field.logicalTypeOptions and field.logicalTypeOptions.get("precision"):
            return field.logicalTypeOptions.get("precision")
        # Also check customProperties
        val = _get_config_value(field, "precision")
        if val:
            return int(val)
        return None
    return field.precision


def _get_scale(field: Union[SchemaProperty, FieldLike]) -> Optional[int]:
    """Get scale from a field."""
    if isinstance(field, SchemaProperty):
        if field.logicalTypeOptions and field.logicalTypeOptions.get("scale"):
            return field.logicalTypeOptions.get("scale")
        # Also check customProperties
        val = _get_config_value(field, "scale")
        if val:
            return int(val)
        return None
    return field.scale


def _get_format(field: Union[SchemaProperty, FieldLike]) -> Optional[str]:
    """Get format from a field."""
    if isinstance(field, SchemaProperty):
        if field.logicalTypeOptions:
            return field.logicalTypeOptions.get("format")
        return None
    return field.format


def _get_items(field: Union[SchemaProperty, FieldLike]) -> Optional[Union[SchemaProperty, FieldLike]]:
    """Get items from an array field."""
    if isinstance(field, SchemaProperty):
        return field.items
    return field.items


def _get_nested_fields(field: Union[SchemaProperty, FieldLike]) -> Dict[str, Union[SchemaProperty, FieldLike]]:
    """Get nested fields from an object field."""
    if isinstance(field, SchemaProperty):
        if field.properties is None:
            return {}
        return {p.name: p for p in field.properties}
    return field.fields if field.fields else {}


def _attach_params_if_present(
    base_type: str, field: Union[SchemaProperty, FieldLike], *, default: Optional[str] = None
) -> str:
    """Attach params from the field's type to the result, e.g. ('varchar', field) -> 'varchar(255)'.
    If no params are present and a default is given, use the default instead."""
    params = _get_params(field)
    if params:
        return f"{base_type}({params})"
    if default:
        return f"{base_type}({default})"
    return base_type


def convert_to_sql_type(field: Union[SchemaProperty, FieldLike], server_type: str) -> str:
    physical_type = _get_config_value(field, "physicalType")
    if physical_type:
        return physical_type

    # Compound physicalTypes like "TIMESTAMP(6) WITH TIME ZONE" should pass through verbatim.
    if isinstance(field, SchemaProperty) and field.physicalType:
        pt = field.physicalType
        if "(" in pt and not pt.endswith(")"):
            return pt

    return _convert_base_to_sql_type(field, server_type)


def _convert_base_to_sql_type(field: Union[SchemaProperty, FieldLike], server_type: str) -> Optional[str]:
    """Route a field to the server-specific converter."""
    if server_type == "snowflake":
        return convert_to_snowflake(field)
    elif server_type == "postgres":
        return convert_type_to_postgres(field)
    elif server_type == "mysql":
        return convert_type_to_mysql(field)
    elif server_type == "dataframe":
        return convert_to_dataframe(field)
    elif server_type == "databricks":
        return convert_to_databricks(field)
    elif server_type == "local" or server_type == "s3":
        return convert_to_duckdb(field)
    elif server_type == "sqlserver":
        return convert_type_to_sqlserver(field)
    elif server_type == "bigquery":
        return convert_type_to_bigquery(field)
    elif server_type == "trino":
        return convert_type_to_trino(field)
    elif server_type == "oracle":
        return convert_type_to_oracle(field)
    # Fallback: return the raw type string (preserves original behavior for unknown/None server_type)
    return _get_type(field)


# snowflake data types:
# https://docs.snowflake.com/en/sql-reference/data-types.html
def convert_to_snowflake(field: Union[SchemaProperty, FieldLike]) -> None | str:
    snowflake_type = _get_config_value(field, "snowflakeType")
    if snowflake_type:
        return snowflake_type

    base_type = _get_base_type(field)

    if base_type is None:
        return None

    if base_type in ["string"]:
        return _attach_params_if_present("STRING", field)
    if base_type in ["varchar"]:
        return _attach_params_if_present("VARCHAR", field)
    if base_type in ["text"]:
        return _attach_params_if_present("TEXT", field)
    if base_type in ["timestamp", "timestamp_tz"]:
        return _attach_params_if_present("TIMESTAMP_TZ", field)
    if base_type in ["timestamp_ntz"]:
        return _attach_params_if_present("TIMESTAMP_NTZ", field)
    if base_type in ["date"]:
        return "DATE"
    if base_type in ["time"]:
        return _attach_params_if_present("TIME", field)
    if base_type in ["number", "decimal", "numeric"]:
        return _attach_params_if_present("NUMBER", field)
    if base_type in ["float", "double"]:
        return "FLOAT"
    if base_type in ["integer", "int", "long", "bigint"]:
        return "NUMBER"
    if base_type in ["boolean"]:
        return "BOOLEAN"
    if base_type in ["object", "record", "struct"]:
        return "OBJECT"
    if base_type in ["bytes"]:
        return _attach_params_if_present("BINARY", field)
    if base_type in ["array"]:
        return "ARRAY"
    if _get_params(field):
        return _get_type(field)
    return None


# https://www.postgresql.org/docs/current/datatype.html
# Using the name whenever possible
def convert_type_to_postgres(field: Union[SchemaProperty, FieldLike]) -> None | str:
    postgres_type = _get_config_value(field, "postgresType")
    if postgres_type:
        return postgres_type

    base_type = _get_base_type(field)
    if base_type is None:
        return None
    if base_type in ["string", "varchar", "text", "nvarchar"]:
        return "uuid" if _get_format(field) == "uuid" else "text"
    if base_type in ["timestamp", "timestamp_tz"]:
        return _attach_params_if_present("timestamptz", field)
    if base_type in ["timestamp_ntz"]:
        return _attach_params_if_present("timestamp", field)
    if base_type in ["date"]:
        return "date"
    if base_type in ["time"]:
        return _attach_params_if_present("time", field)
    if base_type in ["number"]:
        return _attach_params_if_present("numeric", field)
    if base_type in ["decimal"]:
        return _attach_params_if_present("decimal", field)
    if base_type in ["numeric"]:
        return _attach_params_if_present("numeric", field)
    if base_type in ["float"]:
        return "real"
    if base_type in ["double"]:
        return "double precision"
    if base_type in ["integer"]:
        return "integer"
    if base_type in ["int"]:
        return "int"
    if base_type in ["bigint"]:
        return "bigint"
    if base_type in ["long"]:
        return "bigint"
    if base_type in ["boolean"]:
        return "boolean"
    if base_type in ["object", "record", "struct"]:
        return "jsonb"
    if base_type in ["bytes"]:
        return "bytea"
    if base_type in ["array"]:
        items = _get_items(field)
        if items:
            return convert_to_sql_type(items, "postgres") + "[]"
        return "text[]"
    if _get_params(field):
        return _get_type(field)
    return None


# https://dev.mysql.com/doc/refman/8.0/en/data-types.html
def convert_type_to_mysql(field: Union[SchemaProperty, FieldLike]) -> None | str:
    mysql_type = _get_config_value(field, "mysqlType")
    if mysql_type:
        return mysql_type

    base_type = _get_base_type(field)
    if base_type is None:
        return None
    if base_type in ["string", "varchar", "text"]:
        if _get_format(field) == "uuid":
            return "varchar(36)"
        if base_type == "text":
            return "text"
        if base_type == "string":
            return _attach_params_if_present("varchar", field, default="255")
        return _attach_params_if_present("varchar", field)
    if base_type in ["timestamp", "timestamp_tz"]:
        return _attach_params_if_present("timestamp", field)
    if base_type in ["timestamp_ntz"]:
        return _attach_params_if_present("datetime", field)
    if base_type in ["date"]:
        return "date"
    if base_type in ["time"]:
        return _attach_params_if_present("time", field)
    if base_type in ["number"]:
        return _attach_params_if_present("decimal", field)
    if base_type in ["decimal"]:
        return _attach_params_if_present("decimal", field)
    if base_type in ["numeric"]:
        return _attach_params_if_present("numeric", field)
    if base_type in ["float"]:
        return _attach_params_if_present("float", field)
    if base_type in ["double"]:
        return "double"
    if base_type in ["integer", "int"]:
        return "int"
    if base_type in ["long", "bigint"]:
        return "bigint"
    if base_type in ["boolean"]:
        return "boolean"
    if base_type in ["object", "record", "struct"]:
        return "json"
    if base_type in ["bytes"]:
        return "blob"
    if base_type in ["array"]:
        return "json"
    if _get_params(field):
        return _get_type(field)
    return None


# dataframe data types:
# https://spark.apache.org/docs/latest/sql-ref-datatypes.html
def convert_to_dataframe(field: Union[SchemaProperty, FieldLike]) -> None | str:
    dataframe_type = _get_config_value(field, "dataframeType")
    if dataframe_type:
        return dataframe_type

    base_type = _get_base_type(field)
    if base_type is None:
        return None

    if base_type in ["string", "varchar", "text"]:
        return "STRING"
    if base_type in ["timestamp", "timestamp_tz"]:
        return "TIMESTAMP"
    if base_type in ["timestamp_ntz"]:
        return "TIMESTAMP_NTZ"
    if base_type in ["date"]:
        return "DATE"
    if base_type in ["time"]:
        return "STRING"
    if base_type in ["number", "decimal", "numeric"]:
        precision = _get_precision(field)
        scale = _get_scale(field)
        precision = precision if precision is not None else 38
        scale = scale if scale is not None else 0
        return f"DECIMAL({precision},{scale})"
    if base_type in ["float"]:
        return "FLOAT"
    if base_type in ["double"]:
        return "DOUBLE"
    if base_type in ["integer", "int"]:
        return "INT"
    if base_type in ["long", "bigint"]:
        return "BIGINT"
    if base_type in ["boolean"]:
        return "BOOLEAN"
    if base_type in ["object", "record", "struct"]:
        nested_fields = []
        for nested_field_name, nested_field in _get_nested_fields(field).items():
            nested_field_type = convert_to_dataframe(nested_field)
            nested_fields.append(f"{nested_field_name}:{nested_field_type}")
        return f"STRUCT<{','.join(nested_fields)}>"
    if base_type in ["bytes"]:
        return "BINARY"
    if base_type in ["array"]:
        items = _get_items(field)
        if items:
            item_type = convert_to_dataframe(items)
            return f"ARRAY<{item_type}>"
        return "ARRAY<STRING>"
    if _get_params(field):
        return _get_type(field)
    return None


# databricks data types:
# https://docs.databricks.com/en/sql/language-manual/sql-ref-datatypes.html
def convert_to_databricks(field: Union[SchemaProperty, FieldLike]) -> None | str:
    base_type = _get_base_type(field)
    databricks_type = _get_config_value(field, "databricksType")
    if databricks_type and base_type and base_type not in ["array", "object", "record", "struct"]:
        return databricks_type
    if base_type is None:
        return None

    if base_type in ["string", "varchar", "text"]:
        return "STRING"
    if base_type in ["timestamp", "timestamp_tz"]:
        return "TIMESTAMP"
    if base_type in ["timestamp_ntz"]:
        return "TIMESTAMP_NTZ"
    if base_type in ["date"]:
        return "DATE"
    if base_type in ["time"]:
        return "STRING"
    if base_type in ["number", "decimal", "numeric"]:
        precision = _get_precision(field)
        scale = _get_scale(field)
        precision = precision if precision is not None else 38
        scale = scale if scale is not None else 0
        return f"DECIMAL({precision},{scale})"
    if base_type in ["float"]:
        return "FLOAT"
    if base_type in ["double"]:
        return "DOUBLE"
    if base_type in ["integer", "int"]:
        return "INT"
    if base_type in ["long", "bigint"]:
        return "BIGINT"
    if base_type in ["boolean"]:
        return "BOOLEAN"
    if base_type in ["object", "record", "struct"]:
        nested_fields = []
        for nested_field_name, nested_field in _get_nested_fields(field).items():
            nested_field_type = convert_to_databricks(nested_field)
            nested_fields.append(f"{nested_field_name}:{nested_field_type}")
        return f"STRUCT<{','.join(nested_fields)}>"
    if base_type in ["bytes"]:
        return "BINARY"
    if base_type in ["array"]:
        items = _get_items(field)
        if items:
            item_type = convert_to_databricks(items)
            return f"ARRAY<{item_type}>"
        return "ARRAY<STRING>"
    if base_type in ["variant"]:
        return "VARIANT"
    if _get_params(field):
        return _get_type(field)
    return None


def convert_to_duckdb(field: Union[SchemaProperty, FieldLike]) -> None | str:
    """Convert a data contract field to the corresponding DuckDB SQL type."""
    base_type = _get_base_type(field)
    if field is None or base_type is None:
        return None

    if base_type in ["nvarchar", "varchar", "string", "text"]:
        return _attach_params_if_present("VARCHAR", field)
    if base_type in ["binary", "bytes", "blob"]:
        return "BLOB"
    if base_type in ["boolean"]:
        return "BOOLEAN"
    if base_type in ["float"]:
        return "FLOAT"
    if base_type in ["double"]:
        return "DOUBLE"
    if base_type in ["int", "int32", "integer"]:
        return "INTEGER"
    if base_type in ["int64", "long", "bigint"]:
        return "BIGINT"
    if base_type in ["date"]:
        return "DATE"
    if base_type in ["time"]:
        return "TIME"
    if base_type in ["timestamp", "timestamp_tz"]:
        return "TIMESTAMP WITH TIME ZONE"
    if base_type in ["timestamp_ntz"]:
        return "TIMESTAMP"

    # convert decimal numbers with precision and scale
    if "decimal" in base_type or "number" in base_type or "numeric" in base_type:
        precision = _get_precision(field)
        scale = _get_scale(field)
        if precision and scale:
            return f"DECIMAL({precision},{scale})"
        else:
            return _get_type(field)

    # Check list and map
    if base_type == "list" or base_type == "array":
        items = _get_items(field)
        if items:
            item_type = convert_to_duckdb(items)
            return f"{item_type}[]"
        return "VARCHAR[]"
    if base_type == "map":
        keys = _get_config_value(field, "mapKeys")
        values = _get_config_value(field, "mapValues")
        key_type = keys if keys else "VARCHAR"
        value_type = values if values else "VARCHAR"
        return f"MAP({key_type}, {value_type})"
    if base_type in ["struct", "object", "record"]:
        structure_field = "STRUCT("
        field_strings = []
        for fieldKey, fieldValue in _get_nested_fields(field).items():
            field_strings.append(f"{fieldKey} {convert_to_duckdb(fieldValue)}")
        structure_field += ", ".join(field_strings)
        structure_field += ")"
        return structure_field

    return None


def convert_type_to_sqlserver(field: Union[SchemaProperty, FieldLike]) -> None | str:
    """Convert from supported datacontract types to equivalent sqlserver types"""
    base_type = _get_base_type(field)
    if not base_type:
        return None

    sqlserver_type = _get_config_value(field, "sqlserverType")
    if sqlserver_type:
        return sqlserver_type
    if base_type in ["string", "varchar", "text"]:
        return "uniqueidentifier" if _get_format(field) == "uuid" else _attach_params_if_present("varchar", field)
    if base_type in ["timestamp", "timestamp_tz"]:
        return _attach_params_if_present("datetimeoffset", field)
    if base_type in ["timestamp_ntz"]:
        if _get_format(field) == "datetime":
            return "datetime"
        return _attach_params_if_present("datetime2", field)
    if base_type in ["date"]:
        return "date"
    if base_type in ["time"]:
        return _attach_params_if_present("time", field)
    if base_type in ["number"]:
        return _attach_params_if_present("numeric", field)
    if base_type in ["decimal"]:
        return _attach_params_if_present("decimal", field)
    if base_type in ["numeric"]:
        return _attach_params_if_present("numeric", field)
    if base_type in ["float", "double"]:
        return _attach_params_if_present("float", field)
    if base_type in ["integer", "int"]:
        return "INT"
    if base_type in ["bigint", "long"]:
        return "bigint"
    if base_type in ["boolean"]:
        return "bit"
    if base_type in ["object", "record", "struct"]:
        return "nvarchar(max)"
    if base_type in ["bytes"]:
        return _attach_params_if_present("varbinary", field)
    if base_type in ["array"]:
        raise NotImplementedError("SQLServer does not support array types.")
    if _get_params(field):
        return _get_type(field)
    return None


_BQ_TYPES = {
    "STRING",
    "BYTES",
    "INT64",
    "INTEGER",
    "FLOAT64",
    "NUMERIC",
    "BIGNUMERIC",
    "BOOL",
    "TIMESTAMP",
    "DATE",
    "TIME",
    "DATETIME",
    "GEOGRAPHY",
    "JSON",
    "RECORD",
    "STRUCT",
    "ARRAY",
}


def map_type_to_bigquery(prop: SchemaProperty) -> str:
    """Map a schema property type to a flat BigQuery type.

    If physicalType is a valid BigQuery type (including parameterized types like NUMERIC(18, 4)),
    return it directly. Otherwise, strip any parameters, map the base type via the logical type
    mapping, and re-attach parameters to the result.

    Used by the BigQuery exporter for JSON schema output. For string-based syntax
    (ARRAY<STRING>, STRUCT<field1 TYPE1>) needed by SodaCL, use convert_type_to_bigquery.
    """
    if prop.physicalType:
        base_type = prop.physicalType.upper().split("(")[0].strip()
        if base_type in _BQ_TYPES:
            return prop.physicalType

    type_to_map = prop.physicalType or prop.logicalType

    # Strip parameters (e.g. "DECIMAL(10,2)" -> "DECIMAL") before mapping,
    # then re-attach them to the translated type.
    params = None
    if type_to_map and "(" in type_to_map and type_to_map.endswith(")"):
        params = type_to_map[type_to_map.index("(") + 1 : -1]
        type_to_map = type_to_map[: type_to_map.index("(")].strip()

    result = _map_logical_type_to_bigquery(type_to_map, prop.properties)
    if params and result:
        return f"{result}({params})"
    return result


def _map_logical_type_to_bigquery(logical_type: str, nested_fields) -> str:
    """Map a logical type to the corresponding BigQuery type."""
    logger = logging.getLogger(__name__)

    if not logical_type:
        return None

    if logical_type.lower() in ["string", "varchar", "text"]:
        return "STRING"
    elif logical_type.lower() == "json":
        return "JSON"
    elif logical_type.lower() == "bytes":
        return "BYTES"
    elif logical_type.lower() in ["int", "integer"]:
        return "INTEGER"
    elif logical_type.lower() in ["long", "bigint"]:
        return "INT64"
    elif logical_type.lower() == "float":
        return "FLOAT64"
    elif logical_type.lower() == "boolean":
        return "BOOL"
    elif logical_type.lower() in ["timestamp", "timestamp_tz"]:
        return "TIMESTAMP"
    elif logical_type.lower() == "date":
        return "DATE"
    elif logical_type.lower() == "timestamp_ntz":
        return "DATETIME"
    elif logical_type.lower() in ["number", "decimal", "numeric"]:
        return "NUMERIC"
    elif logical_type.lower() == "double":
        return "BIGNUMERIC"
    elif logical_type.lower() in ["object", "record"] and not nested_fields:
        return "JSON"
    elif logical_type.lower() in ["object", "record", "array"]:
        return "RECORD"
    elif logical_type.lower() == "struct":
        return "STRUCT"
    elif logical_type.lower() == "null":
        logger.info(
            "Can't properly map field to bigquery Schema, as 'null' is not supported as a type. Mapping it to STRING."
        )
        return "STRING"
    else:
        raise DataContractException(
            type="schema",
            result="failed",
            name="Map datacontract type to bigquery data type",
            reason=f"Unsupported type {logical_type} in data contract definition.",
            engine="datacontract",
        )


def convert_type_to_bigquery(field: Union[SchemaProperty, FieldLike]) -> None | str:
    """Convert from supported datacontract types to equivalent bigquery types.
    Reference: https://cloud.google.com/bigquery/docs/reference/standard-sql/data-types

    Wraps map_type_to_bigquery with recursive expansion of complex types into
    string-based syntax (e.g. ARRAY<STRING>, STRUCT<field1 TYPE1>) for SodaCL.
    """
    field_type = _get_type(field)
    if not field_type:
        return None

    bigquery_type = _get_config_value(field, "bigqueryType")
    if bigquery_type:
        return bigquery_type

    # Complex types need string-based syntax for SodaCL
    if field_type.lower() in ["array"]:
        items = _get_items(field)
        if items:
            item_type = convert_type_to_bigquery(items)
            return f"ARRAY<{item_type}>"
        return "ARRAY<STRING>"
    if field_type.lower() in ["object", "record", "struct"]:
        nested_fields = []
        for nested_field_name, nested_field in _get_nested_fields(field).items():
            nested_field_type = convert_type_to_bigquery(nested_field)
            nested_fields.append(f"{nested_field_name} {nested_field_type}")
        return f"STRUCT<{', '.join(nested_fields)}>"

    # Simple types
    return map_type_to_bigquery(field)


def convert_type_to_trino(field: Union[SchemaProperty, FieldLike]) -> None | str:
    """Convert from supported datacontract types to equivalent trino types"""
    trino_type = _get_config_value(field, "trinoType")
    if trino_type:
        return trino_type

    base_type = _get_base_type(field)
    if not base_type:
        return None

    if base_type in ["string", "text", "varchar"]:
        return _attach_params_if_present("varchar", field)
    if base_type in ["number", "decimal", "numeric"]:
        return _attach_params_if_present("decimal", field)
    if base_type in ["int", "integer"]:
        return "integer"
    if base_type in ["long", "bigint"]:
        return "bigint"
    if base_type in ["float"]:
        return "real"
    if base_type in ["double"]:
        return "double"
    if base_type in ["timestamp", "timestamp_tz"]:
        return "timestamp(3) with time zone"
    if base_type in ["timestamp_ntz"]:
        return "timestamp(3)"
    if base_type in ["date"]:
        return "date"
    if base_type in ["time"]:
        return _attach_params_if_present("time", field)
    if base_type in ["boolean"]:
        return "boolean"
    if base_type in ["bytes"]:
        return "varbinary"
    if base_type in ["object", "record", "struct"]:
        return "json"
    if base_type in ["array"]:
        return "json"
    if _get_params(field):
        return _get_type(field)
    return None


def convert_type_to_impala(field: Union[SchemaProperty, FieldLike]) -> None | str:
    """Convert from supported data contract types to equivalent Impala types.

    Used as a fallback when `physicalType` is not present.
    """
    # Allow an explicit override via config/customProperties
    impala_type = _get_config_value(field, "impalaType")
    if impala_type:
        return impala_type

    base_type = _get_base_type(field)
    if not base_type:
        return None

    # String-like
    if base_type in ["string", "varchar", "text"]:
        return "STRING"

    # Numeric / decimal
    if base_type in ["number", "decimal", "numeric"]:
        precision = _get_precision(field) or 38
        scale = _get_scale(field) or 0
        return f"DECIMAL({precision},{scale})"

    if base_type == "float":
        return "FLOAT"
    if base_type == "double":
        return "DOUBLE"

    # Integers
    if base_type in ["integer", "int"]:
        return "INT"
    if base_type in ["long", "bigint"]:
        return "BIGINT"

    # Boolean
    if base_type == "boolean":
        return "BOOLEAN"

    # Temporal – Impala has a single TIMESTAMP type
    if base_type in ["timestamp", "timestamp_ntz", "timestamp_tz"]:
        return "TIMESTAMP"
    if base_type == "date":
        return "DATE"
    # No dedicated TIME type in Impala → store as string
    if base_type == "time":
        return "STRING"

    # Binary
    if base_type in ["bytes", "binary"]:
        return "BINARY"

    # For complex / JSON-like types we currently do not emit a type check
    # (returning None means no "has type" check is generated)
    return None


def convert_type_to_oracle(schema_property: SchemaProperty) -> None | str:
    """Convert ODCS logical types to Oracle types.

    Uses physicalType if set, otherwise maps ODCS logical types to Oracle equivalents.
    Reference: https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/Data-Types.html
    """
    if schema_property.physicalType:
        return schema_property.physicalType

    if not schema_property.logicalType:
        return None

    logical_type = schema_property.logicalType

    # ODCS logical type mappings
    mapping = {
        "string": "NVARCHAR2(2000)",
        "varchar": "NVARCHAR2(2000)",
        "text": "CLOB",
        "number": "NUMBER",
        "integer": "NUMBER",
        "int": "NUMBER",
        "long": "NUMBER",
        "bigint": "NUMBER",
        "decimal": "NUMBER",
        "numeric": "NUMBER",
        "float": "BINARY_FLOAT",
        "double": "BINARY_DOUBLE",
        "boolean": "CHAR",
        "date": "DATE",
        "time": "DATE",
        "timestamp": "TIMESTAMP(6) WITH TIME ZONE",
        "timestamp_tz": "TIMESTAMP(6) WITH TIME ZONE",
        "timestamp_ntz": "TIMESTAMP(6)",
        "bytes": "RAW(2000)",
        "object": "CLOB",
        "array": "CLOB",
    }

    return mapping.get(logical_type)
