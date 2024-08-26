from datacontract.export.bigquery_converter import map_type_to_bigquery
from datacontract.model.data_contract_specification import Field


def convert_to_sql_type(field: Field, server_type: str) -> str:
    if server_type == "snowflake":
        return convert_to_snowflake(field)
    elif server_type == "postgres":
        return convert_type_to_postgres(field)
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


# databricks data types:
# https://docs.databricks.com/en/sql/language-manual/sql-ref-datatypes.html
def convert_to_databricks(field: Field) -> None | str:
    if field.config and "databricksType" in field.config:
        return field.config["databricksType"]
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
        return "STRUCT"
    if type.lower() in ["bytes"]:
        return "BINARY"
    if type.lower() in ["array"]:
        return "ARRAY"
    return None


def convert_to_duckdb(field: Field) -> None | str:
    type = field.type
    if type is None:
        return None
    if type.lower() in ["string", "varchar", "text"]:
        return "VARCHAR"  # aliases: VARCHAR, CHAR, BPCHAR, STRING, TEXT, VARCHAR(n)	STRING(n), TEXT(n)
    if type.lower() in ["timestamp", "timestamp_tz"]:
        return "TIMESTAMP WITH TIME ZONE"  # aliases: TIMESTAMPTZ
    if type.lower() in ["timestamp_ntz"]:
        return "DATETIME"  # timestamp with microsecond precision (ignores time zone), aliases: TIMESTAMP
    if type.lower() in ["date"]:
        return "DATE"
    if type.lower() in ["time"]:
        return "TIME"  # TIME WITHOUT TIME ZONE
    if type.lower() in ["number", "decimal", "numeric"]:
        return f"DECIMAL({field.precision},{field.scale})"
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
        return "STRUCT"
    if type.lower() in ["bytes"]:
        return "BLOB"
    if type.lower() in ["array"]:
        return "ARRAY"
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
    field_type = field.type
    if not field_type:
        return None

    # If provided sql-server config type, prefer it over default mapping
    if bigquery_type := get_type_config(field, "bigqueryType"):
        return bigquery_type

    field_type = field_type.lower()
    return map_type_to_bigquery(field_type, field.title)


def get_type_config(field: Field, config_attr: str) -> dict[str, str] | None:
    """Retrieve type configuration if provided in datacontract."""
    if not field.config:
        return None
    return field.config.get(config_attr, None)


def convert_type_to_trino(field: Field) -> None | str:
    """Convert from supported datacontract types to equivalent trino types"""
    field_type = field.type

    if field_type.lower() in ["string", "text", "varchar"]:
        return "varchar"
    # tinyint, smallint not supported by data contract
    if field_type.lower() in ["number", "decimal", "numeric"]:
        # precision and scale not supported by data contract
        return "decimal"
    if field_type.lower() in ["int", "integer"]:
        return "integer"
    if field_type.lower() in ["long", "bigint"]:
        return "bigint"
    if field_type.lower() in ["float"]:
        return "real"
    if field_type.lower() in ["timestamp", "timestamp_tz"]:
        return "timestamp(3) with time zone"
    if field_type.lower() in ["timestamp_ntz"]:
        return "timestamp(3)"
    if field_type.lower() in ["bytes"]:
        return "varbinary"
    if field_type.lower() in ["object", "record", "struct"]:
        return "json"
