import json
import logging
import math
from typing import Any, Dict, List

import fastjsonschema
from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, SchemaProperty

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
    resolver = SchemaResolver(load_and_validate_json_schema(source))
    json_schema = resolver.resolve(resolver.root)
    resolver.warn()

    title = json_schema.get("title", "default_model")
    odcs = create_odcs(name=title)
    odcs.schema_ = [to_schema_object(json_schema, title, json_schema.get("description"), business_name=title)]
    return odcs


def to_schema_object(json_schema: dict, name: str, description: str = None, business_name: str = None) -> SchemaObject:
    """The ODCS schema of a resolved JSON Schema object, warning about what ODCS cannot express."""
    properties = jsonschema_to_properties(json_schema.get("properties", {}), json_schema.get("required", []))
    schema_obj = create_schema_object(
        name=name,
        physical_type=json_schema.get("type", "object"),
        description=description,
        business_name=business_name,
        properties=properties,
    )
    ignored = list(_ignored_keywords(json_schema, ""))
    if ignored:
        listed = ", ".join(f"{keyword} ({path or 'root'})" for keyword, path in ignored)
        logger.warning(f"ODCS cannot express these keywords, which are not imported: {listed}")
    unions = [path for prop in properties for path in _union_paths(prop, prop.name)]
    if unions:
        listed = ", ".join(unions) if len(unions) <= 6 else ", ".join(unions[:5]) + f" and {len(unions) - 5} others"
        logger.warning(f"ODCS has no union type, so these properties are imported as string: {listed}")
    return schema_obj


class SchemaResolver:
    """Resolves the local $refs of a JSON Schema and merges its allOf branches, so properties can be read directly."""

    def __init__(self, root: dict):
        self.root = root
        self.recursive: list[str] = []
        self.unresolved: list[str] = []

    def resolve(self, node, refs: tuple = ()):
        if not isinstance(node, dict):
            return node
        if isinstance(node.get("$ref"), str):
            ref = node["$ref"]
            siblings = {key: value for key, value in node.items() if key != "$ref"}
            if not ref.startswith("#"):
                # another document, which is not loaded; the reference stays, and names the type in a union
                if ref not in self.unresolved:
                    self.unresolved.append(ref)
                return {"$ref": ref, **self.resolve(siblings, refs)}
            if ref in refs:
                # A definition that contains itself stops at its first repetition
                if ref not in self.recursive:
                    self.recursive.append(ref)
                return {"type": "object", **siblings}
            target = self.lookup(ref)
            if target is None:
                if ref not in self.unresolved:
                    self.unresolved.append(ref)
                return {"$ref": ref, **self.resolve(siblings, refs)}
            # keywords next to $ref apply as well, and win
            return {**self.resolve(target, refs + (ref,)), **self.resolve(siblings, refs)}

        resolved = {}
        for key, value in node.items():
            if key in ("properties", "patternProperties", "$defs", "definitions"):
                resolved[key] = (
                    {name: self.resolve(child, refs) for name, child in value.items()}
                    if isinstance(value, dict)
                    else value
                )
            elif key in ("items", "additionalProperties", "not", "if", "then", "else", "contains"):
                resolved[key] = (
                    [self.resolve(v, refs) for v in value] if isinstance(value, list) else self.resolve(value, refs)
                )
            elif key in ("anyOf", "oneOf", "allOf") and isinstance(value, list):
                resolved[key] = [self.resolve(branch, refs) for branch in value]
            else:
                resolved[key] = value
        if isinstance(resolved.get("allOf"), list):
            resolved = merge_all_of(resolved)
        return resolved

    def lookup(self, ref: str):
        """The node a JSON pointer such as #/$defs/Address points to, or None."""
        node = self.root
        for part in ref.lstrip("#").strip("/").split("/") if ref not in ("#", "#/") else []:
            part = part.replace("~1", "/").replace("~0", "~")
            if isinstance(node, dict) and part in node:
                node = node[part]
            elif isinstance(node, list) and part.isdigit() and int(part) < len(node):
                node = node[int(part)]
            else:
                return None
        return node

    def warn(self):
        if self.recursive:
            logger.warning(
                f"These definitions contain themselves, so the repetition is an object without properties: "
                f"{', '.join(self.recursive)}"
            )
        if self.unresolved:
            logger.warning(
                f"These $refs could not be resolved and are imported as strings: {', '.join(self.unresolved)}"
            )


def merge_all_of(node: dict) -> dict:
    """The schema with its allOf branches merged in: properties and required combine, other keywords are kept
    from the schema itself, then from the first branch that has them."""
    branches = [b for b in node["allOf"] if isinstance(b, dict)]
    merged = {key: value for key, value in node.items() if key != "allOf"}
    for branch in branches:
        if isinstance(branch.get("allOf"), list):
            branch = merge_all_of(branch)
        for key, value in branch.items():
            if key == "properties":
                # in the order they come, base branches first; what comes first wins
                known = merged.get("properties", {})
                merged["properties"] = {**known, **{name: v for name, v in value.items() if name not in known}}
            elif key == "required":
                merged["required"] = list(dict.fromkeys(merged.get("required", []) + value))
            else:
                merged.setdefault(key, value)
    if "properties" in merged and "type" not in merged:
        merged["type"] = "object"
    return merged


# Keywords that constrain a value in a way ODCS cannot express
IGNORED_KEYWORDS = (
    "patternProperties", "if", "not", "contains", "propertyNames", "minProperties", "maxProperties",
    "dependentRequired", "dependentSchemas", "dependencies",
)  # fmt: skip


def _ignored_keywords(schema, path: str):
    """The keywords the import leaves out, with the path of the property that has them."""
    if not isinstance(schema, dict):
        return
    for keyword in IGNORED_KEYWORDS:
        if keyword in schema:
            yield keyword, path
    properties = schema.get("properties") if isinstance(schema.get("properties"), dict) else {}
    if properties and isinstance(schema.get("additionalProperties"), dict):
        # a map with properties of its own
        yield "additionalProperties", path
    for name, child in properties.items():
        yield from _ignored_keywords(child, f"{path}.{name}" if path else name)
    items = schema.get("items")
    for item in items if isinstance(items, list) else [items]:
        yield from _ignored_keywords(item, f"{path}[]")
    for key in ("anyOf", "oneOf"):
        for branch in schema.get(key) or []:
            yield from _ignored_keywords(branch, path)


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
        if prop_schema is False:
            # a property that no value satisfies, i.e. one that must be absent
            continue
        is_required = prop_name in required_properties
        prop = schema_to_property(prop_name, prop_schema, is_required)
        properties.append(prop)

    return properties


def schema_to_property(name: str, prop_schema: Dict[str, Any], is_required: bool = None) -> SchemaProperty:
    """Convert a JSON Schema property to an ODCS SchemaProperty."""
    if prop_schema is True:
        # the boolean schema true admits every value, like {}
        prop_schema = {}
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
    if "const" in prop_schema and "enum" not in prop_schema:
        # const allows one value, typed like it
        prop_schema = {
            "type": _JSON_VALUE_TYPES[type(prop_schema["const"])],
            **prop_schema,
            "enum": [prop_schema["const"]],
        }

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
    # An infinite bound, such as 1e400, bounds nothing
    minimum = finite(prop_schema.get("minimum"))
    maximum = finite(prop_schema.get("maximum"))
    format_val = prop_schema.get("format")

    # Handle exclusiveMinimum/exclusiveMaximum (draft-04: boolean, draft-06+: number)
    exclusive_minimum = None
    exclusive_maximum = None
    raw_exclusive_min = finite(prop_schema.get("exclusiveMinimum"))
    raw_exclusive_max = finite(prop_schema.get("exclusiveMaximum"))

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

    # An object with additionalProperties but no properties of its own is a map
    additional = prop_schema.get("additionalProperties")
    is_map = property_type == "object" and not nested_properties and isinstance(additional, dict)

    prop = create_property(
        name=name,
        logical_type="map" if is_map else logical_type,
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
        examples=prop_schema.get("examples"),
        map_value=schema_to_property("value", additional) if is_map else None,
    )
    options = {}
    if property_type == "array":
        options = {key: prop_schema[key] for key in ("minItems", "maxItems") if key in prop_schema}
        if prop_schema.get("uniqueItems"):
            options["uniqueItems"] = True
    if logical_type in ("integer", "number") and "multipleOf" in prop_schema:
        options["multipleOf"] = prop_schema["multipleOf"]
    if options:
        prop.logicalTypeOptions = {**(prop.logicalTypeOptions or {}), **options}

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


def finite(value):
    """The value, or None for an infinite number."""
    return None if isinstance(value, float) and math.isinf(value) else value
