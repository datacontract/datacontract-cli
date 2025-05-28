import json
import os
import re
from typing import Any, Dict, List, Optional, Tuple

from datacontract.imports.importer import Importer
from datacontract.model.data_contract_specification import DataContractSpecification, Model, Server


class JsonImporter(Importer):
    def import_source(
        self, data_contract_specification: DataContractSpecification, source: str, import_args: dict
    ) -> DataContractSpecification:
        return import_json(data_contract_specification, source)


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


def import_json(
    data_contract_specification: DataContractSpecification, source: str, include_examples: bool = False
) -> DataContractSpecification:
    # use the file name as base model name
    base_model_name = os.path.splitext(os.path.basename(source))[0]

    # check if file is newline-delimited JSON
    if is_ndjson(source):
        # load NDJSON data
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
        # load regular JSON data
        with open(source, "r", encoding="utf-8") as file:
            json_data = json.load(file)

    if data_contract_specification.servers is None:
        data_contract_specification.servers = {}

    data_contract_specification.servers["production"] = Server(type="local", path=source, format="json")

    # initialisation
    models = {}

    if isinstance(json_data, list) and json_data:
        # Array of items
        if all(isinstance(item, dict) for item in json_data[:5]):
            # Array of objects, as table
            fields = {}
            for item in json_data[:20]:
                for key, value in item.items():
                    field_def = generate_field_definition(value, key, base_model_name, models)
                    if key in fields:
                        fields[key] = merge_field_definitions(fields[key], field_def)
                    else:
                        fields[key] = field_def

            models[base_model_name] = {
                "type": "table",
                "description": f"Generated from JSON array in {source}",
                "fields": fields,
                "examples": json_data[:3] if include_examples else None,
            }
        else:
            # Simple array
            item_type, item_format = infer_array_type(json_data[:20])
            models[base_model_name] = {
                "type": "array",
                "description": f"Generated from JSON array in {source}",
                "items": {"type": item_type, "format": item_format} if item_format else {"type": item_type},
                "examples": [json_data[:5]] if include_examples else None,
            }
    elif isinstance(json_data, dict):
        # Single object
        fields = {}
        for key, value in json_data.items():
            fields[key] = generate_field_definition(value, key, base_model_name, models)

        models[base_model_name] = {
            "type": "object",
            "description": f"Generated from JSON object in {source}",
            "fields": fields,
            "examples": [json_data] if include_examples else None,
        }
    else:
        # Primitive value
        field_type, field_format = determine_type_and_format(json_data)
        models[base_model_name] = {
            "type": field_type,
            "description": f"Generated from JSON primitive in {source}",
            "format": field_format,
            "examples": [json_data] if include_examples and field_type != "boolean" else None,
        }

    for model_name, model_def in models.items():
        model_type = model_def.pop("type")
        data_contract_specification.models[model_name] = Model(type=model_type, **model_def)

    return data_contract_specification


def generate_field_definition(
    value: Any, field_name: str, parent_model: str, models: Dict[str, Dict[str, Any]]
) -> Dict[str, Any]:
    """Generate a field definition for a JSON value, creating nested models."""

    if isinstance(value, dict):
        # Handle object fields
        fields = {}
        for key, nested_value in value.items():
            fields[key] = generate_field_definition(nested_value, key, parent_model, models)

        return {"type": "object", "fields": fields}

    elif isinstance(value, list):
        # Handle array fields
        if not value:
            return {"type": "array", "items": {"type": "string"}}

        if all(isinstance(item, dict) for item in value):
            # Array of objects
            fields = {}
            for item in value:
                for key, nested_value in item.items():
                    field_def = generate_field_definition(nested_value, key, parent_model, models)
                    if key in fields:
                        fields[key] = merge_field_definitions(fields[key], field_def)
                    else:
                        fields[key] = field_def

            return {"type": "array", "items": {"type": "object", "fields": fields}}

        elif all(isinstance(item, list) for item in value):
            # Array of arrays
            inner_type, inner_format = infer_array_type(value[0])
            return {
                "type": "array",
                "items": {
                    "type": "array",
                    "items": {"type": inner_type, "format": inner_format} if inner_format else {"type": inner_type},
                },
                "examples": value[:5],  # Include examples for nested arrays
            }

        else:
            # Array of simple or mixed types
            item_type, item_format = infer_array_type(value)
            items_def = {"type": item_type}
            if item_format:
                items_def["format"] = item_format

            field_def = {"type": "array", "items": items_def}

            # Add examples if appropriate
            sample_values = [item for item in value[:5] if item is not None]
            if sample_values:
                field_def["examples"] = sample_values

            return field_def

    else:
        # Handle primitive types
        field_type, field_format = determine_type_and_format(value)
        field_def = {"type": field_type}
        if field_format:
            field_def["format"] = field_format

        # Add examples
        if value is not None and field_type != "boolean":
            field_def["examples"] = [value]

        return field_def


def infer_array_type(array: List) -> Tuple[str, Optional[str]]:
    """Infer the common type of items in an array."""
    if not array:
        return "string", None

    # if all items are dictionaries with the same structure
    if all(isinstance(item, dict) for item in array):
        return "object", None

    # if all items are of the same primitive type
    non_null_items = [item for item in array if item is not None]
    if not non_null_items:
        return "null", None

    types_and_formats = [determine_type_and_format(item) for item in non_null_items]
    types = {t for t, _ in types_and_formats}
    formats = {f for _, f in types_and_formats if f is not None}

    # simplify type combinations
    if types == {"integer", "number"}:
        return "number", None
    if len(types) == 1:
        type_name = next(iter(types))
        format_name = next(iter(formats)) if len(formats) == 1 else None
        return type_name, format_name
    if all(t in {"string", "integer", "number", "boolean", "null"} for t in types):
        # If all string values have the same format, keep it
        if len(formats) == 1 and "string" in types:
            return "string", next(iter(formats))
        return "string", None

    # Mixed types
    return "string", None


def determine_type_and_format(value: Any) -> Tuple[str, Optional[str]]:
    """determine the datacontract type and format for a JSON value."""
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
    # Handle type differences
    if field1.get("type") != field2.get("type"):
        type1, _ = field1.get("type", "string"), field1.get("format")
        type2, _ = field2.get("type", "string"), field2.get("format")

        if type1 == "integer" and type2 == "number" or type1 == "number" and type2 == "integer":
            common_type = "number"
            common_format = None
        elif "string" in [type1, type2]:
            common_type = "string"
            common_format = None
        elif all(t in ["string", "integer", "number", "boolean", "null"] for t in [type1, type2]):
            common_type = "string"
            common_format = None
        elif type1 == "array" and type2 == "array":
            # Handle mixed array types
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
            common_type = "array" if "array" in [type1, type2] else "object"
            common_format = None

        result["type"] = common_type
        if common_format:
            result["format"] = common_format
        elif "format" in result:
            del result["format"]

    # Merge examples
    if "examples" in field2:
        if "examples" in result:
            combined = result["examples"] + [ex for ex in field2["examples"] if ex not in result["examples"]]
            result["examples"] = combined[:5]  # Limit to 5 examples
        else:
            result["examples"] = field2["examples"]

    # Handle nested structures
    if result.get("type") == "array" and "items" in field1 and "items" in field2:
        result["items"] = merge_field_definitions(field1["items"], field2["items"])
    elif result.get("type") == "object" and "fields" in field1 and "fields" in field2:
        # Merge fields from both objects
        merged_fields = field1["fields"].copy()
        for key, field_def in field2["fields"].items():
            if key in merged_fields:
                merged_fields[key] = merge_field_definitions(merged_fields[key], field_def)
            else:
                merged_fields[key] = field_def
        result["fields"] = merged_fields

    return result
