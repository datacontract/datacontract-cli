from typing import Any, Dict, Optional, Protocol, Union

from open_data_contract_standard.model import SchemaProperty


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
    """Get the type from a field, handling both ODCS and DCS. Prefers physicalType for accuracy."""
    if isinstance(field, SchemaProperty):
        # Prefer physicalType for accurate type mapping
        if field.physicalType:
            return field.physicalType
        return field.logicalType
    return field.type


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


def convert_to_sql_type(field: Union[SchemaProperty, FieldLike], server_type: str) -> str:
    physical_type = _get_config_value(field, "physicalType")
    if physical_type:
        return physical_type

    if server_type == "snowflake":
        return convert_to_snowflake(field)
    elif server_type == "postgres":
        return convert_type_to_postgres(field)
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

    return _get_type(field)


# snowflake data types:
# https://docs.snowflake.com/en/sql-reference/data-types.html
def convert_to_snowflake(field: Union[SchemaProperty, FieldLike]) -> None | str:
    snowflake_type = _get_config_value(field, "snowflakeType")
    if snowflake_type:
        return snowflake_type

    type = _get_type(field)
    # currently optimized for snowflake
    # LEARNING: data contract has no direct support for CHAR,CHARACTER
    # LEARNING: data contract has no support for "date-time", "datetime", "time"
    # LEARNING: No precision and scale support in data contract
    # LEARNING: no support for any
    # GEOGRAPHY and GEOMETRY are not supported by the mapping
    if type is None:
        return None
    if type.lower() in ["string", "varchar", "text"]:
        return type.upper()  # STRING, TEXT, VARCHAR are all the same in snowflake
    if type.lower() in ["timestamp", "timestamp_tz"]:
        return "TIMESTAMP_TZ"
    if type.lower() in ["timestamp_ntz"]:
        return "TIMESTAMP_NTZ"
    if type.lower() in ["date"]:
        return "DATE"
    if type.lower() in ["time"]:
        return "TIME"
    if type.lower() in ["number", "decimal", "numeric"]:
        # precision and scale not supported by data contract
        return "NUMBER"
    if type.lower() in ["float", "double"]:
        return "FLOAT"
    if type.lower() in ["integer", "int", "long", "bigint"]:
        return "NUMBER"  # always NUMBER(38,0)
    if type.lower() in ["boolean"]:
        return "BOOLEAN"
    if type.lower() in ["object", "record", "struct"]:
        return "OBJECT"
    if type.lower() in ["bytes"]:
        return "BINARY"
    if type.lower() in ["array"]:
        return "ARRAY"
    return None


# https://www.postgresql.org/docs/current/datatype.html
# Using the name whenever possible
def convert_type_to_postgres(field: Union[SchemaProperty, FieldLike]) -> None | str:
    postgres_type = _get_config_value(field, "postgresType")
    if postgres_type:
        return postgres_type

    type = _get_type(field)
    if type is None:
        return None
    format = _get_format(field)
    if type.lower() in ["string", "varchar", "text"]:
        if format == "uuid":
            return "uuid"
        return "text"  # STRING does not exist, TEXT and VARCHAR are all the same in postrges
    if type.lower() in ["timestamp", "timestamp_tz"]:
        return "timestamptz"
    if type.lower() in ["timestamp_ntz"]:
        return "timestamp"
    if type.lower() in ["date"]:
        return "date"
    if type.lower() in ["time"]:
        return "time"
    if type.lower() in ["number", "decimal", "numeric"]:
        # precision and scale not supported by data contract
        if type.lower() == "number":
            return "numeric"
        return type.lower()
    if type.lower() in ["float"]:
        return "real"
    if type.lower() in ["double"]:
        return "double precision"
    if type.lower() in ["integer", "int", "bigint"]:
        return type.lower()
    if type.lower() in ["long"]:
        return "bigint"
    if type.lower() in ["boolean"]:
        return "boolean"
    if type.lower() in ["object", "record", "struct"]:
        return "jsonb"
    if type.lower() in ["bytes"]:
        return "bytea"
    if type.lower() in ["array"]:
        items = _get_items(field)
        if items:
            return convert_to_sql_type(items, "postgres") + "[]"
        return "text[]"
    return None


# dataframe data types:
# https://spark.apache.org/docs/latest/sql-ref-datatypes.html
def convert_to_dataframe(field: Union[SchemaProperty, FieldLike]) -> None | str:
    dataframe_type = _get_config_value(field, "dataframeType")
    if dataframe_type:
        return dataframe_type
    type = _get_type(field)
    if type is None:
        return None
    if type.lower() in ["string", "varchar", "text"]:
        return "STRING"
    if type.lower() in ["timestamp", "timestamp_tz"]:
        return "TIMESTAMP"
    if type.lower() in ["timestamp_ntz"]:
        return "TIMESTAMP_NTZ"
    if type.lower() in ["date"]:
        return "DATE"
    if type.lower() in ["time"]:
        return "STRING"
    if type.lower() in ["number", "decimal", "numeric"]:
        precision = _get_precision(field)
        scale = _get_scale(field)
        precision = precision if precision is not None else 38
        scale = scale if scale is not None else 0
        return f"DECIMAL({precision},{scale})"
    if type.lower() in ["float"]:
        return "FLOAT"
    if type.lower() in ["double"]:
        return "DOUBLE"
    if type.lower() in ["integer", "int"]:
        return "INT"
    if type.lower() in ["long", "bigint"]:
        return "BIGINT"
    if type.lower() in ["boolean"]:
        return "BOOLEAN"
    if type.lower() in ["object", "record", "struct"]:
        nested_fields = []
        for nested_field_name, nested_field in _get_nested_fields(field).items():
            nested_field_type = convert_to_dataframe(nested_field)
            nested_fields.append(f"{nested_field_name}:{nested_field_type}")
        return f"STRUCT<{','.join(nested_fields)}>"
    if type.lower() in ["bytes"]:
        return "BINARY"
    if type.lower() in ["array"]:
        items = _get_items(field)
        if items:
            item_type = convert_to_dataframe(items)
            return f"ARRAY<{item_type}>"
        return "ARRAY<STRING>"
    return None


# databricks data types:
# https://docs.databricks.com/en/sql/language-manual/sql-ref-datatypes.html
def convert_to_databricks(field: Union[SchemaProperty, FieldLike]) -> None | str:
    type = _get_type(field)
    databricks_type = _get_config_value(field, "databricksType")
    if (
        databricks_type
        and type
        and type.lower() not in ["array", "object", "record", "struct"]
    ):
        return databricks_type
    if type is None:
        return None
    if type.lower() in ["string", "varchar", "text"]:
        return "STRING"
    if type.lower() in ["timestamp", "timestamp_tz"]:
        return "TIMESTAMP"
    if type.lower() in ["timestamp_ntz"]:
        return "TIMESTAMP_NTZ"
    if type.lower() in ["date"]:
        return "DATE"
    if type.lower() in ["time"]:
        return "STRING"
    if type.lower() in ["number", "decimal", "numeric"]:
        precision = _get_precision(field)
        scale = _get_scale(field)
        precision = precision if precision is not None else 38
        scale = scale if scale is not None else 0
        return f"DECIMAL({precision},{scale})"
    if type.lower() in ["float"]:
        return "FLOAT"
    if type.lower() in ["double"]:
        return "DOUBLE"
    if type.lower() in ["integer", "int"]:
        return "INT"
    if type.lower() in ["long", "bigint"]:
        return "BIGINT"
    if type.lower() in ["boolean"]:
        return "BOOLEAN"
    if type.lower() in ["object", "record", "struct"]:
        nested_fields = []
        for nested_field_name, nested_field in _get_nested_fields(field).items():
            nested_field_type = convert_to_databricks(nested_field)
            nested_fields.append(f"{nested_field_name}:{nested_field_type}")
        return f"STRUCT<{','.join(nested_fields)}>"
    if type.lower() in ["bytes"]:
        return "BINARY"
    if type.lower() in ["array"]:
        items = _get_items(field)
        if items:
            item_type = convert_to_databricks(items)
            return f"ARRAY<{item_type}>"
        return "ARRAY<STRING>"
    if type.lower() in ["variant"]:
        return "VARIANT"
    return None


def convert_to_duckdb(field: Union[SchemaProperty, FieldLike]) -> None | str:
    """
    Convert a data contract field to the corresponding DuckDB SQL type.

    Parameters:
    field: The data contract field to convert (SchemaProperty or FieldLike).

    Returns:
    str: The corresponding DuckDB SQL type.
    """
    # Check
    type = _get_type(field)
    if field is None or type is None:
        return None

    # Get
    type_lower = type.lower()

    # Prepare
    type_mapping = {
        "varchar": "VARCHAR",
        "string": "VARCHAR",
        "text": "VARCHAR",
        "binary": "BLOB",
        "bytes": "BLOB",
        "blob": "BLOB",
        "boolean": "BOOLEAN",
        "float": "FLOAT",
        "double": "DOUBLE",
        "int": "INTEGER",
        "int32": "INTEGER",
        "integer": "INTEGER",
        "int64": "BIGINT",
        "long": "BIGINT",
        "bigint": "BIGINT",
        "date": "DATE",
        "time": "TIME",
        "timestamp": "TIMESTAMP WITH TIME ZONE",
        "timestamp_tz": "TIMESTAMP WITH TIME ZONE",
        "timestamp_ntz": "TIMESTAMP",
    }

    # Convert simple mappings
    if type_lower in type_mapping:
        return type_mapping[type_lower]

    # convert decimal numbers with precision and scale
    if type_lower == "decimal" or type_lower == "number" or type_lower == "numeric":
        precision = _get_precision(field)
        scale = _get_scale(field)
        return f"DECIMAL({precision},{scale})"

    # Check list and map
    if type_lower == "list" or type_lower == "array":
        items = _get_items(field)
        if items:
            item_type = convert_to_duckdb(items)
            return f"{item_type}[]"
        return "VARCHAR[]"
    if type_lower == "map":
        # For ODCS, we need to get key/value types from customProperties
        keys = _get_config_value(field, "mapKeys")
        values = _get_config_value(field, "mapValues")
        key_type = keys if keys else "VARCHAR"
        value_type = values if values else "VARCHAR"
        return f"MAP({key_type}, {value_type})"
    if type_lower == "struct" or type_lower == "object" or type_lower == "record":
        structure_field = "STRUCT("
        field_strings = []
        for fieldKey, fieldValue in _get_nested_fields(field).items():
            field_strings.append(f"{fieldKey} {convert_to_duckdb(fieldValue)}")
        structure_field += ", ".join(field_strings)
        structure_field += ")"
        return structure_field

    # Return none
    return None


def convert_type_to_sqlserver(field: Union[SchemaProperty, FieldLike]) -> None | str:
    """Convert from supported datacontract types to equivalent sqlserver types"""
    field_type = _get_type(field)
    if not field_type:
        return None

    # If provided sql-server config type, prefer it over default mapping
    sqlserver_type = _get_config_value(field, "sqlserverType")
    if sqlserver_type:
        return sqlserver_type

    field_type = field_type.lower()
    format = _get_format(field)
    if field_type in ["string", "varchar", "text"]:
        if format == "uuid":
            return "uniqueidentifier"
        return "varchar"
    if field_type in ["timestamp", "timestamp_tz"]:
        return "datetimeoffset"
    if field_type in ["timestamp_ntz"]:
        if format == "datetime":
            return "datetime"
        return "datetime2"
    if field_type in ["date"]:
        return "date"
    if field_type in ["time"]:
        return "time"
    if field_type in ["number", "decimal", "numeric"]:
        # precision and scale not supported by data contract
        if field_type == "number":
            return "numeric"
        return field_type
    if field_type in ["float"]:
        return "float"
    if field_type in ["double"]:
        return "double precision"
    if field_type in ["integer", "int", "bigint"]:
        return field_type
    if field_type in ["long"]:
        return "bigint"
    if field_type in ["boolean"]:
        return "bit"
    if field_type in ["object", "record", "struct"]:
        return "jsonb"
    if field_type in ["bytes"]:
        return "binary"
    if field_type in ["array"]:
        raise NotImplementedError("SQLServer does not support array types.")
    return None


def convert_type_to_bigquery(field: Union[SchemaProperty, FieldLike]) -> None | str:
    """Convert from supported datacontract types to equivalent bigquery types"""
    # Import here to avoid circular import
    from datacontract.export.bigquery_exporter import map_type_to_bigquery

    # BigQuery exporter cannot be used for complex types, as the exporter has different syntax than SodaCL

    field_type = _get_type(field)
    if not field_type:
        return None

    bigquery_type = _get_config_value(field, "bigqueryType")
    if bigquery_type:
        return bigquery_type

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

    return map_type_to_bigquery(field)


def convert_type_to_trino(field: Union[SchemaProperty, FieldLike]) -> None | str:
    """Convert from supported datacontract types to equivalent trino types"""
    trino_type = _get_config_value(field, "trinoType")
    if trino_type:
        return trino_type

    field_type = _get_type(field)
    if not field_type:
        return None
    field_type = field_type.lower()
    if field_type in ["string", "text", "varchar"]:
        return "varchar"
    # tinyint, smallint not supported by data contract
    if field_type in ["number", "decimal", "numeric"]:
        # precision and scale not supported by data contract
        return "decimal"
    if field_type in ["int", "integer"]:
        return "integer"
    if field_type in ["long", "bigint"]:
        return "bigint"
    if field_type in ["float"]:
        return "real"
    if field_type in ["timestamp", "timestamp_tz"]:
        return "timestamp(3) with time zone"
    if field_type in ["timestamp_ntz"]:
        return "timestamp(3)"
    if field_type in ["bytes"]:
        return "varbinary"
    if field_type in ["object", "record", "struct"]:
        return "json"
    return None


def convert_type_to_impala(field: Union[SchemaProperty, FieldLike]) -> None | str:
    """Convert from supported data contract types to equivalent Impala types.

    Used as a fallback when `physicalType` is not present.
    """
    # Allow an explicit override via config/customProperties
    impala_type = _get_config_value(field, "impalaType")
    if impala_type:
        return impala_type

    field_type = _get_type(field)
    if not field_type:
        return None

    t = field_type.lower()

    # String-like
    if t in ["string", "varchar", "text"]:
        return "STRING"

    # Numeric / decimal
    if t in ["number", "decimal", "numeric"]:
        precision = _get_precision(field) or 38
        scale = _get_scale(field) or 0
        return f"DECIMAL({precision},{scale})"

    if t == "float":
        return "FLOAT"
    if t == "double":
        return "DOUBLE"

    # Integers
    if t in ["integer", "int"]:
        return "INT"
    if t in ["long", "bigint"]:
        return "BIGINT"

    # Boolean
    if t == "boolean":
        return "BOOLEAN"

    # Temporal – Impala has a single TIMESTAMP type
    if t in ["timestamp", "timestamp_ntz", "timestamp_tz"]:
        return "TIMESTAMP"
    if t == "date":
        return "DATE"
    # No dedicated TIME type in Impala → store as string
    if t == "time":
        return "STRING"

    # Binary
    if t in ["bytes", "binary"]:
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
        "string": "NVARCHAR2",
        "number": "NUMBER",
        "integer": "NUMBER",
        "float": "BINARY_FLOAT",
        "double": "BINARY_DOUBLE",
        "boolean": "CHAR",
        "date": "DATE",
        "timestamp": "TIMESTAMP(6) WITH TIME ZONE",
        "bytes": "RAW",
        "object": "CLOB",
        "array": "CLOB",
    }

    return mapping.get(logical_type)