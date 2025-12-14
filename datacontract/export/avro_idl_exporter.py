import typing
from dataclasses import dataclass
from enum import Enum
from io import StringIO
from typing import Optional

from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, SchemaProperty

from datacontract.export.exporter import Exporter
from datacontract.lint.resolve import inline_definitions_into_data_contract
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


# ODCS logical types and physical types that map to Avro primitive types
avro_primitive_logical_types = {"string", "integer", "number", "boolean", "date"}
avro_primitive_physical_types = {
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
}


class AvroIdlExporter(Exporter):
    def export(self, data_contract, schema_name, server, sql_server_type, export_args) -> dict:
        return to_avro_idl(data_contract)


def to_avro_idl(contract: OpenDataContractStandard) -> str:
    """Serialize the provided data contract specification into an Avro IDL string.

    The data contract will be serialized as a protocol, with one record type
    for each contained model. Model fields are mapped one-to-one to Avro IDL
    record fields.
    """
    stream = StringIO()
    to_avro_idl_stream(contract, stream)
    return stream.getvalue()


def to_avro_idl_stream(contract: OpenDataContractStandard, stream: typing.TextIO):
    """Serialize the provided data contract specification into Avro IDL."""
    ir = _contract_to_avro_idl_ir(contract)
    if ir.description:
        stream.write(f"/** {ir.description} */\n")
    stream.write(f"protocol {ir.name or 'Unnamed'} {{\n")
    for model_type in ir.model_types:
        _write_model_type(model_type, stream)
    stream.write("}\n")


def _get_type(prop: SchemaProperty) -> Optional[str]:
    """Get the logical type from a schema property."""
    return prop.logicalType


def _is_primitive_type(prop: SchemaProperty) -> bool:
    """Check if a property is a primitive type."""
    logical_type = _get_type(prop)
    physical_type = prop.physicalType

    if logical_type in avro_primitive_logical_types:
        return True
    if physical_type and physical_type.lower() in avro_primitive_physical_types:
        return True
    return False


def _to_avro_primitive_logical_type(field_name: str, prop: SchemaProperty) -> AvroPrimitiveField:
    result = AvroPrimitiveField(field_name, prop.required or False, prop.description, AvroPrimitiveType.string)
    logical_type = _get_type(prop)
    physical_type = prop.physicalType.lower() if prop.physicalType else None

    # Check physical type first for more specific mapping
    if physical_type:
        if physical_type in ["string", "text", "varchar"]:
            result.type = AvroPrimitiveType.string
            return result
        elif physical_type == "float":
            result.type = AvroPrimitiveType.float
            return result
        elif physical_type == "double":
            result.type = AvroPrimitiveType.double
            return result
        elif physical_type in ["int", "integer"]:
            result.type = AvroPrimitiveType.int
            return result
        elif physical_type in ["long", "bigint"]:
            result.type = AvroPrimitiveType.long
            return result
        elif physical_type == "boolean":
            result.type = AvroPrimitiveType.boolean
            return result
        elif physical_type in ["timestamp", "timestamp_tz"]:
            result.type = AvroPrimitiveType.string
            return result
        elif physical_type == "timestamp_ntz":
            result.type = AvroLogicalType.timestamp_ms
            return result
        elif physical_type == "date":
            result.type = AvroLogicalType.date
            return result
        elif physical_type == "bytes":
            result.type = AvroPrimitiveType.bytes
            return result
        elif physical_type == "null":
            result.type = AvroPrimitiveType.null
            return result

    # Fall back to logical type
    match logical_type:
        case "string":
            result.type = AvroPrimitiveType.string
        case "number":
            result.type = AvroPrimitiveType.double
        case "integer":
            result.type = AvroPrimitiveType.long
        case "boolean":
            result.type = AvroPrimitiveType.boolean
        case "date":
            result.type = AvroLogicalType.date
        case _:
            raise DataContractException(
                type="general",
                name="avro-idl-export",
                model=prop,
                reason=f"Unknown field type {logical_type}",
                result="failed",
                message="Avro IDL type conversion failed.",
            )
    return result


def _to_avro_idl_type(field_name: str, prop: SchemaProperty) -> AvroField:
    if _is_primitive_type(prop):
        return _to_avro_primitive_logical_type(field_name, prop)
    else:
        logical_type = _get_type(prop)
        physical_type = prop.physicalType.lower() if prop.physicalType else None

        if logical_type == "array":
            if prop.items:
                return AvroArrayField(
                    field_name, prop.required or False, prop.description, _to_avro_idl_type(field_name, prop.items)
                )
            else:
                raise DataContractException(
                    type="general",
                    name="avro-idl-export",
                    model=prop,
                    reason="Array type requires items",
                    result="failed",
                    message="Avro IDL type conversion failed.",
                )
        elif logical_type == "object" or physical_type in ["record", "struct"]:
            if prop.properties:
                return AvroComplexField(
                    field_name,
                    prop.required or False,
                    prop.description,
                    [_to_avro_idl_type(p.name, p) for p in prop.properties],
                )
            else:
                raise DataContractException(
                    type="general",
                    name="avro-idl-export",
                    model=prop,
                    reason="Object type requires properties",
                    result="failed",
                    message="Avro IDL type conversion failed.",
                )
        else:
            raise DataContractException(
                type="general",
                name="avro-idl-export",
                model=prop,
                reason=f"Unknown Data Contract field type: {logical_type}",
                result="failed",
                message="Avro IDL type conversion failed.",
            )


def _generate_field_types(schema_obj: SchemaObject) -> list[AvroField]:
    result = []
    if schema_obj.properties:
        for prop in schema_obj.properties:
            result.append(_to_avro_idl_type(prop.name, prop))
    return result


def generate_model_types(contract: OpenDataContractStandard) -> list[AvroModelType]:
    result = []
    if contract.schema_:
        for schema_obj in contract.schema_:
            result.append(
                AvroModelType(
                    name=schema_obj.name, description=schema_obj.description, fields=_generate_field_types(schema_obj)
                )
            )
    return result


def _model_name_to_identifier(model_name: str):
    return "".join([word.title() for word in model_name.split()])


def _contract_to_avro_idl_ir(contract: OpenDataContractStandard) -> AvroIDLProtocol:
    """Convert models into an intermediate representation for later serialization into Avro IDL.

    Each model is converted to a record containing a field for each model field.
    """
    inlined_contract = contract.model_copy()
    inline_definitions_into_data_contract(inlined_contract)
    protocol_name = _model_name_to_identifier(contract.name) if contract.name else None
    description = contract.description.purpose if contract.description and contract.description.purpose else None
    return AvroIDLProtocol(name=protocol_name, description=description, model_types=generate_model_types(inlined_contract))


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
            for subfield, subfield_type in zip(field.subfields, subfield_types):
                _write_field_description(subfield, indent + 1, stream)
                _write_indent(indent + 1, stream)
                stream.write(f"{subfield_type} {subfield.name};\n")
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
            raise RuntimeError(f"Unknown Avro field type {field}")


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
