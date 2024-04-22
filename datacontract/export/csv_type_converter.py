# https://duckdb.org/docs/data/csv/overview.html
# ['SQLNULL', 'BOOLEAN', 'BIGINT', 'DOUBLE', 'TIME', 'DATE', 'TIMESTAMP', 'VARCHAR']
def convert_to_duckdb_csv_type(field) -> None | str:
    type = field.type
    if type is None:
        return "VARCHAR"
    if type.lower() in ["string", "varchar", "text"]:
        return "VARCHAR"
    if type.lower() in ["timestamp", "timestamp_tz"]:
        return "TIMESTAMP"
    if type.lower() in ["timestamp_ntz"]:
        return "TIMESTAMP"
    if type.lower() in ["date"]:
        return "DATE"
    if type.lower() in ["time"]:
        return "TIME"
    if type.lower() in ["number", "decimal", "numeric"]:
        # precision and scale not supported by data contract
        return "VARCHAR"
    if type.lower() in ["float", "double"]:
        return "DOUBLE"
    if type.lower() in ["integer", "int", "long", "bigint"]:
        return "BIGINT"
    if type.lower() in ["boolean"]:
        return "BOOLEAN"
    if type.lower() in ["object", "record", "struct"]:
        # not supported in CSV
        return "VARCHAR"
    if type.lower() in ["bytes"]:
        # not supported in CSV
        return "VARCHAR"
    if type.lower() in ["array"]:
        return "VARCHAR"
    if type.lower() in ["null"]:
        return "SQLNULL"
    return "VARCHAR"
