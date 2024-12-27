import json
import logging
from typing import Dict, List

from datacontract.export.exporter import Exporter, _check_models_for_export
from datacontract.model.data_contract_specification import Field, Model, Server
from datacontract.model.exceptions import DataContractException


class BigQueryExporter(Exporter):
    def export(self, data_contract, model, server, sql_server_type, export_args) -> dict:
        self.dict_args = export_args
        model_name, model_value = _check_models_for_export(data_contract, model, self.export_format)
        found_server = data_contract.servers.get(server)
        if found_server is None:
            raise RuntimeError("Export to bigquery requires selecting a bigquery server from the data contract.")
        if found_server.type != "bigquery":
            raise RuntimeError("Export to bigquery requires selecting a bigquery server from the data contract.")

        return to_bigquery_json(model_name, model_value, found_server)


def to_bigquery_json(model_name: str, model_value: Model, server: Server) -> str:
    bigquery_table = to_bigquery_schema(model_name, model_value, server)
    return json.dumps(bigquery_table, indent=2)


def to_bigquery_schema(model_name: str, model_value: Model, server: Server) -> dict:
    return {
        "kind": "bigquery#table",
        "tableReference": {"datasetId": server.dataset, "projectId": server.project, "tableId": model_name},
        "description": model_value.description,
        "schema": {"fields": to_fields_array(model_value.fields)},
    }


def to_fields_array(fields: Dict[str, Field]) -> List[Dict[str, Field]]:
    bq_fields = []
    for field_name, field in fields.items():
        bq_fields.append(to_field(field_name, field))

    return bq_fields


def to_field(field_name: str, field: Field) -> dict:
    bq_type = map_type_to_bigquery(field)
    bq_field = {
        "name": field_name,
        "type": bq_type,
        "mode": "REQUIRED" if field.required else "NULLABLE",
        "description": field.description,
    }

    # handle arrays
    if field.type == "array":
        bq_field["mode"] = "REPEATED"
        if field.items.type == "object":
            # in case the array type is a complex object, we want to copy all its fields
            bq_field["fields"] = to_fields_array(field.items.fields)
        else:
            bq_field["type"] = map_type_to_bigquery(field.items)

    # all of these can carry other fields
    elif bq_type.lower() in ["record", "struct"]:
        bq_field["fields"] = to_fields_array(field.fields)

    # strings can have a maxlength
    if bq_type.lower() == "string":
        bq_field["maxLength"] = field.maxLength

    # number types have precision and scale
    if bq_type.lower() in ["numeric", "bignumeric"]:
        bq_field["precision"] = field.precision
        bq_field["scale"] = field.scale

    return bq_field


def map_type_to_bigquery(field: Field) -> str:
    logger = logging.getLogger(__name__)

    field_type = field.type
    if not field_type:
        return None

    if field.config and "bigqueryType" in field.config:
        return field.config["bigqueryType"]

    if field_type.lower() in ["string", "varchar", "text"]:
        return "STRING"
    elif field_type.lower() == "bytes":
        return "BYTES"
    elif field_type.lower() in ["int", "integer"]:
        return "INTEGER"
    elif field_type.lower() in ["long", "bigint"]:
        return "INT64"
    elif field_type.lower() == "float":
        return "FLOAT64"
    elif field_type.lower() == "boolean":
        return "BOOL"
    elif field_type.lower() in ["timestamp", "timestamp_tz"]:
        return "TIMESTAMP"
    elif field_type.lower() == "date":
        return "DATE"
    elif field_type.lower() == "timestamp_ntz":
        return "TIME"
    elif field_type.lower() in ["number", "decimal", "numeric"]:
        return "NUMERIC"
    elif field_type.lower() == "double":
        return "BIGNUMERIC"
    elif field_type.lower() in ["object", "record"] and not field.fields:
        return "JSON"
    elif field_type.lower() in ["object", "record", "array"]:
        return "RECORD"
    elif field_type.lower() == "struct":
        return "STRUCT"
    elif field_type.lower() == "null":
        logger.info(
            f"Can't properly map {field.title} to bigquery Schema, as 'null' \
                 is not supported as a type. Mapping it to STRING."
        )
        return "STRING"
    else:
        raise DataContractException(
            type="schema",
            result="failed",
            name="Map datacontract type to bigquery data type",
            reason=f"Unsupported type {field_type} in data contract definition.",
            engine="datacontract",
        )
