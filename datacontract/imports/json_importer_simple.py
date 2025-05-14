import json
import os
import re
from typing import Any, Dict, List, Tuple, Optional

from datacontract.imports.importer import Importer
from datacontract.model.data_contract_specification import DataContractSpecification, Model, Server


class JsonImporter(Importer):
    def import_source(
        self, data_contract_specification: DataContractSpecification, source: str, import_args: dict
    ) -> DataContractSpecification:
        return import_json(data_contract_specification, source)


def import_json(
    data_contract_specification: DataContractSpecification, source: str, include_examples: bool = False
) -> DataContractSpecification:
    # use the file name as base model name
    base_model_name = os.path.splitext(os.path.basename(source))[0]
    
    with open(source, 'r') as file:
        json_data = json.load(file)
    
    if data_contract_specification.servers is None:
        data_contract_specification.servers = {}
    
    data_contract_specification.servers["production"] = Server(
        type="local", path=source, format="json"
    )
    
    if isinstance(json_data, list) and json_data:
        if all(isinstance(item, dict) for item in json_data[:5]):
            fields = {}
            for item in json_data[:20]:
                for key, value in item.items():
                    field_def = generate_field_definition(value)
                    if key in fields:
                        fields[key] = merge_simple_field_definitions(fields[key], field_def)
                    else:
                        fields[key] = field_def
            
            data_contract_specification.models[base_model_name] = Model(
                type="table",
                description=f"Generated from JSON array in {source}",
                fields=fields,
                examples=json_data[:3] if include_examples else None
            )
        else:
            # Simple array of primitives or mixed types
            item_type, item_format = infer_simple_array_type(json_data[:20])
            items_def = {"type": item_type}
            if item_format:
                items_def["format"] = item_format
                
            data_contract_specification.models[base_model_name] = Model(
                type="array",
                description=f"Generated from JSON array in {source}",
                items=items_def,
                examples=[json_data[:5]] if include_examples else None
            )
    elif isinstance(json_data, dict):
        # Single object
        fields = {}
        for key, value in json_data.items():
            fields[key] = generate_field_definition(value)
        
        data_contract_specification.models[base_model_name] = Model(
            type="object",
            description=f"Generated from JSON object in {source}",
            fields=fields,
            examples=[json_data] if include_examples else None
        )
    else:
        # Primitive value
        field_type, field_format = determine_type_and_format(json_data)
        model_def = {
            "description": f"Generated from JSON primitive in {source}",
        }
        if field_format:
            model_def["format"] = field_format
        if include_examples and field_type != "boolean":
            model_def["examples"] = [json_data]
            
        data_contract_specification.models[base_model_name] = Model(
            type=field_type,
            **model_def
        )
    
    return data_contract_specification


def generate_field_definition(value: Any) -> Dict[str, Any]:
    """Generate a simplified field definition without creating nested models."""
    if isinstance(value, dict):
        # Traiter tous les objets comme simples (inline)
        fields = {}
        for key, nested_value in value.items():
            field_type, field_format = determine_type_and_format(nested_value)
            field_def = {"type": field_type}
            if field_format:
                field_def["format"] = field_format
            if nested_value is not None and field_type != "boolean":
                field_def["examples"] = [nested_value]
            fields[key] = field_def
        
        return {
            "type": "object",
            "fields": fields
        }
            
    elif isinstance(value, list):
        # Array field
        if not value:
            return {"type": "array", "items": {"type": "any"}}
        
        # Traiter tous les tableaux comme des tableaux simples
        item_type, item_format = infer_simple_array_type(value[:20])
        items_def = {"type": item_type}
        if item_format:
            items_def["format"] = item_format
        
        field_def = {
            "type": "array",
            "items": items_def
        }
        
        # Add examples if appropriate
        if item_type not in ["boolean", "any", "null"]:
            sample_values = [item for item in value[:5] if item is not None]
            if sample_values:
                field_def["examples"] = [sample_values]
        
        return field_def
            
    else:
        # Primitive type
        field_type, field_format = determine_type_and_format(value)
        field_def = {"type": field_type}
        if field_format:
            field_def["format"] = field_format
        
        # Add examples if appropriate
        if value is not None and field_type != "boolean":
            field_def["examples"] = [value]
        
        return field_def


def infer_simple_array_type(array: List) -> Tuple[str, Optional[str]]:
    """Infer the common type of items in an array."""
    if not array:
        return "any", None
    
    # Si tous les éléments sont des objets, type object simple
    if all(isinstance(item, dict) for item in array):
        return "object", None
    
    # Pour les types primitifs
    non_null_items = [item for item in array if item is not None]
    if not non_null_items:
        return "null", None
    
    types_and_formats = [determine_type_and_format(item) for item in non_null_items]
    types = {t for t, _ in types_and_formats}
    formats = {f for _, f in types_and_formats if f is not None}
    
    # Simplification des types
    if types == {"integer", "number"}:
        return "number", None
    if len(types) == 1:
        type_name = next(iter(types))
        format_name = next(iter(formats)) if len(formats) == 1 else None
        return type_name, format_name
    
    # Types mixtes
    return "any", None


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
            if re.match(r'^\d{4}-\d{2}-\d{2}$', value):
                return "string", "date"
            elif re.match(r'^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(\.\d+)?(Z|[+-]\d{2}:\d{2})?$', value):
                return "string", "date-time"
            elif re.match(r'^[\w\.-]+@([\w-]+\.)+[\w-]{2,4}$', value):
                return "string", "email"
            elif re.match(r'^[a-f0-9]{8}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{12}$', value.lower()):
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
        return "any", None


def merge_simple_field_definitions(field1: Dict[str, Any], field2: Dict[str, Any]) -> Dict[str, Any]:
    """Merge two field definitions, reconciling type differences."""
    result = field1.copy()
    
    # Handle type differences
    if field1.get("type") != field2.get("type"):
        type1, format1 = field1.get("type", "any"), field1.get("format")
        type2, format2 = field2.get("type", "any"), field2.get("format")
        
        # Determine common type
        if type1 == "integer" and type2 == "number" or type1 == "number" and type2 == "integer":
            result["type"] = "number"
        elif "any" in [type1, type2]:
            result["type"] = "any"
        else:
            result["type"] = "string"
        
        # Reset format when type changes
        if "format" in result:
            del result["format"]
    
    # Merge examples
    if "examples" in field2:
        if "examples" in result:
            combined = result["examples"] + [ex for ex in field2["examples"] if ex not in result["examples"]]
            result["examples"] = combined[:5]  # Limit to 5 examples
        else:
            result["examples"] = field2["examples"]
    
    return result