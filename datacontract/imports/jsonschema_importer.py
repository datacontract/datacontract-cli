import json
from typing import Any, Dict, List

import fastjsonschema

from open_data_contract_standard.model import OpenDataContractStandard, SchemaProperty

from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import (
    create_odcs,
    create_property,
    create_schema_object,
)
from datacontract.model.exceptions import DataContractException


class JsonSchemaImporter(Importer):
    def import_source(
        self, source: str, import_args: dict
    ) -> OpenDataContractStandard:
        return import_jsonschema(source)


def import_jsonschema(source: str) -> OpenDataContractStandard:
    """Import a JSON Schema and create an ODCS data contract."""
    json_schema = load_and_validate_json_schema(source)

    title = json_schema.get("title", "default_model")
    description = json_schema.get("description")
    type_ = json_schema.get("type", "object")
    json_properties = json_schema.get("properties", {})
    required_properties = json_schema.get("required", [])

    odcs = create_odcs(name=title)

    properties = jsonschema_to_properties(json_properties, required_properties)

    schema_obj = create_schema_object(
        name=title,
        physical_type=type_,
        description=description,
        properties=properties,
    )

    odcs.schema_ = [schema_obj]

    return odcs


def load_and_validate_json_schema(source: str) -> dict:
    """Load and validate a JSON Schema file."""
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


def jsonschema_to_properties(
    json_properties: Dict[str, Any], required_properties: List[str]
) -> List[SchemaProperty]:
    """Convert JSON Schema properties to ODCS SchemaProperty list."""
    properties = []

    for prop_name, prop_schema in json_properties.items():
        is_required = prop_name in required_properties
        prop = schema_to_property(prop_name, prop_schema, is_required)
        properties.append(prop)

    return properties


def schema_to_property(
    name: str, prop_schema: Dict[str, Any], is_required: bool = None
) -> SchemaProperty:
    """Convert a JSON Schema property to an ODCS SchemaProperty."""
    # Determine the type
    property_type = determine_type(prop_schema)
    logical_type = map_jsonschema_type_to_odcs(property_type)

    # Extract common attributes
    title = prop_schema.get("title")
    description = prop_schema.get("description")
    pattern = prop_schema.get("pattern")
    min_length = prop_schema.get("minLength")
    max_length = prop_schema.get("maxLength")
    minimum = prop_schema.get("minimum")
    maximum = prop_schema.get("maximum")
    exclusive_minimum = prop_schema.get("exclusiveMinimum")
    exclusive_maximum = prop_schema.get("exclusiveMaximum")
    enum = prop_schema.get("enum")
    format_val = prop_schema.get("format")

    # Build custom properties for attributes not directly mapped
    custom_props = {}
    if format_val:
        custom_props["format"] = format_val
    if prop_schema.get("pii"):
        custom_props["pii"] = prop_schema.get("pii")

    # Handle nested properties for objects
    nested_properties = None
    if property_type == "object":
        nested_json_props = prop_schema.get("properties")
        if nested_json_props:
            nested_required = prop_schema.get("required", [])
            nested_properties = jsonschema_to_properties(nested_json_props, nested_required)

    # Handle array items
    items_prop = None
    if property_type == "array":
        nested_items = prop_schema.get("items")
        if nested_items:
            if isinstance(nested_items, list):
                if len(nested_items) == 1:
                    items_prop = schema_to_property("items", nested_items[0])
                elif len(nested_items) > 1:
                    raise DataContractException(
                        type="schema",
                        name="Parse json schema",
                        reason=f"Union types for arrays are currently not supported ({nested_items})",
                        engine="datacontract",
                    )
            else:
                items_prop = schema_to_property("items", nested_items)

    prop = create_property(
        name=name,
        logical_type=logical_type,
        physical_type=property_type,
        description=description,
        required=is_required if is_required else None,
        pattern=pattern,
        min_length=min_length,
        max_length=max_length,
        minimum=minimum,
        maximum=maximum,
        properties=nested_properties,
        items=items_prop,
        custom_properties=custom_props if custom_props else None,
    )

    # Set title as businessName if present
    if title:
        prop.businessName = title

    return prop


def determine_type(prop_schema: Dict[str, Any]) -> str:
    """Determine the type from a JSON Schema property."""
    property_type = prop_schema.get("type")

    if isinstance(property_type, list):
        # Handle union types like ["string", "null"]
        non_null_types = [t for t in property_type if t != "null"]
        if non_null_types:
            property_type = non_null_types[0]
        else:
            property_type = "string"

    return property_type or "string"


def map_jsonschema_type_to_odcs(json_type: str) -> str:
    """Map JSON Schema type to ODCS logical type."""
    type_mapping = {
        "string": "string",
        "integer": "integer",
        "number": "number",
        "boolean": "boolean",
        "array": "array",
        "object": "object",
        "null": "string",
    }
    return type_mapping.get(json_type, "string")
