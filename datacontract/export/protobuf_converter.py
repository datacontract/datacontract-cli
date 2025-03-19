from datacontract.export.exporter import Exporter
from datacontract.model.data_contract_specification import DataContractSpecification


class ProtoBufExporter(Exporter):
    def export(self, data_contract, model, server, sql_server_type, export_args) -> dict:
        # Returns a dict containing the protobuf representation.
        proto = to_protobuf(data_contract)
        return {"protobuf": proto}


def to_protobuf(data_contract_spec: DataContractSpecification) -> str:
    """
    Generates a Protobuf file from the data contract specification.
    Scans all models for enum fields (even if the type is "string") by checking for a "values" property.
    """
    messages = ""
    enum_definitions = {}

    # Iterate over all models to generate messages and collect enum definitions.
    for model_name, model in data_contract_spec.models.items():
        for field_name, field in model.fields.items():
            # If the field has enum values, collect them.
            if _is_enum_field(field):
                enum_name = _get_enum_name(field, field_name)
                enum_values = _get_enum_values(field)
                if enum_values and enum_name not in enum_definitions:
                    enum_definitions[enum_name] = enum_values

        messages += to_protobuf_message(model_name, model.fields, getattr(model, "description", ""), 0)
        messages += "\n"

    # Build header with syntax and package declarations.
    header = 'syntax = "proto3";\n\n'
    package = getattr(data_contract_spec, "package", "example")
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


def _is_enum_field(field) -> bool:
    """
    Returns True if the field (dict or object) has a non-empty "values" property.
    """
    if isinstance(field, dict):
        return bool(field.get("values"))
    return bool(getattr(field, "values", None))


def _get_enum_name(field, field_name: str) -> str:
    """
    Returns the enum name either from the field's "enum_name" or derived from the field name.
    """
    if isinstance(field, dict):
        return field.get("enum_name", _to_protobuf_message_name(field_name))
    return getattr(field, "enum_name", None) or _to_protobuf_message_name(field_name)


def _get_enum_values(field) -> dict:
    """
    Returns the enum values from the field.
    If the values are not a dictionary, attempts to extract enum attributes.
    """
    if isinstance(field, dict):
        values = field.get("values", {})
    else:
        values = getattr(field, "values", {})

    if not isinstance(values, dict):
        # If values is a BaseModel (or similar) with a .dict() method, use it.
        if hasattr(values, "dict") and callable(values.dict):
            values_dict = values.dict()
            return {k: v for k, v in values_dict.items() if k.isupper() and isinstance(v, int)}
        else:
            # Otherwise, iterate over attributes that look like enums.
            return {
                key: getattr(values, key)
                for key in dir(values)
                if key.isupper() and isinstance(getattr(values, key), int)
            }
    return values


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
        # For nested objects, generate a nested message.
        field_type = _get_field_type(field)
        if field_type in ["object", "record", "struct"]:
            nested_desc = field.get("description", "") if isinstance(field, dict) else getattr(field, "description", "")
            nested_fields = field.get("fields", {}) if isinstance(field, dict) else field.fields
            nested_message = to_protobuf_message(field_name, nested_fields, nested_desc, indent_level + 1)
            result += nested_message + "\n"

        field_desc = field.get("description", "") if isinstance(field, dict) else getattr(field, "description", "")
        result += to_protobuf_field(field_name, field, field_desc, number, indent_level + 1) + "\n"
        number += 1

    result += f"{indent(indent_level)}}}\n"
    return result


def to_protobuf_field(field_name: str, field, description: str, number: int, indent_level: int = 0) -> str:
    """
    Generates a field definition within a Protobuf message.
    """
    result = ""
    if description:
        result += f"{indent(indent_level)}// {description}\n"
    result += f"{indent(indent_level)}{_convert_type(field_name, field)} {field_name} = {number};"
    return result


def indent(indent_level: int) -> str:
    return "  " * indent_level


def _get_field_type(field) -> str:
    """
    Retrieves the field type from the field definition.
    """
    if isinstance(field, dict):
        return field.get("type", "").lower()
    return getattr(field, "type", "").lower()


def _convert_type(field_name: str, field) -> str:
    """
    Converts a field's type (from the data contract) to a Protobuf type.
    Prioritizes enum conversion if a non-empty "values" property exists.
    """
    # For debugging purposes
    print("Converting field:", field_name)
    # If the field should be treated as an enum, return its enum name.
    if _is_enum_field(field):
        return _get_enum_name(field, field_name)

    lower_type = _get_field_type(field)
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
        return _to_protobuf_message_name(field_name)
    if lower_type == "array":
        # Handle array types. Check for an "items" property.
        items = field.get("items") if isinstance(field, dict) else getattr(field, "items", None)
        if items and isinstance(items, dict) and items.get("type"):
            item_type = items.get("type", "").lower()
            if item_type in ["object", "record", "struct"]:
                # Singularize the field name (a simple approach).
                singular = field_name[:-1] if field_name.endswith("s") else field_name
                return "repeated " + _to_protobuf_message_name(singular)
            else:
                return "repeated " + _convert_type(field_name, items)
        else:
            return "repeated string"
    # Fallback for unrecognized types.
    return "string"
