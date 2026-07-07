"""Import `.proto` files into an ODCS data contract.

Uses the pure-Python `proto-schema-parser` (no `protoc` system binary, no C
extension). Imports are resolved transitively by reading `import` statements and
parsing each referenced file, then message/enum type references are linked across
all parsed files by their simple (last-segment) name.
"""

import os
import re
from typing import Dict, List

from open_data_contract_standard.model import OpenDataContractStandard, SchemaProperty
from proto_schema_parser import ast as proto_ast
from proto_schema_parser.parser import Parser

from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import (
    create_odcs,
    create_property,
    create_schema_object,
)
from datacontract.model.exceptions import DataContractException

# Proto scalar type name -> protobuf field-type number (FieldDescriptorProto.Type).
# Kept so the emitted `physicalType` matches the previous protoc-based importer.
_PROTOBUF_TYPE_NUMBER = {
    "double": 1,
    "float": 2,
    "int64": 3,
    "uint64": 4,
    "int32": 5,
    "fixed64": 6,
    "fixed32": 7,
    "bool": 8,
    "string": 9,
    "bytes": 12,
    "uint32": 13,
    "sfixed32": 15,
    "sfixed64": 16,
    "sint32": 17,
    "sint64": 18,
}


def map_type_from_protobuf(field_type: int) -> str:
    """Map a protobuf field-type number to an ODCS logical type."""
    protobuf_type_mapping = {
        1: "number",  # double
        2: "number",  # float
        3: "integer",  # int64
        4: "integer",  # uint64
        5: "integer",  # int32
        6: "string",  # fixed64
        7: "string",  # fixed32
        8: "boolean",  # bool
        9: "string",  # string
        12: "array",  # bytes
        13: "integer",  # uint32
        15: "integer",  # sfixed32
        16: "integer",  # sfixed64
        17: "integer",  # sint32
        18: "integer",  # sint64
    }
    return protobuf_type_mapping.get(field_type, "string")


def parse_imports_raw(proto_file: str) -> list:
    """Return the raw import paths declared in a `.proto` file."""
    try:
        with open(proto_file, "r") as f:
            content = f.read()
    except Exception as e:
        raise DataContractException(
            type="file",
            name="Parse proto imports",
            reason=f"Failed to read proto file: {proto_file}",
            engine="datacontract",
            original_exception=e,
        )
    return re.findall(r'import\s+"(.+?)";', content)


def _parse_proto(proto_file: str) -> proto_ast.File:
    try:
        with open(proto_file, "r") as f:
            return Parser().parse(f.read())
    except Exception as e:
        raise DataContractException(
            type="schema",
            name="Parse proto file",
            reason=f"Failed to parse proto file: {proto_file}",
            engine="datacontract",
            original_exception=e,
        )


def _resolve_proto_files(sources: list, proto_root: str) -> List[str]:
    """Resolve the source files plus all transitively imported `.proto` files."""
    seen: List[str] = []
    queue = list(sources)
    while queue:
        proto = queue.pop(0)
        if proto in seen:
            continue
        seen.append(proto)
        proto_dir = os.path.dirname(proto)
        for imp in parse_imports_raw(proto):
            resolved = os.path.join(proto_dir, imp)
            if not os.path.exists(resolved):
                resolved = os.path.join(proto_root, imp)
            if os.path.exists(resolved) and resolved not in seen:
                queue.append(resolved)
    return seen


def _register_types(elements, messages: Dict[str, proto_ast.Message], enums: Dict[str, dict]) -> None:
    """Index messages and enums by simple name, recursing into nested definitions."""
    for el in elements:
        if isinstance(el, proto_ast.Message):
            messages.setdefault(el.name, el)
            _register_types(el.elements, messages, enums)
        elif isinstance(el, proto_ast.Enum):
            enums.setdefault(
                el.name,
                {v.name: v.number for v in el.elements if isinstance(v, proto_ast.EnumValue)},
            )


def _iter_fields(message: proto_ast.Message):
    """Yield the fields of a message, flattening any `oneof` groups."""
    for el in message.elements:
        if isinstance(el, proto_ast.Field):
            yield el
        elif isinstance(el, proto_ast.OneOf):
            for inner in el.elements:
                if isinstance(inner, proto_ast.Field):
                    yield inner


def _message_properties(
    message: proto_ast.Message,
    messages: Dict[str, proto_ast.Message],
    enums: Dict[str, dict],
) -> List[SchemaProperty]:
    return [_convert_field(field, messages, enums) for field in _iter_fields(message)]


def _convert_field(field, messages: Dict[str, proto_ast.Message], enums: Dict[str, dict]) -> SchemaProperty:
    """Convert a parsed protobuf field into an ODCS SchemaProperty."""
    simple_type = field.type.split(".")[-1]
    repeated = field.cardinality == proto_ast.FieldCardinality.REPEATED
    required = field.cardinality == proto_ast.FieldCardinality.REQUIRED

    if simple_type in messages:
        nested_properties = _message_properties(messages[simple_type], messages, enums)
        if repeated:
            items_prop = create_property(
                name="items",
                logical_type="object",
                physical_type="message",
                properties=nested_properties,
            )
            return create_property(
                name=field.name,
                logical_type="array",
                physical_type="repeated message",
                description=f"List of {simple_type}",
                items=items_prop,
            )
        return create_property(
            name=field.name,
            logical_type="object",
            physical_type="message",
            description=f"Nested object of {simple_type}",
            properties=nested_properties,
        )

    if simple_type in enums:
        enum_values = enums[simple_type]
        return create_property(
            name=field.name,
            logical_type="string",
            physical_type="enum",
            description=f"Enum field {field.name}",
            required=required,
            custom_properties={"enumValues": enum_values} if enum_values else None,
        )

    # Scalar field. Emit the protobuf type number as physicalType, matching the
    # previous protoc-based importer; repeated scalars are not expanded to arrays.
    type_number = _PROTOBUF_TYPE_NUMBER.get(simple_type)
    return create_property(
        name=field.name,
        logical_type=map_type_from_protobuf(type_number) if type_number is not None else "string",
        physical_type=str(type_number) if type_number is not None else simple_type,
        description=f"Field {field.name}",
        required=required,
    )


def import_protobuf(sources: list, import_args: dict = None) -> OpenDataContractStandard:
    """Import protobuf files and generate an ODCS data contract."""
    proto_root = os.path.dirname(os.path.abspath(sources[0])) if sources else ""

    all_proto_files = _resolve_proto_files(sources, proto_root)

    parsed: Dict[str, proto_ast.File] = {proto: _parse_proto(proto) for proto in all_proto_files}

    messages: Dict[str, proto_ast.Message] = {}
    enums: Dict[str, dict] = {}
    for file_ast in parsed.values():
        _register_types(file_ast.file_elements, messages, enums)

    odcs = create_odcs()
    odcs.schema_ = []

    for source in sources:
        file_ast = parsed.get(source)
        if file_ast is None:
            continue
        for element in file_ast.file_elements:
            if isinstance(element, proto_ast.Message):
                schema_obj = create_schema_object(
                    name=element.name,
                    physical_type="message",
                    description=f"Details of {element.name}.",
                    properties=_message_properties(element, messages, enums),
                )
                odcs.schema_.append(schema_obj)

    return odcs


class ProtoBufImporter(Importer):
    def __init__(self, name):
        self.name = name

    def import_source(
        self,
        source: str,
        import_args: dict = None,
    ) -> OpenDataContractStandard:
        """Import a protobuf file into an ODCS data contract."""
        return import_protobuf([source], import_args)
