import json
import logging
from typing import List

from open_data_contract_standard.model import OpenDataContractStandard, SchemaProperty

from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import (
    create_odcs,
    create_property,
    create_schema_object,
)
from datacontract.model.exceptions import DataContractException


class BigQueryImporter(Importer):
    def import_source(
        self, source: str, import_args: dict
    ) -> OpenDataContractStandard:
        if source is not None:
            return import_bigquery_from_json(source)
        else:
            return import_bigquery_from_api(
                import_args.get("bigquery_table"),
                import_args.get("bigquery_project"),
                import_args.get("bigquery_dataset"),
            )


def import_bigquery_from_json(source: str) -> OpenDataContractStandard:
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
    return convert_bigquery_schema(bigquery_schema)


def import_bigquery_from_api(
    bigquery_tables: List[str],
    bigquery_project: str,
    bigquery_dataset: str,
) -> OpenDataContractStandard:
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

    odcs = create_odcs()
    odcs.schema_ = []

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
                reason=f"Table {table} not found on bigtable schema Project {bigquery_project}, dataset {bigquery_dataset}.",
                engine="datacontract",
            )

        schema_obj = convert_bigquery_table_to_schema(api_table.to_api_repr())
        odcs.schema_.append(schema_obj)

    return odcs


def fetch_table_names(client, dataset: str) -> List[str]:
    table_names = []
    api_tables = client.list_tables(dataset)
    for api_table in api_tables:
        table_names.append(api_table.table_id)

    return table_names


def convert_bigquery_schema(bigquery_schema: dict) -> OpenDataContractStandard:
    """Convert a BigQuery schema to ODCS format."""
    odcs = create_odcs()
    odcs.schema_ = [convert_bigquery_table_to_schema(bigquery_schema)]
    return odcs


def convert_bigquery_table_to_schema(bigquery_schema: dict):
    """Convert a BigQuery table definition to an ODCS SchemaObject."""
    properties = import_table_fields(bigquery_schema.get("schema", {}).get("fields", []))

    table_id = bigquery_schema.get("tableReference", {}).get("tableId", "unknown")
    description = bigquery_schema.get("description")
    title = bigquery_schema.get("friendlyName")
    table_type = map_bigquery_type(bigquery_schema.get("type", "TABLE"))

    schema_obj = create_schema_object(
        name=table_id,
        physical_type=table_type,
        description=description,
        properties=properties,
    )

    if title:
        schema_obj.businessName = title

    return schema_obj


def import_table_fields(table_fields) -> List[SchemaProperty]:
    """Import BigQuery table fields as ODCS SchemaProperties."""
    properties = []

    for field in table_fields:
        field_name = field.get("name")
        required = field.get("mode") == "REQUIRED"
        description = field.get("description")
        field_type = field.get("type")

        if field_type == "RECORD":
            nested_properties = import_table_fields(field.get("fields", []))
            prop = create_property(
                name=field_name,
                logical_type="object",
                physical_type="RECORD",
                description=description,
                required=required if required else None,
                properties=nested_properties,
            )
        elif field_type == "STRUCT":
            nested_properties = import_table_fields(field.get("fields", []))
            prop = create_property(
                name=field_name,
                logical_type="object",
                physical_type="STRUCT",
                description=description,
                required=required if required else None,
                properties=nested_properties,
            )
        elif field_type == "RANGE":
            # Range of date/datetime/timestamp - multiple values, map to array
            items_prop = create_property(
                name="items",
                logical_type=map_type_from_bigquery(field.get("rangeElementType", {}).get("type", "STRING")),
                physical_type=field.get("rangeElementType", {}).get("type", "STRING"),
            )
            prop = create_property(
                name=field_name,
                logical_type="array",
                physical_type="RANGE",
                description=description,
                required=required if required else None,
                items=items_prop,
            )
        else:
            logical_type = map_type_from_bigquery(field_type)
            max_length = None
            precision = None
            scale = None

            if field_type == "STRING" and field.get("maxLength") is not None:
                max_length = int(field.get("maxLength"))

            if field_type in ("NUMERIC", "BIGNUMERIC"):
                if field.get("precision") is not None:
                    precision = int(field.get("precision"))
                if field.get("scale") is not None:
                    scale = int(field.get("scale"))

            prop = create_property(
                name=field_name,
                logical_type=logical_type,
                physical_type=field_type,
                description=description,
                required=required if required else None,
                max_length=max_length,
                precision=precision,
                scale=scale,
            )

        properties.append(prop)

    return properties


def map_type_from_bigquery(bigquery_type_str: str) -> str:
    """Map BigQuery type to ODCS logical type."""
    type_mapping = {
        "STRING": "string",
        "BYTES": "array",
        "INTEGER": "integer",
        "INT64": "integer",
        "FLOAT": "number",
        "FLOAT64": "number",
        "BOOLEAN": "boolean",
        "BOOL": "boolean",
        "TIMESTAMP": "date",
        "DATE": "date",
        "TIME": "date",
        "DATETIME": "date",
        "NUMERIC": "number",
        "BIGNUMERIC": "number",
        "GEOGRAPHY": "object",
        "JSON": "object",
    }

    if bigquery_type_str in type_mapping:
        return type_mapping[bigquery_type_str]

    raise DataContractException(
        type="schema",
        result="failed",
        name="Map bigquery type to data contract type",
        reason=f"Unsupported type {bigquery_type_str} in bigquery json definition.",
        engine="datacontract",
    )


def map_bigquery_type(bigquery_type: str) -> str:
    """Map BigQuery table type to ODCS physical type."""
    if bigquery_type in ("TABLE", "EXTERNAL", "SNAPSHOT"):
        return "table"
    elif bigquery_type in ("VIEW", "MATERIALIZED_VIEW"):
        return "view"
    else:
        logger = logging.getLogger(__name__)
        logger.info(
            f"Can't properly map bigquery table type '{bigquery_type}' to datacontracts model types. Mapping it to table."
        )
        return "table"
