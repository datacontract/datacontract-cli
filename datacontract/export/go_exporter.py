import re
from typing import List, Optional

from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, SchemaProperty

from datacontract.export.exporter import Exporter


class GoExporter(Exporter):
    def export(self, data_contract, schema_name, server, sql_server_type, export_args) -> dict:
        return to_go_types(data_contract)


def to_go_types(contract: OpenDataContractStandard) -> str:
    result = "package main\n\n"

    if contract.schema_:
        for schema_obj in contract.schema_:
            go_types = generate_go_type(schema_obj, schema_obj.name)
            for go_type in go_types:
                result += f"\n{go_type}\n"

    return result


def _get_type(prop: SchemaProperty) -> Optional[str]:
    """Get the logical type from a schema property."""
    return prop.logicalType


def python_type_to_go_type(prop_type: Optional[str], physical_type: Optional[str] = None) -> str:
    """Convert ODCS type to Go type."""
    # Check physical type first for more specific mappings
    if physical_type:
        pt = physical_type.lower()
        if pt in ["text", "varchar", "char", "nvarchar"]:
            return "string"
        if pt in ["timestamp", "datetime", "timestamp_tz", "timestamp_ntz"]:
            return "time.Time"
        if pt in ["long", "bigint", "int64"]:
            return "int64"
        if pt in ["int", "integer", "int32"]:
            return "int"
        if pt in ["float", "real", "float32"]:
            return "float32"
        if pt in ["double", "float64"]:
            return "float64"
        if pt in ["bool", "boolean"]:
            return "bool"

    # Then check logical type
    match prop_type:
        case "string":
            return "string"
        case "date":
            return "time.Time"
        case "integer":
            return "int64"
        case "number":
            return "float64"
        case "boolean":
            return "bool"
        case _:
            return "interface{}"


def to_camel_case(snake_str) -> str:
    return "".join(word.capitalize() for word in re.split(r"_|(?<!^)(?=[A-Z])", snake_str))


def get_subtype(prop: SchemaProperty, nested_types: dict, type_name: str, camel_case_name: str) -> str:
    go_type = "interface{}"
    if prop.properties:
        nested_type_name = to_camel_case(f"{type_name}_{camel_case_name}")
        nested_types[nested_type_name] = prop.properties
        go_type = nested_type_name

    prop_type = _get_type(prop)
    physical_type = prop.physicalType

    match prop_type:
        case "array":
            if prop.items:
                item_type = get_subtype(prop.items, nested_types, type_name, camel_case_name + "Item")
                go_type = f"[]{item_type}"
            else:
                go_type = "[]interface{}"
        case "object":
            if prop.properties:
                nested_type_name = to_camel_case(f"{type_name}_{camel_case_name}")
                nested_types[nested_type_name] = prop.properties
                go_type = nested_type_name
            else:
                go_type = "interface{}"
        case _:
            if physical_type and physical_type.lower() in ["record", "struct"]:
                if prop.properties:
                    nested_type_name = to_camel_case(f"{type_name}_{camel_case_name}")
                    nested_types[nested_type_name] = prop.properties
                    go_type = nested_type_name
            elif prop_type:
                go_type = python_type_to_go_type(prop_type, physical_type)

    return go_type


def generate_go_type(schema_obj: SchemaObject, model_name: str) -> List[str]:
    go_types = []
    type_name = to_camel_case(model_name)
    lines = [f"type {type_name} struct {{"]

    nested_types = {}

    if schema_obj.properties:
        for prop in schema_obj.properties:
            prop_type = _get_type(prop)
            physical_type = prop.physicalType
            go_type = python_type_to_go_type(prop_type, physical_type)
            camel_case_name = to_camel_case(prop.name)
            json_tag = prop.name if prop.required else f"{prop.name},omitempty"
            avro_tag = prop.name

            if go_type == "interface{}":
                go_type = get_subtype(prop, nested_types, type_name, camel_case_name)

            go_type = go_type if prop.required else f"*{go_type}"
            description = prop.description or ""
            comment = f"  // {description}" if description else ""

            lines.append(f'    {camel_case_name} {go_type} `json:"{json_tag}" avro:"{avro_tag}"`{comment}')

    lines.append("}")
    go_types.append("\n".join(lines))

    # Generate nested types
    for nested_type_name, nested_properties in nested_types.items():
        # Create a temporary SchemaObject for nested types
        nested_schema = SchemaObject(name=nested_type_name, properties=nested_properties)
        nested_go_types = generate_go_type(nested_schema, nested_type_name)
        go_types.extend(nested_go_types)

    return go_types
