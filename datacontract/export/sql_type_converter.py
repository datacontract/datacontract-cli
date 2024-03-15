from datacontract.model.data_contract_specification import Field


def convert_to_sql_type(field: Field, server_type: str) -> str:
    if server_type == "snowflake":
        return convert_to_snowflake(field)
    if server_type == "postgres":
        return convert_type_to_postgres(field)
    return str(type)

# snowflake data types:
# https://docs.snowflake.com/en/sql-reference/data-types.html
def convert_to_snowflake(field) -> None | str:
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
def convert_type_to_postgres(field : Field) -> None | str:
    type = field.type
    if type is None:
        return None
    if type.lower() in ["string", "varchar", "text"]:
        if field.format == "uuid":
            return "uuid"
        return "text" # STRING does not exist, TEXT and VARCHAR are all the same in postrges
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
