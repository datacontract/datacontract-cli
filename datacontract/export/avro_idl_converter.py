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
class AvroField:
    name: str
    description: typing.Optional[str]

@dataclass
class AvroPrimitiveField(AvroField):
    type: typing.Union[AvroPrimitiveType, AvroLogicalType]

@dataclass
class AvroComplexField(AvroField):
    subfields: list[AvroField]

@dataclass
class AvroArrayField(AvroField):
    type: AvroField

@dataclass
class AvroModelType(AvroField):
    fields: list[AvroField]

@dataclass
class AvroIDLProtocol:
    name: typing.Optional[str]
    description: typing.Optional[str]
    model_types: list[AvroModelType]

avro_primitive_types = set(["string", "text", "varchar",
                            "float", "double", "int",
                            "integer", "long", "bigint",
                            "boolean", "timestamp_ntz",
                            "timestamp", "timestamp_tz",
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
        case "timestamp" | "timestamp_tz":
            result.type = AvroPrimitiveType.string
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

def to_avro_idl_type(field_name: str, field: Field) -> AvroField:
    if field.type in avro_primitive_types:
        return to_avro_primitive_logical_type(field_name, field)
    else:
        match field.type:
            case "array":
                return AvroArrayField(
                    field_name,
                    field.description,
                    to_avro_idl_type(field_name, field.items)
                )
            case "object" | "record" | "struct":
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


def generate_field_types(contract: DataContractSpecification) -> list[AvroField]:
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

def write_field_description(field: AvroField, indent: int, stream: typing.TextIO):
    if field.description:
        write_indent(indent, stream)
        stream.write(f"/** {field.description} */\n")

def write_field_type_definition(field: AvroField, indent: int, stream: typing.TextIO) -> str:
    match field:
        case AvroPrimitiveField(name, _, typ):
            return typ.value
        case AvroComplexField(name, _, subfields):
            write_field_description(field, indent, stream)
            write_indent(indent, stream)
            stream.write(f"record {name}_type {{\n")
            subfield_types = []
            for subfield in subfields:
                subfield_types.append(write_field_type_definition(subfield, indent + 1, stream))
            for (field, subfield_type) in zip(field.subfields, subfield_types):
                write_field_description(field, indent + 1, stream)
                write_indent(indent + 1, stream)
                stream.write(f"{subfield_type} {field.name};\n")
            write_indent(indent, stream)
            stream.write("}\n")
            return f"{name}_type"
        case AvroArrayField(name, _, item_type):
            subfield_type = write_field_type_definition(item_type, indent, stream)
            return f"array<{subfield_type}>"
        case _:
            raise RuntimeError("Unknown Avro field type {field}")

def write_field(field: AvroField,
                indent,
                stream: typing.TextIO):
    typename = write_field_type_definition(field, indent, stream)
    write_field_description(field, indent, stream)
    write_indent(indent, stream)
    stream.write(f"{typename} {field.name};\n")

def write_model_type(model: AvroModelType, stream: typing.TextIO):
    if model.description:
        write_indent(1, stream)
        stream.write(f"/** {model.description} */\n")
    write_indent(1, stream)
    stream.write(f"record {model.name} {{\n")
    for field in model.fields:
        write_field(field, 2, stream)
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
