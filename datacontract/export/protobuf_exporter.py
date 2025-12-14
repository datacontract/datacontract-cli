import sys
from typing import List, Optional

from open_data_contract_standard.model import OpenDataContractStandard, SchemaProperty

from datacontract.export.exporter import Exporter


class ProtoBufExporter(Exporter):
    def export(self, data_contract, schema_name, server, sql_server_type, export_args) -> dict:
        # Returns a dict containing the protobuf representation.
        proto = to_protobuf(data_contract)
        return proto


def _get_config_value(prop: SchemaProperty, key: str) -> Optional[str]:
    """Get a custom property value."""
    if prop.customProperties is None:
        return None
    for cp in prop.customProperties:
        if cp.property == key:
            return cp.value
    return None


def _get_logical_type_option(prop: SchemaProperty, key: str):
    """Get a logical type option value."""
    if prop.logicalTypeOptions is None:
        return None
    return prop.logicalTypeOptions.get(key)


def to_protobuf(data_contract: OpenDataContractStandard) -> str:
    """
    Generates a Protobuf file from the data contract specification.
    Scans all models for enum fields (even if the type is "string") by checking for a "values" property.
    """
    messages = ""
    enum_definitions = {}

    if data_contract.schema_ is None:
        return ""

    # Iterate over all models to generate messages and collect enum definitions.
    for schema_obj in data_contract.schema_:
        properties = schema_obj.properties or []
        for prop in properties:
            # If the field has enum values, collect them.
            if _is_enum_field(prop):
                enum_name = _get_enum_name(prop)
                enum_values = _get_enum_values(prop)
                if enum_values and enum_name not in enum_definitions:
                    enum_definitions[enum_name] = enum_values

        messages += to_protobuf_message(schema_obj.name, properties, schema_obj.description or "", 0)
        messages += "\n"

    # Build header with syntax and package declarations.
    header = 'syntax = "proto3";\n\n'
    package = "example"  # Default package
    header += f"package {package};\n\n"

    # Append enum definitions.
    for enum_name, enum_values in enum_definitions.items():
        header += f"// Enum for {enum_name}\n"
        header += f"enum {enum_name} {{\n"
        # Only iterate if enum_values is a dictionary.
        if isinstance(enum_values, dict):
            for enum_const, value in sorted(enum_values.items(), key=lambda item: item[1]):
                normalized_const = enum_const.upper().replace(" ", "_")
                header += f"  {normalized_const} = {value};\n"
        else:
            header += f"  // Warning: Enum values for {enum_name} are not a dictionary\n"
        header += "}\n\n"
    return header + messages


def _is_enum_field(prop: SchemaProperty) -> bool:
    """
    Returns True if the field has a non-empty "enumValues" property (via customProperties).
    """
    values = _get_config_value(prop, "enumValues")
    return bool(values)


def _get_enum_name(prop: SchemaProperty) -> str:
    """
    Returns the enum name either from the field's "enum_name" or derived from the field name.
    """
    enum_name = _get_config_value(prop, "enum_name")
    if enum_name:
        return enum_name
    return _to_protobuf_message_name(prop.name)


def _get_enum_values(prop: SchemaProperty) -> dict:
    """
    Returns the enum values from the field.
    """
    values = _get_config_value(prop, "enumValues")
    if values and isinstance(values, dict):
        return values
    return {}


def _to_protobuf_message_name(name: str) -> str:
    """
    Returns a valid Protobuf message/enum name by capitalizing the first letter.
    """
    return name[0].upper() + name[1:] if name else name


def to_protobuf_message(model_name: str, properties: List[SchemaProperty], description: str, indent_level: int = 0) -> str:
    """
    Generates a Protobuf message definition from the model's fields.
    Handles nested messages for complex types.
    """
    result = ""
    if description:
        result += f"{indent(indent_level)}// {description}\n"

    result += f"message {_to_protobuf_message_name(model_name)} {{\n"
    number = 1
    for prop in properties:
        # For nested objects, generate a nested message.
        field_type = prop.logicalType or ""
        if field_type.lower() in ["object", "record", "struct"]:
            nested_desc = prop.description or ""
            nested_props = prop.properties or []
            nested_message = to_protobuf_message(prop.name, nested_props, nested_desc, indent_level + 1)
            result += nested_message + "\n"

        field_desc = prop.description or ""
        result += to_protobuf_field(prop, field_desc, number, indent_level + 1) + "\n"
        number += 1

    result += f"{indent(indent_level)}}}\n"
    return result


def to_protobuf_field(prop: SchemaProperty, description: str, number: int, indent_level: int = 0) -> str:
    """
    Generates a field definition within a Protobuf message.
    """
    result = ""
    if description:
        result += f"{indent(indent_level)}// {description}\n"
    result += f"{indent(indent_level)}{_convert_type(prop)} {prop.name} = {number};"
    return result


def indent(indent_level: int) -> str:
    return "  " * indent_level


def _convert_type(prop: SchemaProperty) -> str:
    """
    Converts a field's type (from the data contract) to a Protobuf type.
    Prioritizes enum conversion if a non-empty "values" property exists.
    """
    # For debugging purposes
    print("Converting field:", prop.name, file=sys.stderr)
    # If the field should be treated as an enum, return its enum name.
    if _is_enum_field(prop):
        return _get_enum_name(prop)

    field_type = prop.logicalType or ""
    lower_type = field_type.lower()

    if lower_type in ["string", "varchar", "text"]:
        return "string"
    if lower_type in ["timestamp", "timestamp_tz", "timestamp_ntz", "date", "time"]:
        return "string"
    if lower_type in ["number", "decimal", "numeric"]:
        return "double"
    if lower_type in ["float", "double"]:
        return lower_type
    if lower_type in ["integer", "int"]:
        return "int32"
    if lower_type in ["long", "bigint"]:
        return "int64"
    if lower_type in ["boolean"]:
        return "bool"
    if lower_type in ["bytes"]:
        return "bytes"
    if lower_type in ["object", "record", "struct"]:
        return _to_protobuf_message_name(prop.name)
    if lower_type == "array":
        # Handle array types. Check for an "items" property.
        if prop.items:
            items_type = prop.items.logicalType or ""
            if items_type.lower() in ["object", "record", "struct"]:
                # Singularize the field name (a simple approach).
                singular = prop.name[:-1] if prop.name.endswith("s") else prop.name
                return "repeated " + _to_protobuf_message_name(singular)
            else:
                return "repeated " + _convert_type(prop.items)
        else:
            return "repeated string"
    # Fallback for unrecognized types.
    return "string"
