from datacontract.export.bigquery_converter import map_type_to_bigquery
from datacontract.model.data_contract_specification import Field


def convert_to_sql_type(field: Field, server_type: str) -> str:
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
    return field.type


# snowflake data types:
# https://docs.snowflake.com/en/sql-reference/data-types.html
def convert_to_snowflake(field: Field) -> None | str:
    if field.config and "snowflakeType" in field.config:
        return field.config["snowflakeType"]

    type = field.type
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
def convert_type_to_postgres(field: Field) -> None | str:
    if field.config and "postgresType" in field.config:
        return field.config["postgresType"]

    type = field.type
    if type is None:
        return None
    if type.lower() in ["string", "varchar", "text"]:
        if field.format == "uuid":
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
        return convert_to_sql_type(field.items, "postgres") + "[]"
    return None


# dataframe data types:
# https://spark.apache.org/docs/latest/sql-ref-datatypes.html
def convert_to_dataframe(field: Field) -> None | str:
    if field.config and "dataframeType" in field.config:
        return field.config["dataframeType"]
    type = field.type
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
        # precision and scale not supported by data contract
        return "DECIMAL"
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
        for nested_field_name, nested_field in field.fields.items():
            nested_field_type = convert_to_dataframe(nested_field)
            nested_fields.append(f"{nested_field_name}:{nested_field_type}")
        return f"STRUCT<{','.join(nested_fields)}>"
    if type.lower() in ["bytes"]:
        return "BINARY"
    if type.lower() in ["array"]:
        item_type = convert_to_dataframe(field.items)
        return f"ARRAY<{item_type}>"
    return None


# databricks data types:
# https://docs.databricks.com/en/sql/language-manual/sql-ref-datatypes.html
def convert_to_databricks(field: Field) -> None | str:
    type = field.type
    if (
        field.config
        and "databricksType" in field.config
        and type.lower() not in ["array", "object", "record", "struct"]
    ):
        return field.config["databricksType"]
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
        # precision and scale not supported by data contract
        return "DECIMAL"
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
        for nested_field_name, nested_field in field.fields.items():
            nested_field_type = convert_to_databricks(nested_field)
            nested_fields.append(f"{nested_field_name} {nested_field_type}")
        return f"STRUCT<{', '.join(nested_fields)}>"
    if type.lower() in ["bytes"]:
        return "BINARY"
    if type.lower() in ["array"]:
        item_type = convert_to_databricks(field.items)
        return f"ARRAY<{item_type}>"
    if type.lower() in ["variant"]:
        return "VARIANT"
    return None


def convert_to_duckdb(field: Field) -> None | str:
    """
    Convert a data contract field to the corresponding DuckDB SQL type.

    Parameters:
    field (Field): The data contract field to convert.

    Returns:
    str: The corresponding DuckDB SQL type.
    """
    # Check
    if field is None or field.type is None:
        return None

    # Get
    type_lower = field.type.lower()

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
        return f"DECIMAL({field.precision},{field.scale})"

    # Check list and map
    if type_lower == "list" or type_lower == "array":
        item_type = convert_to_duckdb(field.items)
        return f"{item_type}[]"
    if type_lower == "map":
        key_type = convert_to_duckdb(field.keys)
        value_type = convert_to_duckdb(field.values)
        return f"MAP({key_type}, {value_type})"
    if type_lower == "struct" or type_lower == "object" or type_lower == "record":
        structure_field = "STRUCT("
        field_strings = []
        for fieldKey, fieldValue in field.fields.items():
            field_strings.append(f"{fieldKey} {convert_to_duckdb(fieldValue)}")
        structure_field += ", ".join(field_strings)
        structure_field += ")"
        return structure_field

    # Return none
    return None


def convert_type_to_sqlserver(field: Field) -> None | str:
    """Convert from supported datacontract types to equivalent sqlserver types"""
    field_type = field.type
    if not field_type:
        return None

    # If provided sql-server config type, prefer it over default mapping
    if sqlserver_type := get_type_config(field, "sqlserverType"):
        return sqlserver_type

    field_type = field_type.lower()
    if field_type in ["string", "varchar", "text"]:
        if field.format == "uuid":
            return "uniqueidentifier"
        return "varchar"
    if field_type in ["timestamp", "timestamp_tz"]:
        return "datetimeoffset"
    if field_type in ["timestamp_ntz"]:
        if field.format == "datetime":
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


def convert_type_to_bigquery(field: Field) -> None | str:
    """Convert from supported datacontract types to equivalent bigquery types"""

    # BigQuery exporter cannot be used for complex types, as the exporter has different syntax than SodaCL

    field_type = field.type
    if not field_type:
        return None

    if field.config and "bigqueryType" in field.config:
        return field.config["bigqueryType"]

    if field_type.lower() in ["array"]:
        item_type = convert_type_to_bigquery(field.items)
        return f"ARRAY<{item_type}>"

    if field_type.lower() in ["object", "record", "struct"]:
        nested_fields = []
        for nested_field_name, nested_field in field.fields.items():
            nested_field_type = convert_type_to_bigquery(nested_field)
            nested_fields.append(f"{nested_field_name} {nested_field_type}")
        return f"STRUCT<{', '.join(nested_fields)}>"

    return map_type_to_bigquery(field)


def get_type_config(field: Field, config_attr: str) -> dict[str, str] | None:
    """Retrieve type configuration if provided in datacontract."""
    if not field.config:
        return None
    return field.config.get(config_attr, None)


def convert_type_to_trino(field: Field) -> None | str:
    """Convert from supported datacontract types to equivalent trino types"""
    if field.config and "trinoType" in field.config:
        return field.config["trinoType"]

    field_type = field.type.lower()
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
