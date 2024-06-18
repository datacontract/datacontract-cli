from datacontract.model.data_contract_specification import DataContractSpecification
from datacontract.export.exporter import Exporter


class ProtoBufExporter(Exporter):
    def export(self, data_contract, model, server, sql_server_type, export_args) -> dict:
        return to_protobuf(data_contract)


def to_protobuf(data_contract_spec: DataContractSpecification):
    messages = ""
    for model_name, model in data_contract_spec.models.items():
        messages += to_protobuf_message(model_name, model.fields, model.description, 0)
        messages += "\n"

    result = f"""syntax = "proto3";

{messages}
"""

    return result


def _to_protobuf_message_name(model_name):
    return model_name[0].upper() + model_name[1:]


def to_protobuf_message(model_name, fields, description, indent_level: int = 0):
    result = ""

    if description is not None:
        result += f"""{indent(indent_level)}/* {description} */\n"""

    fields_protobuf = ""
    number = 1
    for field_name, field in fields.items():
        if field.type in ["object", "record", "struct"]:
            fields_protobuf += (
                "\n".join(
                    map(
                        lambda x: "  " + x,
                        to_protobuf_message(field_name, field.fields, field.description, indent_level + 1).splitlines(),
                    )
                )
                + "\n"
            )

        fields_protobuf += to_protobuf_field(field_name, field, field.description, number, 1) + "\n"
        number += 1
    result += f"message {_to_protobuf_message_name(model_name)} {{\n{fields_protobuf}}}\n"

    return result


def to_protobuf_field(field_name, field, description, number: int, indent_level: int = 0):
    optional = ""
    if not field.required:
        optional = "optional "

    result = ""

    if description is not None:
        result += f"""{indent(indent_level)}/* {description} */\n"""

    result += f"{indent(indent_level)}{optional}{_convert_type(field_name, field)} {field_name} = {number};"

    return result


def indent(indent_level):
    return "  " * indent_level


def _convert_type(field_name, field) -> None | str:
    type = field.type
    if type is None:
        return None
    if type.lower() in ["string", "varchar", "text"]:
        return "string"
    if type.lower() in ["timestamp", "timestamp_tz"]:
        return "string"
    if type.lower() in ["timestamp_ntz"]:
        return "string"
    if type.lower() in ["date"]:
        return "string"
    if type.lower() in ["time"]:
        return "string"
    if type.lower() in ["number", "decimal", "numeric"]:
        return "double"
    if type.lower() in ["float", "double"]:
        return type.lower()
    if type.lower() in ["integer", "int"]:
        return "int32"
    if type.lower() in ["long", "bigint"]:
        return "int64"
    if type.lower() in ["boolean"]:
        return "bool"
    if type.lower() in ["bytes"]:
        return "bytes"
    if type.lower() in ["object", "record", "struct"]:
        return _to_protobuf_message_name(field_name)
    if type.lower() in ["array"]:
        # TODO spec is missing arrays
        return "repeated string"
    return None
