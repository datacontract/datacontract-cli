from typing import Dict

import yaml

from datacontract.export.exporter import Exporter
from datacontract.model.data_contract_specification import DataContractSpecification, Model, Field, Server


class DataCatererExporter(Exporter):
    """
    Exporter class for Data Caterer.
    Creates a YAML file, based on the data contract, for Data Caterer to generate synthetic data.
    """

    def export(self, data_contract, model, server, sql_server_type, export_args) -> dict:
        return to_data_caterer_generate_yaml(data_contract, server)


def to_data_caterer_generate_yaml(data_contract_spec: DataContractSpecification, server):
    generation_task = {"name": data_contract_spec.info.title, "steps": []}
    server_info = _get_server_info(data_contract_spec, server)

    for model_key, model_value in data_contract_spec.models.items():
        odcs_table = _to_data_caterer_generate_step(model_key, model_value, server_info)
        generation_task["steps"].append(odcs_table)
    return yaml.dump(generation_task, indent=2, sort_keys=False, allow_unicode=True)


def _get_server_info(data_contract_spec: DataContractSpecification, server):
    if server is not None and server in data_contract_spec.servers:
        return data_contract_spec.servers.get(server)
    elif server is not None:
        raise Exception(f"Server name not found in servers list in data contract, server-name={server}")
    elif len(data_contract_spec.servers.keys()) > 0:
        return next(iter(data_contract_spec.servers.values()))
    else:
        return None


def _to_data_caterer_generate_step(model_key, model_value: Model, server: Server) -> dict:
    step = {
        "name": model_key,
        "type": _to_step_type(server),
        "options": _to_data_source_options(model_key, server),
        "schema": [],
    }
    fields = _to_fields(model_value.fields)
    if fields:
        step["schema"] = fields
    return step


def _to_step_type(server: Server):
    if server is not None and server.type is not None:
        if server.type in ["s3", "gcs", "azure", "local"]:
            return server.format
        else:
            return server.type
    else:
        return "csv"


def _to_data_source_options(model_key, server: Server):
    options = {}
    if server is not None and server.type is not None:
        if server.type in ["s3", "gcs", "azure", "local"]:
            if server.path is not None:
                options["path"] = server.path
            elif server.location is not None:
                options["path"] = server.location
            else:
                options["path"] = "/tmp/data_caterer_data"
        elif server.type == "postgres":
            options["schema"] = server.schema_
            options["table"] = model_key
        elif server.type == "kafka":
            options["topic"] = server.topic

    return options


def _to_fields(fields: Dict[str, Field]) -> list:
    dc_fields = []
    for field_name, field in fields.items():
        column = _to_field(field_name, field)
        dc_fields.append(column)
    return dc_fields


def _to_field(field_name: str, field: Field) -> dict:
    dc_field = {"name": field_name}
    dc_generator_opts = {}

    if field.type is not None:
        new_type = _to_data_type(field.type)
        dc_field["type"] = _to_data_type(field.type)
        if new_type == "object" or new_type == "record" or new_type == "struct":
            # need to get nested field definitions
            nested_fields = _to_fields(field.fields)
            dc_field["schema"] = {"fields": nested_fields}

    if field.enum is not None and len(field.enum) > 0:
        dc_generator_opts["oneOf"] = field.enum
    if field.unique is not None and field.unique:
        dc_generator_opts["isUnique"] = field.unique
    if field.minLength is not None:
        dc_generator_opts["minLength"] = field.minLength
    if field.maxLength is not None:
        dc_generator_opts["maxLength"] = field.maxLength
    if field.pattern is not None:
        dc_generator_opts["regex"] = field.pattern
    if field.minimum is not None:
        dc_generator_opts["min"] = field.minimum
    if field.maximum is not None:
        dc_generator_opts["max"] = field.maximum

    if len(dc_generator_opts.keys()) > 0:
        dc_field["generator"] = {"options": dc_generator_opts}
    return dc_field


def _to_data_type(data_type):
    if data_type == "number" or data_type == "numeric" or data_type == "double":
        return "double"
    elif data_type == "decimal" or data_type == "bigint":
        return "decimal"
    elif data_type == "int":
        return "integer"
    elif data_type == "long":
        return "long"
    elif data_type == "float":
        return "float"
    elif data_type == "string" or data_type == "text" or data_type == "varchar":
        return "string"
    if data_type == "boolean":
        return "boolean"
    if data_type == "timestamp" or data_type == "timestamp_tz" or data_type == "timestamp_ntz":
        return "timestamp"
    elif data_type == "date":
        return "date"
    elif data_type == "array":
        return "array"
    elif data_type == "map" or data_type == "object" or data_type == "record" or data_type == "struct":
        return "struct"
    elif data_type == "bytes":
        return "binary"
    else:
        return "string"
