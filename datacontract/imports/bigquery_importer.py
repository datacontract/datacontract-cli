import json
import logging
from typing import List

from datacontract.imports.importer import Importer
from datacontract.model.data_contract_specification import DataContractSpecification, Model, Field
from datacontract.model.exceptions import DataContractException


class BigQueryImporter(Importer):
    def import_source(
        self, data_contract_specification: DataContractSpecification, source: str, import_args: dict
    ) -> DataContractSpecification:
        if source is not None:
            data_contract_specification = import_bigquery_from_json(data_contract_specification, source)
        else:
            data_contract_specification = import_bigquery_from_api(
                data_contract_specification,
                import_args.get("bigquery_table"),
                import_args.get("bigquery_project"),
                import_args.get("bigquery_dataset"),
            )
        return data_contract_specification


def import_bigquery_from_json(
    data_contract_specification: DataContractSpecification, source: str
) -> DataContractSpecification:
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
    return convert_bigquery_schema(data_contract_specification, bigquery_schema)


def import_bigquery_from_api(
    data_contract_specification: DataContractSpecification,
    bigquery_tables: List[str],
    bigquery_project: str,
    bigquery_dataset: str,
) -> DataContractSpecification:
    try:
        from google.cloud import bigquery
    except ImportError as e:
        raise DataContractException(
            type="schema",
            result="failed",
            name="bigquery extra missing",
            reason="Install the extra datacontract-cli[bigquery] to use bigquery",
            engine="datacontract",
            original_exception=e,
        )

    client = bigquery.Client(project=bigquery_project)

    if bigquery_tables is None:
        bigquery_tables = fetch_table_names(client, bigquery_dataset)

    for table in bigquery_tables:
        try:
            api_table = client.get_table("{}.{}.{}".format(bigquery_project, bigquery_dataset, table))

        except ValueError as e:
            raise DataContractException(
                type="schema",
                result="failed",
                name="Invalid table name for bigquery API",
                reason=f"Tablename {table} is invalid for the bigquery API",
                original_exception=e,
                engine="datacontract",
            )

        if api_table is None:
            raise DataContractException(
                type="request",
                result="failed",
                name="Query bigtable Schema from API",
                reason=f"Table {table} bnot found on bigtable schema Project {bigquery_project}, dataset {bigquery_dataset}.",
                engine="datacontract",
            )

        convert_bigquery_schema(data_contract_specification, api_table.to_api_repr())

    return data_contract_specification


def fetch_table_names(client, dataset: str) -> List[str]:
    table_names = []
    api_tables = client.list_tables(dataset)
    for api_table in api_tables:
        table_names.append(api_table.table_id)

    return table_names


def convert_bigquery_schema(
    data_contract_specification: DataContractSpecification, bigquery_schema: dict
) -> DataContractSpecification:
    if data_contract_specification.models is None:
        data_contract_specification.models = {}

    fields = import_table_fields(bigquery_schema.get("schema").get("fields"))

    # Looking at actual export data, I guess this is always set and friendlyName isn't, though I couldn't say
    # what exactly leads to friendlyName being set
    table_id = bigquery_schema.get("tableReference").get("tableId")

    data_contract_specification.models[table_id] = Model(
        fields=fields, type=map_bigquery_type(bigquery_schema.get("type"))
    )

    # Copy the description, if it exists
    if bigquery_schema.get("description") is not None:
        data_contract_specification.models[table_id].description = bigquery_schema.get("description")

    # Set the title from friendlyName if it exists
    if bigquery_schema.get("friendlyName") is not None:
        data_contract_specification.models[table_id].title = bigquery_schema.get("friendlyName")

    return data_contract_specification


def import_table_fields(table_fields):
    imported_fields = {}
    for field in table_fields:
        field_name = field.get("name")
        imported_fields[field_name] = Field()
        imported_fields[field_name].required = field.get("mode") == "REQUIRED"
        imported_fields[field_name].description = field.get("description")

        if field.get("type") == "RECORD":
            imported_fields[field_name].type = "object"
            imported_fields[field_name].fields = import_table_fields(field.get("fields"))
        elif field.get("type") == "STRUCT":
            imported_fields[field_name].type = "struct"
            imported_fields[field_name].fields = import_table_fields(field.get("fields"))
        elif field.get("type") == "RANGE":
            # This is a range of date/datetime/timestamp but multiple values
            # So we map it to an array
            imported_fields[field_name].type = "array"
            imported_fields[field_name].items = Field(
                type=map_type_from_bigquery(field["rangeElementType"].get("type"))
            )
        else:  # primitive type
            imported_fields[field_name].type = map_type_from_bigquery(field.get("type"))

        if field.get("type") == "STRING":
            # in bigquery both string and bytes have maxLength but in the datacontracts
            # spec it is only valid for strings
            if field.get("maxLength") is not None:
                imported_fields[field_name].maxLength = int(field.get("maxLength"))

        if field.get("type") == "NUMERIC" or field.get("type") == "BIGNUMERIC":
            if field.get("precision") is not None:
                imported_fields[field_name].precision = int(field.get("precision"))

            if field.get("scale") is not None:
                imported_fields[field_name].scale = int(field.get("scale"))

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


def map_bigquery_type(bigquery_type: str) -> str:
    if bigquery_type == "TABLE" or bigquery_type == "EXTERNAL" or bigquery_type == "SNAPSHOT":
        return "table"
    elif bigquery_type == "VIEW" or bigquery_type == "MATERIALIZED_VIEW":
        return "view"
    else:
        logger = logging.getLogger(__name__)
        logger.info(
            f"Can't properly map bigquery table type '{bigquery_type}' to datacontracts model types. Mapping it to table."
        )
        return "table"
