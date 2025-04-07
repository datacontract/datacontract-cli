from typing import Dict
from datacontract.export.csv_type_converter import convert_to_duckdb_csv_type
from datacontract.model.data_contract_specification import Field

def convert_to_duckdb_json_type(field: Field) -> None | str:
    type = field.type
    if type is None:
        return "VARCHAR"
    if type.lower() in [ "array" ]:
        return convert_to_duckdb_json_type(field.items) + "[]"  # type: ignore
    if type.lower() in [ "object", "record", "struct" ]:
        return convert_to_duckdb_object(field.fields)
    return convert_to_duckdb_csv_type(field)

def convert_to_duckdb_object(fields: Dict[str, Field]):
    columns = [ f'"{x[0]}" {convert_to_duckdb_json_type(x[1])}' for x in fields.items() ]
    return f'STRUCT({", ".join(columns)})'
