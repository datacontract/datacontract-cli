import json
from typing import Dict, List

from open_data_contract_standard.model import SchemaObject, SchemaProperty, Server

from datacontract.export.exporter import Exporter, _check_schema_name_for_export
from datacontract.export.sql_type_converter import map_type_to_bigquery


class BigQueryExporter(Exporter):
    def export(self, data_contract, schema_name, server, sql_server_type, export_args) -> str:
        self.dict_args = export_args
        schema_name, schema_object = _check_schema_name_for_export(data_contract, schema_name, self.export_format)

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

        return to_bigquery_json(schema_name, schema_object, found_server)


def to_bigquery_json(schema_name: str, schema_object: SchemaObject, server: Server) -> str:
    bigquery_table = to_bigquery_schema(schema_object, server)
    return json.dumps(bigquery_table, indent=2)


def to_bigquery_schema(schema_object: SchemaObject, server: Server) -> dict:
    return {
        "kind": "bigquery#table",
        "tableReference": {
            "datasetId": server.dataset,
            "projectId": server.project,
            "tableId": schema_object.physicalName or schema_object.name,
        },
        "description": schema_object.description,
        "schema": {"fields": to_bigquery_fields_array(schema_object.properties or [])},
    }


def to_bigquery_fields_array(properties: List[SchemaProperty]) -> List[Dict]:
    bq_fields = []
    for prop in properties:
        bq_fields.append(to_bigquery_field(prop))
    return bq_fields


def to_bigquery_field(prop: SchemaProperty) -> dict:
    bq_type = map_type_to_bigquery(prop)
    field_name = prop.physicalName or prop.name
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
                bq_field["fields"] = to_bigquery_fields_array(prop.items.properties or [])
            else:
                bq_field["type"] = map_type_to_bigquery(prop.items)

    # all of these can carry other fields
    elif bq_type.lower() in ["record", "struct"]:
        bq_field["fields"] = to_bigquery_fields_array(prop.properties or [])

    # strings can have a maxlength
    if bq_type.lower() == "string":
        max_length = None
        if prop.logicalTypeOptions:
            max_length = prop.logicalTypeOptions.get("maxLength")
        bq_field["maxLength"] = max_length

    # number types have precision and scale (from customProperties)
    if bq_type.lower() in ["numeric", "bignumeric"]:
        precision = _get_custom_property(prop, "precision")
        scale = _get_custom_property(prop, "scale")
        bq_field["precision"] = int(precision) if precision is not None else None
        bq_field["scale"] = int(scale) if scale is not None else None

    return bq_field


def _get_custom_property(prop: SchemaProperty, key: str):
    """Get a custom property value from a SchemaProperty."""
    if prop.customProperties is None:
        return None
    for cp in prop.customProperties:
        if cp.property == key:
            return cp.value
    return None
