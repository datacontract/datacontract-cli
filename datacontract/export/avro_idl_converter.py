import typing
from dataclasses import dataclass
from enum import Enum
from io import StringIO

from datacontract.lint.resolve import inline_definitions_into_data_contract
from datacontract.model.data_contract_specification import DataContractSpecification, Field
from datacontract.model.exceptions import DataContractException

from datacontract.export.exporter import Exporter


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
    required: bool
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
class AvroModelType:
    name: str
    description: typing.Optional[str]
    fields: list[AvroField]


@dataclass
class AvroIDLProtocol:
    name: typing.Optional[str]
    description: typing.Optional[str]
    model_types: list[AvroModelType]


avro_primitive_types = set(
    [
        "string",
        "text",
        "varchar",
        "float",
        "double",
        "int",
        "integer",
        "long",
        "bigint",
        "boolean",
        "timestamp_ntz",
        "timestamp",
        "timestamp_tz",
        "date",
        "bytes",
        "null",
    ]
)


class AvroIdlExporter(Exporter):
    def export(self, data_contract, model, server, sql_server_type, export_args) -> dict:
        return to_avro_idl(data_contract)


def to_avro_idl(contract: DataContractSpecification) -> str:
    """Serialize the provided data contract specification into an Avro IDL string.

    The data contract will be serialized as a protocol, with one record type
    for each contained model. Model fields are mapped one-to-one to Avro IDL
    record fields.
    """
    stream = StringIO()
    to_avro_idl_stream(contract, stream)
    return stream.getvalue()


def to_avro_idl_stream(contract: DataContractSpecification, stream: typing.TextIO):
    """Serialize the provided data contract specification into Avro IDL."""
    ir = _contract_to_avro_idl_ir(contract)
    if ir.description:
        stream.write(f"/** {contract.info.description} */\n")
    stream.write(f"protocol {ir.name or 'Unnamed'} {{\n")
    for model_type in ir.model_types:
        _write_model_type(model_type, stream)
    stream.write("}\n")


def _to_avro_primitive_logical_type(field_name: str, field: Field) -> AvroPrimitiveField:
    result = AvroPrimitiveField(field_name, field.required, field.description, AvroPrimitiveType.string)
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
                message="Avro IDL type conversion failed.",
            )
    return result


def _to_avro_idl_type(field_name: str, field: Field) -> AvroField:
    if field.type in avro_primitive_types:
        return _to_avro_primitive_logical_type(field_name, field)
    else:
        match field.type:
            case "array":
                return AvroArrayField(
                    field_name, field.required, field.description, _to_avro_idl_type(field_name, field.items)
                )
            case "object" | "record" | "struct":
                return AvroComplexField(
                    field_name,
                    field.required,
                    field.description,
                    [_to_avro_idl_type(field_name, field) for (field_name, field) in field.fields.items()],
                )
            case _:
                raise DataContractException(
                    type="general",
                    name="avro-idl-export",
                    model=type,
                    reason="Unknown Data Contract field type",
                    result="failed",
                    message="Avro IDL type conversion failed.",
                )


def _generate_field_types(contract: DataContractSpecification) -> list[AvroField]:
    result = []
    for _, model in contract.models.items():
        for field_name, field in model.fields.items():
            result.append(_to_avro_idl_type(field_name, field))
    return result


def generate_model_types(contract: DataContractSpecification) -> list[AvroModelType]:
    result = []
    for model_name, model in contract.models.items():
        result.append(
            AvroModelType(name=model_name, description=model.description, fields=_generate_field_types(contract))
        )
    return result


def _model_name_to_identifier(model_name: str):
    return "".join([word.title() for word in model_name.split()])


def _contract_to_avro_idl_ir(contract: DataContractSpecification) -> AvroIDLProtocol:
    """Convert models into an intermediate representation for later serialization into Avro IDL.

    Each model is converted to a record containing a field for each model field.
    """
    inlined_contract = contract.model_copy()
    inline_definitions_into_data_contract(inlined_contract)
    protocol_name = _model_name_to_identifier(contract.info.title) if contract.info and contract.info.title else None
    description = contract.info.description if contract.info and contract.info.description else None
    return AvroIDLProtocol(
        name=protocol_name, description=description, model_types=generate_model_types(inlined_contract)
    )


def _write_indent(indent: int, stream: typing.TextIO):
    stream.write("    " * indent)


def _write_field_description(field: AvroField, indent: int, stream: typing.TextIO):
    if field.description:
        _write_indent(indent, stream)
        stream.write(f"/** {field.description} */\n")


def _write_field_type_definition(field: AvroField, indent: int, stream: typing.TextIO) -> str:
    # Write any extra information (such as record type definition) and return
    # the name of the generated type. Writes descriptions only for record
    # types. This leads to record types being described twice, once on the
    # record definition, and once on use. The alternative (detect when the
    # complex field type is not used in an array or another complex type) is
    # significantly more complex to implement.
    match field:
        case AvroPrimitiveField(name, required, _, typ) if required is True:
            return typ.value
        case AvroPrimitiveField(name, required, _, typ):
            return typ.value + "?"
        case AvroComplexField(name, required, _, subfields):
            _write_field_description(field, indent, stream)
            _write_indent(indent, stream)
            stream.write(f"record {name}_type {{\n")
            subfield_types = []
            # Recursively define records for all subfields if necessary
            for subfield in subfields:
                subfield_types.append(_write_field_type_definition(subfield, indent + 1, stream))
            # Reference all defined record types.
            for field, subfield_type in zip(field.subfields, subfield_types):
                _write_field_description(field, indent + 1, stream)
                _write_indent(indent + 1, stream)
                stream.write(f"{subfield_type} {field.name};\n")
            _write_indent(indent, stream)
            stream.write("}\n")
            if required is True:
                return f"{name}_type"
            else:
                return f"{name}_type?"
        case AvroArrayField(name, required, _, item_type):
            subfield_type = _write_field_type_definition(item_type, indent, stream)
            if required is True:
                return f"array<{subfield_type}>"
            else:
                return f"array<{subfield_type}>?"
        case _:
            raise RuntimeError("Unknown Avro field type {field}")


def _write_field(field: AvroField, indent, stream: typing.TextIO):
    # Start of recursion.
    typename = _write_field_type_definition(field, indent, stream)
    _write_field_description(field, indent, stream)
    _write_indent(indent, stream)
    stream.write(f"{typename} {field.name};\n")


def _write_model_type(model: AvroModelType, stream: typing.TextIO):
    # Called once for each model
    if model.description:
        _write_indent(1, stream)
        stream.write(f"/** {model.description} */\n")
    _write_indent(1, stream)
    stream.write(f"record {model.name} {{\n")
    # Called for each model field
    for field in model.fields:
        _write_field(field, 2, stream)
    _write_indent(1, stream)
    stream.write("}\n")
