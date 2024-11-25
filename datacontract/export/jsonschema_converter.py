import json
from typing import Dict

from datacontract.export.exporter import Exporter, _check_models_for_export
from datacontract.model.data_contract_specification import DataContractSpecification, Field, Model


class JsonSchemaExporter(Exporter):
    def export(self, data_contract, model, server, sql_server_type, export_args) -> dict:
        model_name, model_value = _check_models_for_export(data_contract, model, self.export_format)
        return to_jsonschema_json(model_name, model_value)


def to_jsonschemas(data_contract_spec: DataContractSpecification):
    jsonschmemas = {}
    for model_key, model_value in data_contract_spec.models.items():
        jsonschema = to_jsonschema(model_key, model_value)
        jsonschmemas[model_key] = jsonschema
    return jsonschmemas


def to_jsonschema_json(model_key, model_value: Model) -> str:
    jsonschema = to_jsonschema(model_key, model_value)
    return json.dumps(jsonschema, indent=2)


def to_properties(fields: Dict[str, Field]) -> dict:
    properties = {}
    for field_name, field in fields.items():
        properties[field_name] = to_property(field)
    return properties


def to_property(field: Field) -> dict:
    property = {}
    json_type, json_format = convert_type_format(field.type, field.format)
    if json_type is not None:
        if not field.required:
            """
            From: https://json-schema.org/understanding-json-schema/reference/type
            The type keyword may either be a string or an array:

            If it's a string, it is the name of one of the basic types above.
            If it is an array, it must be an array of strings, where each string 
            is the name of one of the basic types, and each element is unique.
            In this case, the JSON snippet is valid if it matches any of the given types.
            """
            property["type"] = [json_type, "null"]
        else:
            property["type"] = json_type
    if json_format is not None:
        property["format"] = json_format
    if field.primaryKey:
        property["primaryKey"] = field.primaryKey
    if field.unique:
        property["unique"] = True
    if json_type == "object":
        # TODO: any better idea to distinguish between properties and patternProperties?
        if field.fields.keys() and next(iter(field.fields.keys())).startswith("^"):
            property["patternProperties"] = to_properties(field.fields)
        else:
            property["properties"] = to_properties(field.fields)
        property["required"] = to_required(field.fields)
    if json_type == "array":
        property["items"] = to_property(field.items)
    if field.pattern:
        property["pattern"] = field.pattern
    if field.enum:
        property["enum"] = field.enum
    if field.minLength is not None:
        property["minLength"] = field.minLength
    if field.maxLength is not None:
        property["maxLength"] = field.maxLength
    if field.title:
        property["title"] = field.title
    if field.description:
        property["description"] = field.description
    if field.exclusiveMinimum is not None:
        property["exclusiveMinimum"] = field.exclusiveMinimum
    if field.exclusiveMaximum is not None:
        property["exclusiveMaximum"] = field.exclusiveMaximum
    if field.minimum is not None:
        property["minimum"] = field.minimum
    if field.maximum is not None:
        property["maximum"] = field.maximum
    if field.tags:
        property["tags"] = field.tags
    if field.pii:
        property["pii"] = field.pii
    if field.classification is not None:
        property["classification"] = field.classification

    # TODO: all constraints
    return property


def to_required(fields: Dict[str, Field]):
    required = []
    for field_name, field in fields.items():
        if field.required is True:
            required.append(field_name)
    return required


def convert_type_format(type, format) -> (str, str):
    if type is None:
        return None, None
    if type.lower() in ["string", "varchar", "text"]:
        return "string", format
    if type.lower() in ["timestamp", "timestamp_tz", "date-time", "datetime"]:
        return "string", "date-time"
    if type.lower() in ["timestamp_ntz"]:
        return "string", None
    if type.lower() in ["date"]:
        return "string", "date"
    if type.lower() in ["time"]:
        return "string", "time"
    if type.lower() in ["number", "decimal", "numeric", "float", "double"]:
        return "number", None
    if type.lower() in ["integer", "int", "long", "bigint"]:
        return "integer", None
    if type.lower() in ["boolean"]:
        return "boolean", None
    if type.lower() in ["object", "record", "struct"]:
        return "object", None
    if type.lower() in ["array"]:
        return "array", None
    return None, None


def convert_format(self, format):
    if format is None:
        return None
    if format.lower() in ["uri"]:
        return "uri"
    if format.lower() in ["email"]:
        return "email"
    if format.lower() in ["uuid"]:
        return "uuid"
    if format.lower() in ["boolean"]:
        return "boolean"
    return None


def to_jsonschema(model_key, model_value: Model) -> dict:
    model = {
        "$schema": "http://json-schema.org/draft-07/schema#",
        "type": "object",
        "properties": to_properties(model_value.fields),
        "required": to_required(model_value.fields),
    }
    if model_value.title:
        model["title"] = model_value.title
    if model_value.description:
        model["description"] = model_value.description

    return model
