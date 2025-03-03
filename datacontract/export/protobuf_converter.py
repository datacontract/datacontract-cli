from datacontract.export.exporter import Exporter
from datacontract.model.data_contract_specification import DataContractSpecification


class ProtoBufExporter(Exporter):
    def export(self, data_contract, model, server, sql_server_type, export_args) -> dict:
        # Return the generated proto file as a dict with a key (e.g. "proto")
        return {"proto": to_protobuf(data_contract)}


def to_protobuf(data_contract_spec: DataContractSpecification) -> str:
    """
    Generates a Protobuf file from the data contract specification.
    It scans all models for enum fields and collects their definitions.
    """
    messages = ""
    enum_definitions = {}

    # Iterate over all models to generate messages and collect enum definitions.
    for model_name, model in data_contract_spec.models.items():
        for field_name, field in model.fields.items():
            if field.type and field.type.lower() == "enum":
                # Determine enum name: use field.enum_name if provided,
                # otherwise generate a name from the field name.
                enum_name = getattr(field, "enum_name", None) or _to_protobuf_message_name(field_name)
                # If the field has enum_values defined, add to enum_definitions.
                enum_values = getattr(field, "enum_values", None)
                if enum_values:
                    # Only add if we haven't already added this enum.
                    if enum_name not in enum_definitions:
                        enum_definitions[enum_name] = enum_values

        messages += to_protobuf_message(model_name, model.fields, model.description, 0)
        messages += "\n"

    # Build the file header with the syntax and package declarations.
    header = 'syntax = "proto3";\n\n'
    package = getattr(data_contract_spec, "package", "example")
    header += f"package {package};\n\n"

    # Append enum definitions if any were found.
    for enum_name, enum_values in enum_definitions.items():
        header += f"// Enum for {enum_name}\n"
        header += f"enum {enum_name} {{\n"
        header += "  UNKNOWN = 0;\n"
        for idx, value in enumerate(enum_values, start=1):
            # Normalize enum constant names to uppercase with underscores.
            enum_const = value.upper().replace(" ", "_")
            header += f"  {enum_const} = {idx};\n"
        header += "}\n\n"

    return header + messages


def _to_protobuf_message_name(name: str) -> str:
    """
    Returns a valid Protobuf message/enum name by capitalizing the first letter.
    """
    return name[0].upper() + name[1:] if name else name


def to_protobuf_message(model_name: str, fields: dict, description: str, indent_level: int = 0) -> str:
    """
    Generates a Protobuf message definition from the model's fields.
    Handles nested messages for complex types.
    """
    result = ""
    if description:
        result += f"{indent(indent_level)}// {description}\n"

    result += f"message {_to_protobuf_message_name(model_name)} {{\n"
    number = 1
    for field_name, field in fields.items():
        # If the field is a nested object, record, or struct, generate a nested message.
        if field.type and field.type.lower() in ["object", "record", "struct"]:
            nested_message = to_protobuf_message(field_name, field.fields, field.description, indent_level + 1)
            result += nested_message + "\n"

        result += to_protobuf_field(field_name, field, field.description, number, indent_level + 1) + "\n"
        number += 1

    result += f"{indent(indent_level)}}}\n"
    return result


def to_protobuf_field(field_name: str, field, description: str, number: int, indent_level: int = 0) -> str:
    """
    Generates a field definition within a Protobuf message.
    In proto3, fields are optional by default.
    """
    result = ""
    if description:
        result += f"{indent(indent_level)}// {description}\n"
    # Map the field type using the _convert_type helper.
    result += f"{indent(indent_level)}{_convert_type(field_name, field)} {field_name} = {number};"
    return result


def indent(indent_level: int) -> str:
    return "  " * indent_level


def _convert_type(field_name: str, field) -> str:
    """
    Converts a field's type (as specified in the data contract) to a Protobuf type.
    Supports standard types and generic enums.
    """
    if field.type is None:
        return "string"

    lower_type = field.type.lower()
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
        # For complex types, use the field name as the message name.
        return _to_protobuf_message_name(field_name)
    if lower_type == "array":
        # Generic handling: defaults to repeated string.
        # (This could be improved to handle arrays of a specific type.)
        return "repeated string"
    if lower_type == "enum":
        # For enum, return the enum name (either provided via attribute or derived from field name).
        return getattr(field, "enum_name", None) or _to_protobuf_message_name(field_name)
    # Fallback: default any unrecognized type to "string".
    return "string"
