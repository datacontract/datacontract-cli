import json

import fastjsonschema

from datacontract.imports.importer import Importer
from datacontract.model.data_contract_specification import DataContractSpecification, Definition, Field, Model
from datacontract.model.exceptions import DataContractException


class JsonSchemaImporter(Importer):
    def import_source(
        self, data_contract_specification: DataContractSpecification, source: str, import_args: dict
    ) -> DataContractSpecification:
        return import_jsonschema(data_contract_specification, source)


def import_jsonschema(data_contract_specification: DataContractSpecification, source: str) -> DataContractSpecification:
    if data_contract_specification.models is None:
        data_contract_specification.models = {}

    json_schema = load_and_validate_json_schema(source)

    title = json_schema.get("title", "default_model")
    description = json_schema.get("description")
    type_ = json_schema.get("type")
    properties = json_schema.get("properties", {})
    required_properties = json_schema.get("required", [])

    fields_kwargs = jsonschema_to_args(properties, required_properties)
    fields = {name: Field(**kwargs) for name, kwargs in fields_kwargs.items()}

    model = Model(description=description, type=type_, title=title, fields=fields)
    data_contract_specification.models[title] = model

    definitions = json_schema.get("definitions", {})
    for name, schema in definitions.items():
        kwargs = schema_to_args(schema)
        data_contract_specification.definitions[name] = Definition(name=name, **kwargs)

    return data_contract_specification


def load_and_validate_json_schema(source):
    try:
        with open(source, "r") as file:
            json_schema = json.loads(file.read())

        validator = fastjsonschema.compile({})
        validator(json_schema)

    except fastjsonschema.JsonSchemaException as e:
        raise DataContractException(
            type="schema",
            name="Parse json schema",
            reason=f"Failed to validate json schema from {source}: {e}",
            engine="datacontract",
        )

    except Exception as e:
        raise DataContractException(
            type="schema",
            name="Parse json schema",
            reason=f"Failed to parse json schema from {source}",
            engine="datacontract",
            original_exception=e,
        )
    return json_schema


def jsonschema_to_args(properties, required_properties):
    args = {}
    for property, property_schema in properties.items():
        is_required = property in required_properties
        args[property] = schema_to_args(property_schema, is_required)

    return args


def schema_to_args(property_schema, is_required: bool = None) -> dict:
    direct_mappings = {
        "title",
        "description",
        "format",
        "pattern",
        "enum",
        "tags",
        "pii",
        "minLength",
        "maxLength",
        "minimum",
        "exclusiveMinimum",
        "maximum",
        "exclusiveMaximum",
    }

    field_kwargs = {key: value for key, value in property_schema.items() if key in direct_mappings}

    if is_required is not None:
        field_kwargs["required"] = is_required

    property_type = determine_type(property_schema)
    if property_type is not None:
        field_kwargs["type"] = property_type

    if property_type == "array":
        nested_item_type, nested_items = determine_nested_item_type(property_schema)

        if nested_items is not None:
            field_kwargs["items"] = schema_to_args(nested_item_type)

    nested_properties = property_schema.get("properties")
    if nested_properties is not None:
        # recursive call for complex nested properties
        required = property_schema.get("required", [])
        field_kwargs["fields"] = jsonschema_to_args(nested_properties, required)

    return field_kwargs


def determine_nested_item_type(property_schema):
    nested_items = property_schema.get("items")
    nested_items_is_list = isinstance(nested_items, list)
    if nested_items_is_list and len(nested_items) != 1:
        raise DataContractException(
            type="schema",
            name="Parse json schema",
            reason=f"Union types for arrays are currently not supported ({nested_items})",
            engine="datacontract",
        )
    if nested_items_is_list and len(nested_items) == 1:
        nested_item_type = nested_items[0]
    elif not nested_items_is_list and nested_items is not None:
        nested_item_type = nested_items
    return nested_item_type, nested_items


def determine_type(property_schema):
    property_type = property_schema.get("type")
    type_is_list = isinstance(property_type, list)
    if type_is_list:
        non_null_types = [t for t in property_type if t != "null"]
        if non_null_types:
            property_type = non_null_types[0]
        else:
            property_type = None
    return property_type
