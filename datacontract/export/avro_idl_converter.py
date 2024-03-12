from datacontract.model.data_contract_specification import DataContractSpecification, Field
from datacontract.lint.resolve import inline_definitions_into_data_contract
from dataclasses import dataclass
from enum import Enum
import typing
from io import StringIO

from datacontract.model.exceptions import DataContractException

class AvroPrimitiveType(Enum):
    int = "int"
    long = "long"
    string = "string"
    boolean = "boolean"
    float = "float"
    double = "double"
    null = "null"
    bytes = "bytes"

class AvroLogicalType(Enum):
    decimal = "decimal"
    date = "date"
    time_ms = "time_ms"
    timestamp_ms = "timestamp_ms"

@dataclass
class AvroPrimitiveField:
    name: str
    description: typing.Optional[str]
    type: typing.Union[AvroPrimitiveType, AvroLogicalType]

@dataclass
class AvroComplexField:
    name: str
    description: typing.Optional[str]
    subfields: list[typing.Union[AvroPrimitiveField, 'AvroComplexField']]

@dataclass
class AvroModelType:
    name: str
    description: typing.Optional[str]
    fields: list[typing.Union[AvroPrimitiveField, AvroComplexField]]

@dataclass
class AvroIDLProtocol:
    name: typing.Optional[str]
    description: typing.Optional[str]
    model_types: list[AvroModelType]

avro_primitive_types = set(["string", "text", "varchar",
                            "float", "double", "int",
                            "integer", "long", "bigint",
                            "boolean", "timestamp_ntz",
                            "date", "bytes",
                            "null"])

def to_avro_primitive_logical_type(field_name: str, field: Field) -> AvroPrimitiveField:
    result = AvroPrimitiveField(field_name, field.description, AvroPrimitiveType.string)
    match field.type:
        case "string" | "text" | "varchar":
            result.type = AvroPrimitiveType.string
        case "float":
            result.type = AvroPrimitiveType.float
        case "double":
            result.type = AvroPrimitiveType.double
        case "int" | "integer":
            result.type = AvroPrimitiveType.int
        case "long" | "bigint":
            result.type = AvroPrimitiveType.long
        case "boolean":
            result.type = AvroPrimitiveType.boolean
        case "timestamp_ntz":
            result.type = AvroLogicalType.timestamp_ms
        case "date":
            result.type = AvroLogicalType.date
        case "bytes":
            result.type = AvroPrimitiveType.bytes
        case "null":
            result.type = AvroPrimitiveType.null
        case _:
            raise DataContractException(
                type="general",
                name="avro-idl-export",
                model=field,
                reason="Unknown field type {field.type}",
                result="failed",
                message="Avro IDL type conversion failed."
            )
    return result

def to_avro_idl_type(field_name: str, field: Field) -> typing.Union[AvroPrimitiveField, AvroComplexField]:
    if field.type in avro_primitive_types:
        return to_avro_primitive_logical_type(field_name, field)
    else:
        match field.type:
            case "timestamp" | "timestamp_tz":
                raise DataContractException(
                    type="general",
                    name="avro-idl-export",
                    model=type,
                    reason="Avro IDL does not support timestamps with timezone.",
                    result="failed",
                    message="Avro IDL type conversion failed."
                )
            case "array":
                raise DataContractException(
                    type="general",
                    name="avro-idl-export",
                    model=type,
                    reason="Avro IDL export for arrays is not implemented.",
                    result="failed",
                    message="Avro IDL type conversion failed."
                )
            case "object" | "record":
                return AvroComplexField(
                    field_name,
                    field.description,
                    [to_avro_idl_type(field_name, field) for (field_name, field) in field.fields.items()]
                )
            case _:
                raise DataContractException(
                    type="general",
                    name="avro-idl-export",
                    model=type,
                    reason="Unknown Data Contract field type",
                    result="failed",
                    message="Avro IDL type conversion failed."
                )


def generate_field_types(contract: DataContractSpecification) -> list[typing.Union[AvroPrimitiveField, AvroComplexField]]:
    result = []
    for (_, model) in contract.models.items():
        for (field_name, field) in model.fields.items():
            result.append(to_avro_idl_type(field_name, field))
    return result

def generate_model_types(contract: DataContractSpecification) -> list[AvroModelType]:
    result = []
    for (model_name, model) in contract.models.items():
        result.append(AvroModelType(
            name=model_name,
            description=model.description,
            fields=generate_field_types(contract)
        ))
    return result

def model_name_to_identifier(model_name: str):
    return "".join([word.title() for word in  model_name.split()])

def contract_to_avro_idl_ir(contract: DataContractSpecification) -> AvroIDLProtocol:
    """Convert models into an intermediate representation for later serialization into Avro IDL.

      Each model is converted to a record containing a field for each model field.
      """
    inlined_contract = contract.model_copy()
    inline_definitions_into_data_contract(inlined_contract)
    protocol_name = (model_name_to_identifier(contract.info.title)
                     if contract.info and contract.info.title
                     else None)
    description = (contract.info.description if
                   contract.info and contract.info.description
                   else None)
    return AvroIDLProtocol(name=protocol_name,
                           description=description,
                           model_types=generate_model_types(inlined_contract))

def write_indent(indent: int, stream: typing.TextIO):
    stream.write("    " * indent)

def write_field_type(field: typing.Union[AvroPrimitiveField, AvroComplexField],
                     stream: typing.TextIO, indent=2):
    if field.description:
        write_indent(indent, stream)
        stream.write(f"/** {field.description} */\n")
    match field:
        case AvroPrimitiveField(name, _, type):
            write_indent(indent, stream)
            stream.write(f"{type.value} {name};\n")
        case AvroComplexField(name, _, subfields):
            write_indent(indent, stream)
            stream.write(f"record {name}_type {{\n")
            for subfield in subfields:
                write_field_type(subfield, stream, indent + 1)
            write_indent(indent, stream)
            stream.write("}\n")
            write_indent(indent, stream)
            stream.write(f"{name}_type {name};\n");

def write_model_type(model: AvroModelType, stream: typing.TextIO):
    if model.description:
        write_indent(1, stream)
        stream.write(f"/** {model.description} */\n")
    write_indent(1, stream)
    stream.write(f"record {model.name} {{\n")
    for field in model.fields:
        write_field_type(field, stream)
    write_indent(1, stream)
    stream.write("}\n")

def to_avro_idl(contract: DataContractSpecification) -> str:
    stream = StringIO()
    to_avro_idl_stream(contract, stream)
    return stream.getvalue()

def to_avro_idl_stream(contract: DataContractSpecification, stream: typing.TextIO):
    ir = contract_to_avro_idl_ir(contract)
    if ir.description:
        stream.write(f"/** {contract.info.description} */\n")
    stream.write(f"protocol {ir.name or 'Unnamed'} {{\n")
    for model_type in ir.model_types:
        write_model_type(model_type, stream)
    stream.write("}\n")
