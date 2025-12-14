import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from open_data_contract_standard.model import OpenDataContractStandard, SchemaProperty

from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import (
    create_odcs,
    create_property,
    create_schema_object,
    create_server,
)


class JsonImporter(Importer):
    def import_source(
        self, source: str, import_args: dict
    ) -> OpenDataContractStandard:
        return import_json(source)


def is_ndjson(file_path: str) -> bool:
    """Check if a file contains newline-delimited JSON."""
    with open(file_path, "r", encoding="utf-8") as file:
        for _ in range(5):
            line = file.readline().strip()
            if not line:
                continue
            try:
                json.loads(line)
                return True
            except json.JSONDecodeError:
                break
    return False


def import_json(source: str, include_examples: bool = False) -> OpenDataContractStandard:
    """Import a JSON file and create an ODCS data contract."""
    base_model_name = os.path.splitext(os.path.basename(source))[0]

    # Check if file is newline-delimited JSON
    if is_ndjson(source):
        json_data = []
        with open(source, "r", encoding="utf-8") as file:
            for line in file:
                line = line.strip()
                if line:
                    try:
                        json_data.append(json.loads(line))
                    except json.JSONDecodeError:
                        continue
    else:
        with open(source, "r", encoding="utf-8") as file:
            json_data = json.load(file)

    odcs = create_odcs()
    odcs.servers = [create_server(name="production", server_type="local", path=source, format="json")]

    if isinstance(json_data, list) and json_data:
        if all(isinstance(item, dict) for item in json_data[:5]):
            # Array of objects, as table
            properties = []
            field_defs = {}
            for item in json_data[:20]:
                for key, value in item.items():
                    field_def = generate_field_definition(value, key)
                    if key in field_defs:
                        field_defs[key] = merge_field_definitions(field_defs[key], field_def)
                    else:
                        field_defs[key] = field_def

            properties = [dict_to_property(name, field_def) for name, field_def in field_defs.items()]

            schema_obj = create_schema_object(
                name=base_model_name,
                physical_type="table",
                description=f"Generated from JSON array in {source}",
                properties=properties,
            )
        else:
            # Simple array
            item_type, item_format = infer_array_type(json_data[:20])
            schema_obj = create_schema_object(
                name=base_model_name,
                physical_type="array",
                description=f"Generated from JSON array in {source}",
            )
    elif isinstance(json_data, dict):
        properties = []
        for key, value in json_data.items():
            field_def = generate_field_definition(value, key)
            properties.append(dict_to_property(key, field_def))

        schema_obj = create_schema_object(
            name=base_model_name,
            physical_type="object",
            description=f"Generated from JSON object in {source}",
            properties=properties,
        )
    else:
        field_type, field_format = determine_type_and_format(json_data)
        schema_obj = create_schema_object(
            name=base_model_name,
            physical_type=field_type,
            description=f"Generated from JSON primitive in {source}",
        )

    odcs.schema_ = [schema_obj]
    return odcs


def dict_to_property(name: str, field_def: Dict[str, Any]) -> SchemaProperty:
    """Convert a field definition dict to an ODCS SchemaProperty."""
    logical_type = map_json_type_to_odcs(field_def.get("type", "string"))

    nested_properties = None
    if field_def.get("type") == "object" and "fields" in field_def:
        nested_properties = [dict_to_property(k, v) for k, v in field_def["fields"].items()]

    items_prop = None
    if field_def.get("type") == "array" and "items" in field_def:
        items_prop = dict_to_property("items", field_def["items"])

    examples = field_def.get("examples")

    custom_props = {}
    if field_def.get("format"):
        custom_props["format"] = field_def.get("format")

    return create_property(
        name=name,
        logical_type=logical_type,
        physical_type=field_def.get("type"),
        examples=examples,
        properties=nested_properties,
        items=items_prop,
        custom_properties=custom_props if custom_props else None,
    )


def map_json_type_to_odcs(json_type: str) -> str:
    """Map JSON type to ODCS logical type."""
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


def generate_field_definition(value: Any, field_name: str) -> Dict[str, Any]:
    """Generate a field definition for a JSON value."""
    if isinstance(value, dict):
        fields = {}
        for key, nested_value in value.items():
            fields[key] = generate_field_definition(nested_value, key)
        return {"type": "object", "fields": fields}

    elif isinstance(value, list):
        if not value:
            return {"type": "array", "items": {"type": "string"}}

        if all(isinstance(item, dict) for item in value):
            fields = {}
            for item in value:
                for key, nested_value in item.items():
                    field_def = generate_field_definition(nested_value, key)
                    if key in fields:
                        fields[key] = merge_field_definitions(fields[key], field_def)
                    else:
                        fields[key] = field_def
            return {"type": "array", "items": {"type": "object", "fields": fields}}

        elif all(isinstance(item, list) for item in value):
            inner_type, inner_format = infer_array_type(value[0])
            return {
                "type": "array",
                "items": {
                    "type": "array",
                    "items": {"type": inner_type, "format": inner_format} if inner_format else {"type": inner_type},
                },
            }
        else:
            item_type, item_format = infer_array_type(value)
            items_def = {"type": item_type}
            if item_format:
                items_def["format"] = item_format
            field_def = {"type": "array", "items": items_def}
            sample_values = [item for item in value[:5] if item is not None]
            if sample_values:
                field_def["examples"] = sample_values
            return field_def
    else:
        field_type, field_format = determine_type_and_format(value)
        field_def = {"type": field_type}
        if field_format:
            field_def["format"] = field_format
        if value is not None and field_type != "boolean":
            field_def["examples"] = [value]
        return field_def


def infer_array_type(array: List) -> Tuple[str, Optional[str]]:
    """Infer the common type of items in an array."""
    if not array:
        return "string", None

    if all(isinstance(item, dict) for item in array):
        return "object", None

    non_null_items = [item for item in array if item is not None]
    if not non_null_items:
        return "null", None

    types_and_formats = [determine_type_and_format(item) for item in non_null_items]
    types = {t for t, _ in types_and_formats}
    formats = {f for _, f in types_and_formats if f is not None}

    if types == {"integer", "number"}:
        return "number", None
    if len(types) == 1:
        type_name = next(iter(types))
        format_name = next(iter(formats)) if len(formats) == 1 else None
        return type_name, format_name
    if all(t in {"string", "integer", "number", "boolean", "null"} for t in types):
        if len(formats) == 1 and "string" in types:
            return "string", next(iter(formats))
        return "string", None

    return "string", None


def determine_type_and_format(value: Any) -> Tuple[str, Optional[str]]:
    """Determine the datacontract type and format for a JSON value."""
    if value is None:
        return "null", None
    elif isinstance(value, bool):
        return "boolean", None
    elif isinstance(value, int):
        return "integer", None
    elif isinstance(value, float):
        return "number", None
    elif isinstance(value, str):
        try:
            if re.match(r"^\d{4}-\d{2}-\d{2}$", value):
                return "string", "date"
            elif re.match(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$", value):
                return "string", "date-time"
            elif re.match(r"^[\w\.-]+@([\w-]+\.)+[\w-]{2,4}$", value):
                return "string", "email"
            elif re.match(r"^[a-f0-9]{8}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{12}$", value.lower()):
                return "string", "uuid"
            else:
                return "string", None
        except re.error:
            return "string", None
    elif isinstance(value, dict):
        return "object", None
    elif isinstance(value, list):
        return "array", None
    else:
        return "string", None


def merge_field_definitions(field1: Dict[str, Any], field2: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two field definitions."""
    result = field1.copy()
    if field1.get("type") == "object" and field2.get("type") != "object":
        return field1
    if field2.get("type") == "object" and field1.get("type") != "object":
        return field2

    if field1.get("type") != field2.get("type"):
        type1 = field1.get("type", "string")
        type2 = field2.get("type", "string")

        if (type1 == "integer" and type2 == "number") or (type1 == "number" and type2 == "integer"):
            result["type"] = "number"
        elif "string" in [type1, type2]:
            result["type"] = "string"
        elif type1 == "array" and type2 == "array":
            items1 = field1.get("items", {})
            items2 = field2.get("items", {})
            if items1.get("type") == "object" or items2.get("type") == "object":
                if items1.get("type") == "object" and items2.get("type") == "object":
                    merged_items = merge_field_definitions(items1, items2)
                else:
                    merged_items = items1 if items1.get("type") == "object" else items2
                return {"type": "array", "items": merged_items}
            else:
                merged_items = merge_field_definitions(items1, items2)
                return {"type": "array", "items": merged_items}
        else:
            result["type"] = "array" if "array" in [type1, type2] else "object"

        if "format" in result:
            del result["format"]

    if "examples" in field2:
        if "examples" in result:
            combined = result["examples"] + [ex for ex in field2["examples"] if ex not in result["examples"]]
            result["examples"] = combined[:5]
        else:
            result["examples"] = field2["examples"]

    if result.get("type") == "array" and "items" in field1 and "items" in field2:
        result["items"] = merge_field_definitions(field1["items"], field2["items"])
    elif result.get("type") == "object" and "fields" in field1 and "fields" in field2:
        merged_fields = field1["fields"].copy()
        for key, field_def in field2["fields"].items():
            if key in merged_fields:
                merged_fields[key] = merge_field_definitions(merged_fields[key], field_def)
            else:
                merged_fields[key] = field_def
        result["fields"] = merged_fields

    return result
