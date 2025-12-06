import json
import logging
from typing import Dict, List, Optional, Union

from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, SchemaProperty, Server

from datacontract.export.exporter import Exporter, _check_models_for_export
from datacontract.model.exceptions import DataContractException


class BigQueryExporter(Exporter):
    def export(self, data_contract, model, server, sql_server_type, export_args) -> dict:
        self.dict_args = export_args
        model_name, model_value = _check_models_for_export(data_contract, model, self.export_format)

        # Find the server
        found_server = None
        if data_contract.servers:
            for srv in data_contract.servers:
                if srv.server == server:
                    found_server = srv
                    break

        if found_server is None:
            raise RuntimeError("Export to bigquery requires selecting a bigquery server from the data contract.")
        if found_server.type != "bigquery":
            raise RuntimeError("Export to bigquery requires selecting a bigquery server from the data contract.")

        return to_bigquery_json(model_name, model_value, found_server)


def to_bigquery_json(model_name: str, model_value: SchemaObject, server: Server) -> str:
    bigquery_table = to_bigquery_schema(model_name, model_value, server)
    return json.dumps(bigquery_table, indent=2)


def to_bigquery_schema(model_name: str, model_value: SchemaObject, server: Server) -> dict:
    return {
        "kind": "bigquery#table",
        "tableReference": {"datasetId": server.dataset, "projectId": server.project, "tableId": model_name},
        "description": model_value.description,
        "schema": {"fields": to_fields_array(model_value.properties or [])},
    }


def to_fields_array(properties: List[SchemaProperty]) -> List[Dict]:
    bq_fields = []
    for prop in properties:
        bq_fields.append(to_field(prop.name, prop))
    return bq_fields


def to_field(field_name: str, prop: SchemaProperty) -> dict:
    bq_type = map_type_to_bigquery(prop)
    bq_field = {
        "name": field_name,
        "type": bq_type,
        "mode": "REQUIRED" if prop.required else "NULLABLE",
        "description": prop.description,
    }

    field_type = prop.logicalType or ""

    # handle arrays
    if field_type.lower() == "array":
        bq_field["mode"] = "REPEATED"
        if prop.items:
            items_type = prop.items.logicalType or ""
            if items_type.lower() == "object":
                # in case the array type is a complex object, we want to copy all its fields
                bq_field["fields"] = to_fields_array(prop.items.properties or [])
            else:
                bq_field["type"] = map_type_to_bigquery(prop.items)

    # all of these can carry other fields
    elif bq_type.lower() in ["record", "struct"]:
        bq_field["fields"] = to_fields_array(prop.properties or [])

    # strings can have a maxlength
    if bq_type.lower() == "string":
        max_length = None
        if prop.logicalTypeOptions:
            max_length = prop.logicalTypeOptions.get("maxLength")
        bq_field["maxLength"] = max_length

    # number types have precision and scale
    if bq_type.lower() in ["numeric", "bignumeric"]:
        precision = None
        scale = None
        if prop.logicalTypeOptions:
            precision = prop.logicalTypeOptions.get("precision")
            scale = prop.logicalTypeOptions.get("scale")
        bq_field["precision"] = precision
        bq_field["scale"] = scale

    return bq_field


def _get_config_value(prop: SchemaProperty, key: str) -> Optional[str]:
    """Get a custom property value from a SchemaProperty."""
    if prop.customProperties is None:
        return None
    for cp in prop.customProperties:
        if cp.property == key:
            return cp.value
    return None


def map_type_to_bigquery(prop: Union[SchemaProperty, "FieldLike"]) -> str:
    """Map a property type to BigQuery type."""
    logger = logging.getLogger(__name__)

    # Handle both SchemaProperty and FieldLike (from PropertyAdapter)
    if isinstance(prop, SchemaProperty):
        # Prefer physicalType for accurate type mapping (e.g., bigint -> INT64)
        field_type = prop.physicalType or prop.logicalType
        config_value = _get_config_value(prop, "bigqueryType")
        nested_fields = prop.properties
    else:
        # FieldLike interface
        field_type = getattr(prop, 'type', None)
        config = getattr(prop, 'config', None)
        config_value = config.get("bigqueryType") if config else None
        nested_fields = getattr(prop, 'fields', None)
        if nested_fields and isinstance(nested_fields, dict):
            nested_fields = list(nested_fields.values())

    if not field_type:
        return None

    if config_value:
        return config_value

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
        return "DATETIME"
    elif field_type.lower() in ["number", "decimal", "numeric"]:
        return "NUMERIC"
    elif field_type.lower() == "double":
        return "BIGNUMERIC"
    elif field_type.lower() in ["object", "record"] and not nested_fields:
        return "JSON"
    elif field_type.lower() in ["object", "record", "array"]:
        return "RECORD"
    elif field_type.lower() == "struct":
        return "STRUCT"
    elif field_type.lower() == "null":
        logger.info(
            f"Can't properly map field to bigquery Schema, as 'null' \
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
