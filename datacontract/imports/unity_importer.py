import json
import requests
import os
import typing

from datacontract.imports.importer import Importer
from datacontract.model.data_contract_specification import DataContractSpecification, Model, Field
from datacontract.model.exceptions import DataContractException


class UnityImporter(Importer):
    def import_source(
        self, data_contract_specification: DataContractSpecification, source: str, import_args: dict
    ) -> dict:
        if source is not None:
            data_contract_specification = import_unity_from_json(data_contract_specification, source)
        else:
            data_contract_specification = import_unity_from_api(
                data_contract_specification, import_args.get("unity_table_full_name")
            )
        return data_contract_specification


def import_unity_from_json(
    data_contract_specification: DataContractSpecification, source: str
) -> DataContractSpecification:
    try:
        with open(source, "r") as file:
            unity_schema = json.loads(file.read())
    except json.JSONDecodeError as e:
        raise DataContractException(
            type="schema",
            name="Parse unity schema",
            reason=f"Failed to parse unity schema from {source}",
            engine="datacontract",
            original_exception=e,
        )
    return convert_unity_schema(data_contract_specification, unity_schema)


def import_unity_from_api(
    data_contract_specification: DataContractSpecification, unity_table_full_name: typing.Optional[str] = None
) -> DataContractSpecification:
    databricks_instance = os.getenv("DATABRICKS_IMPORT_INSTANCE")
    access_token = os.getenv("DATABRICKS_IMPORT_ACCESS_TOKEN")

    if not databricks_instance or not access_token:
        print("Missing environment variables for Databricks instance or access token.")
        print("Both, $DATABRICKS_IMPORT_INSTANCE and $DATABRICKS_IMPORT_ACCESS_TOKEN must be set.")
        exit(1)  # Exit if variables are not set

    api_url = f"{databricks_instance}/api/2.1/unity-catalog/tables/{unity_table_full_name}"

    headers = {"Authorization": f"Bearer {access_token}"}
    response = requests.get(api_url, headers=headers)

    if response.status_code != 200:
        raise DataContractException(
            type="schema",
            name="Retrieve unity catalog schema",
            reason=f"Failed to retrieve unity catalog schema from databricks instance: {response.status_code} {response.text}",
            engine="datacontract",
        )

    convert_unity_schema(data_contract_specification, response.json())

    return data_contract_specification


def convert_unity_schema(
    data_contract_specification: DataContractSpecification, unity_schema: dict
) -> DataContractSpecification:
    if data_contract_specification.models is None:
        data_contract_specification.models = {}

    fields = import_table_fields(unity_schema.get("columns"))

    table_id = unity_schema.get("table_id")

    data_contract_specification.models[table_id] = Model(fields=fields, type="table")

    if unity_schema.get("name") is not None:
        data_contract_specification.models[table_id].title = unity_schema.get("name")

    return data_contract_specification


def import_table_fields(table_fields):
    imported_fields = {}
    for field in table_fields:
        field_name = field.get("name")
        imported_fields[field_name] = Field()
        imported_fields[field_name].required = field.get("nullable") == "false"
        imported_fields[field_name].description = field.get("comment")

        # databricks api 2.1 specifies that type_name can be any of:
        # BOOLEAN | BYTE | SHORT | INT | LONG | FLOAT | DOUBLE | DATE | TIMESTAMP | TIMESTAMP_NTZ | STRING
        # | BINARY | DECIMAL | INTERVAL | ARRAY | STRUCT | MAP | CHAR | NULL | USER_DEFINED_TYPE | TABLE_TYPE
        if field.get("type_name") in ["INTERVAL", "ARRAY", "STRUCT", "MAP", "USER_DEFINED_TYPE", "TABLE_TYPE"]:
            # complex types are not supported, yet
            raise DataContractException(
                type="schema",
                result="failed",
                name="Map unity type to data contract type",
                reason=f"type ${field.get('type_name')} is not supported yet for unity import",
                engine="datacontract",
            )

        imported_fields[field_name].type = map_type_from_unity(field.get("type_name"))

    return imported_fields


def map_type_from_unity(type_str: str):
    if type_str == "BOOLEAN":
        return "boolean"
    elif type_str == "BYTE":
        return "bytes"
    elif type_str == "SHORT":
        return "int"
    elif type_str == "INT":
        return "int"
    elif type_str == "LONG":
        return "long"
    elif type_str == "FLOAT":
        return "float"
    elif type_str == "DOUBLE":
        return "double"
    elif type_str == "DATE":
        return "date"
    elif type_str == "TIMESTAMP":
        return "timestamp"
    elif type_str == "TIMESTAMP_NTZ":
        return "timestamp_ntz"
    elif type_str == "STRING":
        return "string"
    elif type_str == "BINARY":
        return "bytes"
    elif type_str == "DECIMAL":
        return "decimal"
    elif type_str == "CHAR":
        return "varchar"
    elif type_str == "NULL":
        return "null"
    else:
        raise DataContractException(
            type="schema",
            result="failed",
            name="Map unity type to data contract type",
            reason=f"Unsupported type {type_str} in unity json definition.",
            engine="datacontract",
        )
