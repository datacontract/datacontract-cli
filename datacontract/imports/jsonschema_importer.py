import json

import fastjsonschema

from datacontract.imports.importer import Importer
from datacontract.model.data_contract_specification import DataContractSpecification, Model, Field, Definition
from datacontract.model.exceptions import DataContractException


class JsonSchemaImporter(Importer):
    def import_source(
        self, data_contract_specification: DataContractSpecification, source: str, import_args: dict
    ) -> DataContractSpecification:
        return import_jsonschema(data_contract_specification, source)


def import_jsonschema(data_contract_specification: DataContractSpecification, source: str) -> DataContractSpecification:
    if data_contract_specification.models is None:
        data_contract_specification.models = {}

    try:
        with open(source, "r") as file:
            json_schema = json.loads(file.read())

        validator = fastjsonschema.compile({})
        validator(json_schema)

        description = json_schema.get("description")
        type_ = json_schema.get("type")
        title = json_schema.get("title", "default_model")
        properties = json_schema.get("properties", {})
        required_properties = json_schema.get("required", [])

        field_kwargs = {}
        for property_name, property_schema in properties.items():
            is_required = property_name in required_properties
            field_kwargs[property_name] = dict_to_field_args(property_schema, is_required)

        data_contract_specification.models[title] = Model(
            description=description,
            type=type_,
            title=title,
            fields={field_name: Field(**kwargs) for field_name, kwargs in field_kwargs.items()},
        )

        definitions = json_schema.get("definitions", {})

        for definition_name, definition_schema in definitions.items():
            kwargs = dict_to_field_args(definition_schema)
            data_contract_specification.definitions[definition_name] = Definition(name=definition_name, **kwargs)

    except fastjsonschema.JsonSchemaException as e:
        raise DataContractException(
            type="schema",
            name="Parse json schema",
            reason=f"Failed to parse json schema from {source}: {e}",
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

    return data_contract_specification


def jsonschema_to_args(properties, required_properties):
    fields = {}
    for property, property_schema in properties.items():
        is_required = property in required_properties
        field = dict_to_field_args(property_schema, is_required)
        fields[property] = field

    return fields


def dict_to_field_args(property_schema, is_required: bool = None) -> dict:
    field_kwargs = {}

    property_type = determine_type(property_schema)
    if property_type is not None:
        field_kwargs["type"] = property_type

    if is_required is not None:
        field_kwargs["required"] = is_required

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

    directly_mapped_properties = {key: value for key, value in property_schema.items() if key in direct_mappings}

    field_kwargs = field_kwargs | directly_mapped_properties

    nested_properties = property_schema.get("properties")
    if nested_properties is not None:
        field_kwargs["fields"] = jsonschema_to_args(nested_properties, property_schema["required"])

    if property_type == "array":
        nested_item_type, nested_items = determine_nested_item_type(property_schema)

        if nested_items is not None:
            field_kwargs["items"] = dict_to_field_args(nested_item_type)

    return field_kwargs


def determine_nested_item_type(property_schema):
    nested_items = property_schema.get("items")
    nested_items_is_list = isinstance(nested_items, list)
    if nested_items_is_list and len(nested_items) != 1:
        raise DataContractException(
            type="schema",
            name="Parse json schema",
            reason=f"Union types are currently not supported ({nested_items})",
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
