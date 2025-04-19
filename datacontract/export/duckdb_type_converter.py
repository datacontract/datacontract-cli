from typing import Dict

from datacontract.model.data_contract_specification import Field


# https://duckdb.org/docs/data/csv/overview.html
# ['SQLNULL', 'BOOLEAN', 'BIGINT', 'DOUBLE', 'TIME', 'DATE', 'TIMESTAMP', 'VARCHAR']
def convert_to_duckdb_csv_type(field) -> None | str:
    datacontract_type = field.type
    if datacontract_type is None:
        return "VARCHAR"
    if datacontract_type.lower() in ["string", "varchar", "text"]:
        return "VARCHAR"
    if datacontract_type.lower() in ["timestamp", "timestamp_tz"]:
        return "TIMESTAMP"
    if datacontract_type.lower() in ["timestamp_ntz"]:
        return "TIMESTAMP"
    if datacontract_type.lower() in ["date"]:
        return "DATE"
    if datacontract_type.lower() in ["time"]:
        return "TIME"
    if datacontract_type.lower() in ["number", "decimal", "numeric"]:
        # precision and scale not supported by data contract
        return "VARCHAR"
    if datacontract_type.lower() in ["float", "double"]:
        return "DOUBLE"
    if datacontract_type.lower() in ["integer", "int", "long", "bigint"]:
        return "BIGINT"
    if datacontract_type.lower() in ["boolean"]:
        return "BOOLEAN"
    if datacontract_type.lower() in ["object", "record", "struct"]:
        # not supported in CSV
        return "VARCHAR"
    if datacontract_type.lower() in ["bytes"]:
        # not supported in CSV
        return "VARCHAR"
    if datacontract_type.lower() in ["array"]:
        return "VARCHAR"
    if datacontract_type.lower() in ["null"]:
        return "SQLNULL"
    return "VARCHAR"


def convert_to_duckdb_json_type(field: Field) -> None | str:
    datacontract_type = field.type
    if datacontract_type is None:
        return "VARCHAR"
    if datacontract_type.lower() in ["array"]:
        return convert_to_duckdb_json_type(field.items) + "[]"  # type: ignore
    if datacontract_type.lower() in ["object", "record", "struct"]:
        return convert_to_duckdb_object(field.fields)
    return convert_to_duckdb_csv_type(field)


def convert_to_duckdb_object(fields: Dict[str, Field]):
    columns = [f'"{x[0]}" {convert_to_duckdb_json_type(x[1])}' for x in fields.items()]
    return f"STRUCT({', '.join(columns)})"
