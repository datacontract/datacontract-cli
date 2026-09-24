import json
import logging
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

logger = logging.getLogger(__name__)


class JsonSchemaImporter(Importer):
    def import_source(self, source: str, import_args: dict) -> OpenDataContractStandard:
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
        business_name=title,
        properties=properties,
    )

    odcs.schema_ = [schema_obj]
    unions = [path for prop in properties for path in _union_paths(prop, prop.name)]
    if unions:
        listed = ", ".join(unions) if len(unions) <= 6 else ", ".join(unions[:5]) + f" and {len(unions) - 5} others"
        logger.warning(f"ODCS has no union type, so these properties are imported as string: {listed}")

    return odcs


def _union_paths(prop: SchemaProperty, path: str):
    if "|" in (prop.physicalType or ""):
        yield f"{path} ({prop.physicalType})"
    for child in prop.properties or []:
        yield from _union_paths(child, f"{path}.{child.name}")
    if prop.items:
        yield from _union_paths(prop.items, f"{path}[]")


def load_and_validate_json_schema(source: str) -> dict:
    """Load and validate a JSON Schema file."""
    try:
        with open(source, "r", encoding="utf-8") as file:
            json_schema = json.loads(file.read())

        validator = fastjsonschema.compile({})
        validator(json_schema)

    except fastjsonschema.JsonSchemaException as e:
        raise DataContractException(
            type="schema",
            name="Parse json schema",
            reason=f"Failed to validate json schema from {source}: {e}",
            engine="datacontract-cli",
        )

    except Exception as e:
        raise DataContractException(
            type="schema",
            name="Parse json schema",
            reason=f"Failed to parse json schema from {source}",
            engine="datacontract-cli",
            original_exception=e,
        )
    return json_schema


def jsonschema_to_properties(json_properties: Dict[str, Any], required_properties: List[str]) -> List[SchemaProperty]:
    """Convert JSON Schema properties to ODCS SchemaProperty list."""
    properties = []

    for prop_name, prop_schema in json_properties.items():
        is_required = prop_name in required_properties
        prop = schema_to_property(prop_name, prop_schema, is_required)
        properties.append(prop)

    return properties


def schema_to_property(name: str, prop_schema: Dict[str, Any], is_required: bool = None) -> SchemaProperty:
    """Convert a JSON Schema property to an ODCS SchemaProperty."""
    key = "anyOf" if "anyOf" in prop_schema else "oneOf"
    if key in prop_schema:
        # A true branch admits every value, a false one none
        prop_schema = {**prop_schema, key: [{} if b is True else b for b in prop_schema[key] if b is not False]}
    branches = prop_schema.get(key) or []
    non_null_branches = [branch for branch in branches if branch.get("type") != "null"]
    if len(non_null_branches) == 1:
        # One type or null is a nullable property, not a union
        outer = {key: value for key, value in prop_schema.items() if key not in ("anyOf", "oneOf")}
        prop_schema = {**non_null_branches[0], **outer}

    # Determine the type
    property_type = determine_type(prop_schema)
    # ODCS has no union type
    logical_type = "string" if "|" in property_type else map_jsonschema_type_to_odcs(property_type)

    # Extract common attributes
    title = prop_schema.get("title")
    description = prop_schema.get("description")
    pattern = prop_schema.get("pattern")
    min_length = prop_schema.get("minLength")
    max_length = prop_schema.get("maxLength")
    minimum = prop_schema.get("minimum")
    maximum = prop_schema.get("maximum")
    format_val = prop_schema.get("format")

    # Handle exclusiveMinimum/exclusiveMaximum (draft-04: boolean, draft-06+: number)
    exclusive_minimum = None
    exclusive_maximum = None
    raw_exclusive_min = prop_schema.get("exclusiveMinimum")
    raw_exclusive_max = prop_schema.get("exclusiveMaximum")

    if isinstance(raw_exclusive_min, bool):
        # Draft-04: boolean, use minimum value as exclusive
        if raw_exclusive_min and minimum is not None:
            exclusive_minimum = minimum
            minimum = None
    elif raw_exclusive_min is not None:
        # Draft-06+: number value
        exclusive_minimum = raw_exclusive_min

    if isinstance(raw_exclusive_max, bool):
        # Draft-04: boolean, use maximum value as exclusive
        if raw_exclusive_max and maximum is not None:
            exclusive_maximum = maximum
            maximum = None
    elif raw_exclusive_max is not None:
        # Draft-06+: number value
        exclusive_maximum = raw_exclusive_max

    quality_rules = []

    # Build custom properties for attributes not directly mapped
    custom_props = {}
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
                        engine="datacontract-cli",
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
        exclusive_minimum=exclusive_minimum,
        exclusive_maximum=exclusive_maximum,
        format=format_val,
        properties=nested_properties,
        items=items_prop,
        custom_properties=custom_props if custom_props else None,
        enum=prop_schema.get("enum"),
    )

    # Set title as businessName if present
    if title:
        prop.businessName = title

    # Attach quality rules to property
    if quality_rules:
        prop.quality = quality_rules

    return prop


def determine_type(prop_schema: Dict[str, Any]) -> str:
    """Determine the type from a JSON Schema property; a union is rendered as ``string|integer``."""
    branches = prop_schema.get("anyOf") or prop_schema.get("oneOf")
    if not branches:
        types = [prop_schema.get("type") or "string"]
    elif any("type" not in b and "$ref" not in b and "const" not in b and "enum" not in b for b in branches):
        # a branch without any type constraint admits every value
        return "string"
    else:
        types = [
            b.get("type")
            or b.get("$ref", "").rsplit("/", 1)[-1]
            or [_JSON_VALUE_TYPES[type(v)] for v in ([b["const"]] if "const" in b else b["enum"])]
            for b in branches
        ]
    flat = [t for listed in types for t in (listed if isinstance(listed, list) else [listed])]
    names = [t for t in flat if t != "null"]
    # two object or array shapes are a union even though their type names match
    if len(dict.fromkeys(names)) == 1 and names[0] in ("object", "array") and len(names) > 1:
        return "|".join(names)
    return "|".join(dict.fromkeys(names)) or "string"


_JSON_VALUE_TYPES = {
    str: "string",
    bool: "boolean",
    int: "integer",
    float: "number",
    dict: "object",
    list: "array",
    type(None): "null",
}


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
