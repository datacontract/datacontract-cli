import json

from datacontract.model.data_contract_specification import \
    DataContractSpecification, Model, Field
from datacontract.model.exceptions import DataContractException


def import_bigquery(data_contract_specification: DataContractSpecification, source: str) -> DataContractSpecification:
    if data_contract_specification.models is None:
        data_contract_specification.models = {}

    try:
        with open(source, "r") as file:
            bigquery_schema = json.loads(file.read())
    except json.JSONDecodeError as e:
        raise DataContractException(
            type="schema",
            name="Parse bigquery schema",
            reason=f"Failed to parse bigquery schema from {source}",
            engine="datacontract",
            original_exception=e,
        )

    # pprint.pp(bigquery_schema)
    fields = import_table_fields(bigquery_schema["schema"]["fields"])

    # Looking at actual export data, I guess this is always set and friendlyName isn't, though I couldn't say
    # what exactly leads to friendlyName being set
    table_id = bigquery_schema["tableReference"]["tableId"]

    data_contract_specification.models[table_id] = Model(
        fields=fields,
        type='table'
    )

    # Copy the description, if it exists
    if bigquery_schema.get("description") is not None:
        data_contract_specification.models[table_id].description = bigquery_schema["description"]

    # Set the title from friendlyName if it exists
    if bigquery_schema.get("friendlyName") is not None:
        data_contract_specification.models[table_id].title = bigquery_schema["friendlyName"]

    return data_contract_specification


def import_table_fields(table_fields):
    imported_fields = {}
    for field in table_fields:
        field_name = field["name"]
        imported_fields[field_name] = Field()
        imported_fields[field_name].required = field["mode"] == "REQUIRED"
        imported_fields[field_name].description = field["description"]
        
        if field["type"] == "RECORD":
            imported_fields[field_name].type = "object"
            imported_fields[field_name].fields = import_table_fields(field["fields"])
        elif field["type"] == "STRUCT":
            imported_fields[field_name].type = "struct"
            imported_fields[field_name].fields = import_table_fields(field["fields"])
        elif field["type"] == "RANGE":
            # This is a range of date/datetime/timestamp but multiple values
            # So we map it to an array
            imported_fields[field_name].type = "array"
            imported_fields[field_name].items = Field(type = map_type_from_bigquery(field["rangeElementType"]["type"]))
        else:  # primitive type
            imported_fields[field_name].type = map_type_from_bigquery(field["type"])

        if field["type"] == "STRING":
            # in bigquery both string and bytes have maxLength but in the datacontracts
            # spec it is only valid for strings
            if field.get("maxLength") is not None:
                imported_fields[field_name].maxLength = int(field["maxLength"])
        
        if field["type"] == "NUMERIC" or field["type"] == "BIGNUMERIC":
            if field.get("precision") is not None:
                imported_fields[field_name].precision = int(field["precision"])

            if field.get("scale") is not None:
                imported_fields[field_name].scale = int(field["scale"])

    return imported_fields

def map_type_from_bigquery(bigquery_type_str: str):
    if bigquery_type_str == "STRING":
        return "string"
    elif bigquery_type_str == "BYTES":
        return "bytes"
    elif bigquery_type_str == "INTEGER":
        return "int"
    elif bigquery_type_str == "INT64":
        return "bigint"
    elif bigquery_type_str == "FLOAT":
        return "float"
    elif bigquery_type_str == "FLOAT64":
        return "double"
    elif bigquery_type_str == "BOOLEAN" or bigquery_type_str == "BOOL":
        return "boolean"
    elif bigquery_type_str == "TIMESTAMP":
        return "timestamp"
    elif bigquery_type_str == "DATE":
        return "date"
    elif bigquery_type_str == "TIME":
        return "timestamp_ntz"
    elif bigquery_type_str == "DATETIME":
        return "timestamp"
    elif bigquery_type_str == "NUMERIC":
        return "numeric"
    elif bigquery_type_str == "BIGNUMERIC":
        return "double"
    elif bigquery_type_str == "GEOGRAPHY":
        return "object"
    elif bigquery_type_str == "JSON":
        return "object"
    else:
        raise DataContractException(
            type="schema",
            result="failed",
            name="Map bigquery type to data contract type",
            reason=f"Unsupported type {bigquery_type_str} in bigquery json definition.",
            engine="datacontract",
        )
