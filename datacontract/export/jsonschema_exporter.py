import json
from typing import List, Optional

from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, SchemaProperty

from datacontract.export.exporter import Exporter, _check_schema_name_for_export


class JsonSchemaExporter(Exporter):
    def export(self, data_contract, schema_name, server, sql_server_type, export_args) -> dict:
        model_name, model_value = _check_schema_name_for_export(data_contract, schema_name, self.export_format)
        return to_jsonschema_json(model_name, model_value)


def to_jsonschemas(data_contract: OpenDataContractStandard) -> dict:
    jsonschemas = {}
    if data_contract.schema_:
        for schema_obj in data_contract.schema_:
            jsonschema = to_jsonschema(schema_obj.name, schema_obj)
            jsonschemas[schema_obj.name] = jsonschema
    return jsonschemas


def to_jsonschema_json(model_key: str, model_value: SchemaObject) -> str:
    jsonschema = to_jsonschema(model_key, model_value)
    return json.dumps(jsonschema, indent=2)


def to_properties(properties: List[SchemaProperty]) -> dict:
    result = {}
    for prop in properties:
        result[prop.name] = to_property(prop)
    return result


def _get_logical_type_option(prop: SchemaProperty, key: str):
    """Get a logical type option value."""
    if prop.logicalTypeOptions is None:
        return None
    return prop.logicalTypeOptions.get(key)


def _get_config_value(prop: SchemaProperty, key: str):
    """Get a custom property value."""
    if prop.customProperties is None:
        return None
    for cp in prop.customProperties:
        if cp.property == key:
            return cp.value
    return None


def _get_enum_from_quality(prop: SchemaProperty):
    """Get enum values from quality rules (invalidValues metric with validValues)."""
    if prop.quality is None:
        return None
    for q in prop.quality:
        if q.metric == "invalidValues" and q.arguments:
            valid_values = q.arguments.get("validValues")
            if valid_values:
                return valid_values
    return None


def to_property(prop: SchemaProperty) -> dict:
    property_dict = {}
    field_type = prop.logicalType
    json_type, json_format = convert_type_format(field_type, _get_logical_type_option(prop, "format"))

    if json_type is not None:
        if not prop.required:
            """
            From: https://json-schema.org/understanding-json-schema/reference/type
            The type keyword may either be a string or an array:

            If it's a string, it is the name of one of the basic types above.
            If it is an array, it must be an array of strings, where each string
            is the name of one of the basic types, and each element is unique.
            In this case, the JSON snippet is valid if it matches any of the given types.
            """
            property_dict["type"] = [json_type, "null"]
        else:
            property_dict["type"] = json_type

    if json_format is not None:
        property_dict["format"] = json_format

    if prop.primaryKey:
        property_dict["primaryKey"] = prop.primaryKey

    if prop.unique:
        property_dict["unique"] = True

    if json_type == "object":
        nested_props = prop.properties or []
        # TODO: any better idea to distinguish between properties and patternProperties?
        if nested_props and nested_props[0].name.startswith("^"):
            property_dict["patternProperties"] = to_properties(nested_props)
        else:
            property_dict["properties"] = to_properties(nested_props)
        property_dict["required"] = to_required(nested_props)

    if json_type == "array" and prop.items:
        property_dict["items"] = to_property(prop.items)

    pattern = _get_logical_type_option(prop, "pattern")
    if pattern:
        property_dict["pattern"] = pattern

    # Check logicalTypeOptions, customProperties, or quality rules for enum
    enum_values = _get_logical_type_option(prop, "enum")
    if not enum_values:
        enum_from_custom = _get_config_value(prop, "enum")
        if enum_from_custom:
            # Parse JSON string from customProperties
            try:
                enum_values = json.loads(enum_from_custom)
            except (json.JSONDecodeError, TypeError):
                enum_values = None
    if not enum_values:
        # Check quality rules for invalidValues metric with validValues
        enum_values = _get_enum_from_quality(prop)
    if enum_values:
        property_dict["enum"] = enum_values

    min_length = _get_logical_type_option(prop, "minLength")
    if min_length is not None:
        property_dict["minLength"] = min_length

    max_length = _get_logical_type_option(prop, "maxLength")
    if max_length is not None:
        property_dict["maxLength"] = max_length

    if prop.businessName:
        property_dict["title"] = prop.businessName

    if prop.description:
        property_dict["description"] = prop.description

    exclusive_minimum = _get_logical_type_option(prop, "exclusiveMinimum")
    if exclusive_minimum is not None:
        property_dict["exclusiveMinimum"] = exclusive_minimum

    exclusive_maximum = _get_logical_type_option(prop, "exclusiveMaximum")
    if exclusive_maximum is not None:
        property_dict["exclusiveMaximum"] = exclusive_maximum

    minimum = _get_logical_type_option(prop, "minimum")
    if minimum is not None:
        property_dict["minimum"] = minimum

    maximum = _get_logical_type_option(prop, "maximum")
    if maximum is not None:
        property_dict["maximum"] = maximum

    if prop.tags:
        property_dict["tags"] = prop.tags

    pii = _get_config_value(prop, "pii")
    if pii:
        property_dict["pii"] = pii

    if prop.classification is not None:
        property_dict["classification"] = prop.classification

    # TODO: all constraints
    return property_dict


def to_required(properties: List[SchemaProperty]) -> list:
    required = []
    for prop in properties:
        if prop.required is True:
            required.append(prop.name)
    return required


def convert_type_format(type_str: Optional[str], format_str: Optional[str]) -> tuple:
    if type_str is None:
        return None, None
    if type_str.lower() in ["string", "varchar", "text"]:
        return "string", format_str
    if type_str.lower() in ["timestamp", "timestamp_tz", "date-time", "datetime"]:
        return "string", "date-time"
    if type_str.lower() in ["timestamp_ntz"]:
        return "string", None
    if type_str.lower() in ["date"]:
        return "string", "date"
    if type_str.lower() in ["time"]:
        return "string", "time"
    if type_str.lower() in ["number", "decimal", "numeric", "float", "double"]:
        return "number", None
    if type_str.lower() in ["integer", "int", "long", "bigint"]:
        return "integer", None
    if type_str.lower() in ["boolean"]:
        return "boolean", None
    if type_str.lower() in ["object", "record", "struct"]:
        return "object", None
    if type_str.lower() in ["array"]:
        return "array", None
    return None, None


def convert_format(format_str: Optional[str]) -> Optional[str]:
    if format_str is None:
        return None
    if format_str.lower() in ["uri"]:
        return "uri"
    if format_str.lower() in ["email"]:
        return "email"
    if format_str.lower() in ["uuid"]:
        return "uuid"
    if format_str.lower() in ["boolean"]:
        return "boolean"
    return None


def to_jsonschema(model_key: str, model_value: SchemaObject) -> dict:
    properties = model_value.properties or []
    model = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": to_properties(properties),
        "required": to_required(properties),
    }
    if model_value.businessName:
        model["title"] = model_value.businessName
    if model_value.description:
        model["description"] = model_value.description

    return model
