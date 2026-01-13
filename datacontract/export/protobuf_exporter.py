import sys
from typing import List, Optional

from open_data_contract_standard.model import OpenDataContractStandard, SchemaProperty

from datacontract.export.exporter import Exporter


class ProtoBufExporter(Exporter):
    def export(self, data_contract, schema_name, server, sql_server_type, export_args) -> dict:
        """Exports data contract to Protobuf format."""
        proto = to_protobuf(data_contract)
        return proto


def _get_config_value(prop: SchemaProperty, key: str) -> Optional[str]:
    """Get a custom property value from customProperties."""
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
    package = "example"  # Default package, can be customized
    header += f"package {package};\n\n"

    # Append enum definitions before messages.
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
    Uses UpperCamelCase formatting.
    """
    enum_name = _get_config_value(prop, "enum_name")
    if enum_name:
        return _snake_to_upper_camel(enum_name)
    return _snake_to_upper_camel(prop.name)


def _get_enum_values(prop: SchemaProperty) -> dict:
    """
    Returns the enum values from the field.
    """
    values = _get_config_value(prop, "enumValues")
    if values and isinstance(values, dict):
        return values
    return {}


def _snake_to_upper_camel(name: str) -> str:
    """
    Convert snake_case to UpperCamelCase.
    Preserves existing capitalization in parts.
    
    Examples:
      "fsa_room" -> "FsaRoom"
      "FsaRegister" -> "FsaRegister" (already in UpperCamelCase)
      "simple_obj" -> "SimpleObj"
    """
    if not name:
        return name
    
    # If already UpperCamelCase (first letter uppercase, no underscores after first word)
    if name and name[0].isupper() and '_' not in name:
        return name
    
    parts = name.split('_')
    # Capitalize each part while preserving internal capitalization
    return ''.join(part[0].upper() + part[1:] if part else '' for part in parts)


def _get_type_name(prop: SchemaProperty) -> str:
    """
    Get appropriate message/enum type name in UpperCamelCase.
    Used for message declarations and field type references.
    """
    # For enums
    if _is_enum_field(prop):
        return _get_enum_name(prop)
    
    # For regular objects
    if prop.logicalType and prop.logicalType.lower() in ["object", "record", "struct"]:
        return _snake_to_upper_camel(prop.name)
    
    # For objects inside arrays
    if (prop.logicalType and prop.logicalType.lower() == "array" and 
        prop.items and prop.items.logicalType and 
        prop.items.logicalType.lower() in ["object", "record", "struct"]):
        
        # If explicit name is provided in items.name
        if hasattr(prop.items, 'name') and prop.items.name:
            # Use as-is (might already be in UpperCamelCase)
            return prop.items.name
        
        # Otherwise generate from field name
        return _get_singular_type_name(prop.name)
    
    return _snake_to_upper_camel(prop.name)


def _get_singular_type_name(field_name: str) -> str:
    """
    Convert field name to singular type name in UpperCamelCase.
    
    Example: "fsa_rooms" -> "FsaRoom"
    """
    # First convert to UpperCamelCase
    field_name_upper = _snake_to_upper_camel(field_name)
    
    # Then make singular (remove trailing 's')
    if field_name_upper.endswith('s'):
        return field_name_upper[:-1]  # Remove 's' for plural forms
    return field_name_upper


def _should_create_nested_message(prop: SchemaProperty) -> bool:
    """
    Check if we need to create a nested message for this property.
    Returns True for objects and arrays of objects.
    """
    if not prop.logicalType:
        return False
    
    lower_type = prop.logicalType.lower()
    
    # Regular object
    if lower_type in ["object", "record", "struct"]:
        return True
    
    # Array of objects
    if lower_type == "array" and prop.items:
        items_lower_type = prop.items.logicalType.lower() if prop.items.logicalType else ""
        return items_lower_type in ["object", "record", "struct"]
    
    return False


def _get_nested_properties(prop: SchemaProperty) -> Optional[List[SchemaProperty]]:
    """
    Get properties for nested message.
    Returns None if no nested properties.
    """
    if prop.logicalType and prop.logicalType.lower() in ["object", "record", "struct"]:
        return prop.properties or []
    
    if (prop.logicalType and prop.logicalType.lower() == "array" and 
        prop.items and prop.items.logicalType and 
        prop.items.logicalType.lower() in ["object", "record", "struct"]):
        return prop.items.properties or []
    
    return None


def _get_nested_description(prop: SchemaProperty) -> str:
    """
    Get description for nested message.
    """
    if prop.logicalType and prop.logicalType.lower() in ["object", "record", "struct"]:
        return prop.description or ""
    
    if (prop.logicalType and prop.logicalType.lower() == "array" and 
        prop.items and prop.items.logicalType and 
        prop.items.logicalType.lower() in ["object", "record", "struct"]):
        return prop.items.description or ""
    
    return ""


def _get_primitive_type(prop: SchemaProperty) -> str:
    """
    Get Protobuf type for primitive fields.
    Handles recursive type resolution for arrays of primitives.
    """
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
    
    # Recursive handling for arrays of primitives
    if lower_type == "array" and prop.items:
        return _get_primitive_type(prop.items)
    
    return "string"  # Fallback for unrecognized types


def _get_field_type(prop: SchemaProperty) -> str:
    """
    Get Protobuf type for field (string, int32, repeated TypeName, etc).
    Combines repeated keyword with type name for arrays.
    """
    field_type = prop.logicalType or ""
    lower_type = field_type.lower()
    
    # Handle arrays
    if lower_type == "array":
        if prop.items:
            items_type = prop.items.logicalType or ""
            items_lower_type = items_type.lower()
            
            # If array contains objects
            if items_lower_type in ["object", "record", "struct"]:
                type_name = _get_type_name(prop)  # e.g., FsaRoom
                return f"repeated {type_name}"
            else:
                # For primitive types
                primitive_type = _get_primitive_type(prop.items)
                return f"repeated {primitive_type}"
        else:
            return "repeated string"  # Default array type
    
    # Handle regular objects
    if lower_type in ["object", "record", "struct"]:
        type_name = _get_type_name(prop)  # e.g., SimpleObj
        return type_name
    
    # Handle enums
    if _is_enum_field(prop):
        return _get_enum_name(prop)
    
    # Handle primitive types
    return _get_primitive_type(prop)


def to_protobuf_message(model_name: str, properties: List[SchemaProperty], description: str, indent_level: int = 0) -> str:
    """
    Generates a Protobuf message definition from the model's fields.
    Handles nested messages for complex types recursively.
    """
    result = ""
    if description:
        result += f"{indent(indent_level)}// {description}\n"

    # Message name always in UpperCamelCase
    message_name = _snake_to_upper_camel(model_name)
    result += f"message {message_name} {{\n"
    
    # Phase 1: Create all nested messages
    for prop in properties:
        if _should_create_nested_message(prop):
            type_name = _get_type_name(prop)  # UpperCamelCase
            nested_props = _get_nested_properties(prop)
            nested_desc = _get_nested_description(prop)
            
            if nested_props is not None:
                nested_message = to_protobuf_message(type_name, nested_props, nested_desc, indent_level + 1)
                result += nested_message + "\n"
    
    # Phase 2: Create all fields
    number = 1
    for prop in properties:
        field_name = prop.name  # snake_case (preserve as in YAML)
        # field_type = _get_field_type(prop)  # includes "repeated" if needed
        field_decl = _get_field_declaration(prop)  # Новая функция
        field_desc = prop.description or ""
        
        result += f"{indent(indent_level + 1)}"
        if field_desc:
            result += f"// {field_desc}\n{indent(indent_level + 1)}"
        
        result += f"{field_decl} {field_name} = {number};\n"
        number += 1

    result += f"{indent(indent_level)}}}\n"
    return result


def indent(indent_level: int) -> str:
    """Generate indentation string for Protobuf formatting."""
    return "  " * indent_level


def _get_field_declaration(prop: SchemaProperty) -> str:
    """
    Returns field declaration with optional keyword if needed.
    """
    field_type = _get_field_type(prop)  # includes "repeated" if needed
    
    # Add 'optional' for non-required fields that are not arrays
    if (hasattr(prop, 'required') and prop.required is False and
        not (prop.logicalType and prop.logicalType.lower() == "array")):
        return f"optional {field_type}"
    return field_type