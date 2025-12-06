from typing import List, Optional

from open_data_contract_standard.model import SchemaProperty


def _get_type(prop: SchemaProperty) -> Optional[str]:
    """Get the type from a schema property, checking both logical and physical type."""
    if prop.logicalType:
        return prop.logicalType
    if prop.physicalType:
        return prop.physicalType
    return None


# https://duckdb.org/docs/data/csv/overview.html
# ['SQLNULL', 'BOOLEAN', 'BIGINT', 'DOUBLE', 'TIME', 'DATE', 'TIMESTAMP', 'VARCHAR']
def convert_to_duckdb_csv_type(prop: SchemaProperty) -> None | str:
    datacontract_type = _get_type(prop)
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
        return "DOUBLE"
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


def convert_to_duckdb_json_type(prop: SchemaProperty) -> None | str:
    datacontract_type = _get_type(prop)
    if datacontract_type is None:
        return "VARCHAR"
    if datacontract_type.lower() in ["array"]:
        if prop.items:
            return convert_to_duckdb_json_type(prop.items) + "[]"  # type: ignore
        return "VARCHAR[]"
    if datacontract_type.lower() in ["object", "record", "struct"]:
        # If no properties are defined, treat as generic JSON
        if prop.properties is None or len(prop.properties) == 0:
            return "JSON"
        return convert_to_duckdb_object(prop.properties)
    return convert_to_duckdb_csv_type(prop)


def convert_to_duckdb_object(properties: List[SchemaProperty]):
    columns = [f'"{prop.name}" {convert_to_duckdb_json_type(prop)}' for prop in properties]
    return f"STRUCT({', '.join(columns)})"
