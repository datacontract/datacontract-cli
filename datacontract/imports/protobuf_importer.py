import os
import re
import tempfile
from typing import List

from google.protobuf import descriptor_pb2
from grpc_tools import protoc
from open_data_contract_standard.model import OpenDataContractStandard, SchemaProperty

from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import (
    create_odcs,
    create_property,
    create_schema_object,
)
from datacontract.model.exceptions import DataContractException


def map_type_from_protobuf(field_type: int) -> str:
    """Map protobuf field type to ODCS logical type."""
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
    """Parse import statements from a .proto file and return the raw import paths."""
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


def compile_proto_to_binary(proto_files: list, output_file: str, proto_root: str = None):
    """Compile the provided proto files into a single descriptor set."""
    if proto_root:
        proto_dirs = {proto_root}
    else:
        proto_dirs = set(os.path.dirname(os.path.abspath(proto)) for proto in proto_files)
    proto_paths = [f"--proto_path={d}" for d in proto_dirs]

    abs_proto_files = [os.path.abspath(proto) for proto in proto_files]

    args = [""] + proto_paths + [f"--descriptor_set_out={output_file}"] + abs_proto_files
    ret = protoc.main(args)
    if ret != 0:
        raise DataContractException(
            type="schema",
            name="Compile proto files",
            reason=f"grpc_tools.protoc failed with exit code {ret}",
            engine="datacontract",
            original_exception=None,
        )


def extract_enum_values_from_fds(fds: descriptor_pb2.FileDescriptorSet, enum_name: str) -> dict:
    """Search the FileDescriptorSet for an enum definition."""
    for file_descriptor in fds.file:
        for enum in file_descriptor.enum_type:
            if enum.name == enum_name:
                return {value.name: value.number for value in enum.value}
        for message in file_descriptor.message_type:
            for enum in message.enum_type:
                if enum.name == enum_name:
                    return {value.name: value.number for value in enum.value}
    return {}


def extract_message_fields_to_properties(
    fds: descriptor_pb2.FileDescriptorSet, message_name: str
) -> List[SchemaProperty]:
    """Extract message fields from a FileDescriptorSet as ODCS properties."""
    for file_descriptor in fds.file:
        for msg in file_descriptor.message_type:
            if msg.name == message_name:
                properties = []
                for field in msg.field:
                    prop = convert_proto_field_to_property(fds, field)
                    properties.append(prop)
                return properties
    return []


def convert_proto_field_to_property(fds: descriptor_pb2.FileDescriptorSet, field) -> SchemaProperty:
    """Convert a protobuf field to an ODCS SchemaProperty."""
    if field.type == 11:  # TYPE_MESSAGE
        nested_msg_name = field.type_name.split(".")[-1]
        nested_properties = extract_message_fields_to_properties(fds, nested_msg_name)
        if field.label == 3:  # repeated field
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
                description=f"List of {nested_msg_name}",
                items=items_prop,
            )
        else:
            return create_property(
                name=field.name,
                logical_type="object",
                physical_type="message",
                description=f"Nested object of {nested_msg_name}",
                properties=nested_properties,
            )
    elif field.type == 14:  # TYPE_ENUM
        enum_name = field.type_name.split(".")[-1]
        enum_values = extract_enum_values_from_fds(fds, enum_name)
        return create_property(
            name=field.name,
            logical_type="string",
            physical_type="enum",
            description=f"Enum field {field.name}",
            required=field.label == 2,
            custom_properties={"enumValues": enum_values} if enum_values else None,
        )
    else:
        return create_property(
            name=field.name,
            logical_type=map_type_from_protobuf(field.type),
            physical_type=str(field.type),
            description=f"Field {field.name}",
            required=field.label == 2,
        )


def import_protobuf(sources: list, import_args: dict = None) -> OpenDataContractStandard:
    """Import protobuf files and generate an ODCS data contract."""
    proto_root = os.path.dirname(os.path.abspath(sources[0])) if sources else ""

    proto_files_set = set()
    queue = list(sources)
    while queue:
        proto = queue.pop(0)
        if proto not in proto_files_set:
            proto_files_set.add(proto)
            proto_dir = os.path.dirname(proto)
            for imp in parse_imports_raw(proto):
                resolved = os.path.join(proto_dir, imp)
                if not os.path.exists(resolved):
                    resolved = os.path.join(proto_root, imp)
                if os.path.exists(resolved) and resolved not in proto_files_set:
                    queue.append(resolved)
    all_proto_files = list(proto_files_set)

    temp_descriptor = tempfile.NamedTemporaryFile(suffix=".pb", delete=False)
    descriptor_file = temp_descriptor.name
    temp_descriptor.close()

    try:
        compile_proto_to_binary(all_proto_files, descriptor_file, proto_root)

        with open(descriptor_file, "rb") as f:
            proto_data = f.read()
        fds = descriptor_pb2.FileDescriptorSet()
        try:
            fds.ParseFromString(proto_data)
        except Exception as e:
            raise DataContractException(
                type="schema",
                name="Parse descriptor set",
                reason="Failed to parse descriptor set from compiled proto files",
                engine="datacontract",
                original_exception=e,
            )

        odcs = create_odcs()
        odcs.schema_ = []

        source_proto_basenames = {os.path.basename(proto) for proto in sources}

        for file_descriptor in fds.file:
            if os.path.basename(file_descriptor.name) not in source_proto_basenames:
                continue

            for message in file_descriptor.message_type:
                properties = []
                for field in message.field:
                    prop = convert_proto_field_to_property(fds, field)
                    properties.append(prop)

                schema_obj = create_schema_object(
                    name=message.name,
                    physical_type="message",
                    description=f"Details of {message.name}.",
                    properties=properties,
                )
                odcs.schema_.append(schema_obj)

        return odcs
    finally:
        if os.path.exists(descriptor_file):
            os.remove(descriptor_file)


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
