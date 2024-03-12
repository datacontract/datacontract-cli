from datacontract.model.data_contract_specification import DataContractSpecification
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
class AvroFieldType:
    name: str
    description: typing.Optional[str]
    type: typing.Union[AvroPrimitiveType, AvroLogicalType]

@dataclass
class AvroModelType:
    name: str
    description: typing.Optional[str]
    fields: list[AvroFieldType]

@dataclass
class AvroIDLProtocol:
    name: str
    description: typing.Optional[str]
    model_types: list[AvroModelType]


def to_avro_idl_type(type: str) -> typing.Union[AvroPrimitiveType, AvroLogicalType]:
    match type:
        case "string" | "text" | "varchar":
            return AvroPrimitiveType.string
        case "float":
            return AvroPrimitiveType.float
        case "double":
            return AvroPrimitiveType.double
        case "int" | "integer":
            return AvroPrimitiveType.int
        case "long" | "bigint":
            return AvroPrimitiveType.long
        case "boolean":
            return AvroPrimitiveType.boolean
        case "timestamp" | "timestamp_tz":
            raise DataContractException(
                type="general",
                name="avro-idl-export",
                model=type,
                reason="Avro IDL does not support timestamps with timezone.",
                result="failed",
                message="Avro IDL type conversion failed."
            )
        case "timestamp_ntz":
            return AvroLogicalType.timestamp_ms
        case "date":
            return AvroLogicalType.date
        case "array":
            raise DataContractException(
                type="general",
                name="avro-idl-export",
                model=type,
                reason="Avro IDL export for arrays is not implemented.",
                result="failed",
                message="Avro IDL type conversion failed."
            )
        case "object":
            raise DataContractException(
                type="general",
                name="avro-idl-export",
                model=type,
                reason="Avro IDL export for objects is not implemented.",
                result="failed",
                message="Avro IDL type conversion failed."
            )
        case "record":
             raise DataContractException(
                 type="general",
                 name="avro-idl-export",
                 model=type,
                 reason="Avro IDL export for records is currently not implemented.",
                 result="failed",
                 message="Avro IDL type conversion failed."
             )
        case "bytes":
            return AvroPrimitiveType.bytes
        case "null":
            return AvroPrimitiveType.null
        case _:
            raise DataContractException(
                type="general",
                name="avro-idl-export",
                model=type,
                reason="Unknown Data Contract field type",
                result="failed",
                message="Avro IDL type conversion failed."
                )

def generate_field_types(contract: DataContractSpecification) -> list[AvroFieldType]:
    result = []
    for (_, model) in contract.models.items():
        for (field_name, field) in model.fields.items():
            result.append(AvroFieldType(
                name=field_name,
                description=field.description,
                type=to_avro_idl_type(field.type)
            ))
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

def model_to_avro_idl_ir(contract: DataContractSpecification) -> AvroIDLProtocol:
    """Convert models into an intermediate representation for later serialization into Avro IDL.

      Each model is converted to a record containing a field for each model field.
      """
    inlined_contract = contract.model_copy()
    inline_definitions_into_data_contract(inlined_contract)
    return AvroIDLProtocol(name=model_name_to_identifier(contract.info.title),
                           description=contract.info.description,
                           model_types=generate_model_types(inlined_contract))

def write_model_type(model: AvroModelType, stream: typing.TextIO):
    if model.description:
        stream.write(f"    /** {model.description} */\n")
    stream.write(f"    record {model.name} {{\n")
    for field in model.fields:
        if field.description:
            stream.write(f"        /** {field.description} */\n")
        stream.write(f"        {field.type.value} {field.name};\n")
    stream.write("    }\n")

def to_avro_idl(contract: DataContractSpecification) -> str:
    stream = StringIO()
    to_avro_idl_stream(contract, stream)
    return stream.getvalue()

def to_avro_idl_stream(contract: DataContractSpecification, stream: typing.TextIO):
    ir = model_to_avro_idl_ir(contract)
    if contract.info and contract.info.description:
        stream.write(f"/** {contract.info.description} */\n")
    stream.write(f"protocol {ir.name} {{\n")
    for model_type in ir.model_types:
        write_model_type(model_type, stream)
    stream.write("}\n")
