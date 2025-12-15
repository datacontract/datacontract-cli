from typing import List, Optional

import yaml
from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, SchemaProperty, Server

from datacontract.export.exporter import Exporter


class DataCatererExporter(Exporter):
    """
    Exporter class for Data Caterer.
    Creates a YAML file, based on the data contract, for Data Caterer to generate synthetic data.
    """

    def export(self, data_contract, schema_name, server, sql_server_type, export_args) -> dict:
        return to_data_caterer_generate_yaml(data_contract, server)


def _get_server_by_name(data_contract: OpenDataContractStandard, name: str) -> Optional[Server]:
    """Get a server by name."""
    if data_contract.servers is None:
        return None
    return next((s for s in data_contract.servers if s.server == name), None)


def _get_type(prop: SchemaProperty) -> Optional[str]:
    """Get the type from a schema property."""
    if prop.physicalType:
        return prop.physicalType
    if prop.logicalType:
        return prop.logicalType
    return None


def _get_logical_type_option(prop: SchemaProperty, key: str):
    """Get a logical type option value."""
    if prop.logicalTypeOptions is None:
        return None
    return prop.logicalTypeOptions.get(key)


def _get_custom_property_value(prop: SchemaProperty, key: str):
    """Get a custom property value."""
    if prop.customProperties is None:
        return None
    for cp in prop.customProperties:
        if cp.property == key:
            return cp.value
    return None


def _get_enum_values(prop: SchemaProperty):
    """Get enum values from logicalTypeOptions, customProperties, or quality rules."""
    import json
    # First check logicalTypeOptions
    enum_values = _get_logical_type_option(prop, "enum")
    if enum_values:
        return enum_values
    # Then check customProperties
    enum_str = _get_custom_property_value(prop, "enum")
    if enum_str:
        try:
            if isinstance(enum_str, list):
                return enum_str
            return json.loads(enum_str)
        except (json.JSONDecodeError, TypeError):
            pass
    # Finally check quality rules for invalidValues with validValues
    if prop.quality:
        for q in prop.quality:
            if q.metric == "invalidValues" and q.arguments:
                valid_values = q.arguments.get("validValues")
                if valid_values:
                    return valid_values
    return None


def to_data_caterer_generate_yaml(data_contract: OpenDataContractStandard, server):
    generation_task = {"name": data_contract.name, "steps": []}
    server_info = _get_server_info(data_contract, server)

    if data_contract.schema_:
        for schema_obj in data_contract.schema_:
            step = _to_data_caterer_generate_step(schema_obj.name, schema_obj, server_info)
            generation_task["steps"].append(step)
    return yaml.dump(generation_task, indent=2, sort_keys=False, allow_unicode=True)


def _get_server_info(data_contract: OpenDataContractStandard, server) -> Optional[Server]:
    if server is not None:
        found_server = _get_server_by_name(data_contract, server)
        if found_server:
            return found_server
        raise Exception(f"Server name not found in servers list in data contract, server-name={server}")
    elif data_contract.servers and len(data_contract.servers) > 0:
        return data_contract.servers[0]
    else:
        return None


def _to_data_caterer_generate_step(model_key: str, schema_obj: SchemaObject, server: Optional[Server]) -> dict:
    step = {
        "name": model_key,
        "type": _to_step_type(server),
        "options": _to_data_source_options(model_key, server),
        "fields": [],
    }
    fields = _to_fields(schema_obj.properties or [])
    if fields:
        step["fields"] = fields
    return step


def _to_step_type(server: Optional[Server]):
    if server is not None and server.type is not None:
        if server.type in ["s3", "gcs", "azure", "local"]:
            return server.format
        else:
            return server.type
    else:
        return "csv"


def _to_data_source_options(model_key: str, server: Optional[Server]):
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


def _to_fields(properties: List[SchemaProperty]) -> list:
    dc_fields = []
    for prop in properties:
        column = _to_field(prop.name, prop)
        dc_fields.append(column)
    return dc_fields


def _to_field(field_name: str, prop: SchemaProperty) -> dict:
    dc_field = {"name": field_name}
    dc_generator_opts = {}

    prop_type = _get_type(prop)
    if prop_type is not None:
        new_type = _to_data_type(prop_type)
        dc_field["type"] = new_type
        if new_type in ["object", "record", "struct"]:
            # need to get nested field definitions
            nested_fields = _to_fields(prop.properties or [])
            dc_field["fields"] = nested_fields
        elif new_type == "array":
            if prop.items is not None:
                item_type = _get_type(prop.items)
                if item_type is not None:
                    dc_generator_opts["arrayType"] = _to_data_type(item_type)
                else:
                    dc_generator_opts["arrayType"] = "string"
            else:
                dc_generator_opts["arrayType"] = "string"

    enum_values = _get_enum_values(prop)
    if enum_values is not None and len(enum_values) > 0:
        dc_generator_opts["oneOf"] = enum_values
    if prop.unique is not None and prop.unique:
        dc_generator_opts["isUnique"] = prop.unique
    if prop.primaryKey is not None and prop.primaryKey:
        dc_generator_opts["isPrimaryKey"] = prop.primaryKey

    min_length = _get_logical_type_option(prop, "minLength")
    max_length = _get_logical_type_option(prop, "maxLength")
    pattern = _get_logical_type_option(prop, "pattern")
    minimum = _get_logical_type_option(prop, "minimum")
    maximum = _get_logical_type_option(prop, "maximum")

    if min_length is not None:
        if prop_type is not None and prop_type.lower() == "array":
            dc_generator_opts["arrayMinLen"] = min_length
        else:
            dc_generator_opts["minLen"] = min_length
    if max_length is not None:
        if prop_type is not None and prop_type.lower() == "array":
            dc_generator_opts["arrayMaxLen"] = max_length
        else:
            dc_generator_opts["maxLen"] = max_length
    if pattern is not None:
        dc_generator_opts["regex"] = pattern
    if minimum is not None:
        dc_generator_opts["min"] = minimum
    if maximum is not None:
        dc_generator_opts["max"] = maximum

    if len(dc_generator_opts.keys()) > 0:
        dc_field["options"] = dc_generator_opts
    return dc_field


def _to_data_type(data_type):
    data_type_lower = data_type.lower() if data_type else ""
    if data_type_lower in ["number", "numeric", "double"]:
        return "double"
    elif data_type_lower in ["decimal", "bigint"]:
        return "decimal"
    elif data_type_lower in ["int", "integer"]:
        return "integer"
    elif data_type_lower == "long":
        return "long"
    elif data_type_lower == "float":
        return "float"
    elif data_type_lower in ["string", "text", "varchar"]:
        return "string"
    elif data_type_lower == "boolean":
        return "boolean"
    elif data_type_lower in ["timestamp", "timestamp_tz", "timestamp_ntz"]:
        return "timestamp"
    elif data_type_lower == "date":
        return "date"
    elif data_type_lower == "array":
        return "array"
    elif data_type_lower in ["map", "object", "record", "struct"]:
        return "struct"
    elif data_type_lower == "bytes":
        return "binary"
    else:
        return "string"
