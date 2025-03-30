import os
import re
import tempfile

from google.protobuf import descriptor_pb2
from grpc_tools import protoc

from datacontract.imports.importer import Importer
from datacontract.model.data_contract_specification import DataContractSpecification
from datacontract.model.exceptions import DataContractException


def map_type_from_protobuf(field_type: int):
    protobuf_type_mapping = {
        1: "double",
        2: "float",
        3: "long",
        4: "long",  # uint64 mapped to long
        5: "integer",  # int32 mapped to integer
        6: "string",  # fixed64 mapped to string
        7: "string",  # fixed32 mapped to string
        8: "boolean",
        9: "string",
        12: "bytes",
        13: "integer",  # uint32 mapped to integer
        15: "integer",  # sfixed32 mapped to integer
        16: "long",  # sfixed64 mapped to long
        17: "integer",  # sint32 mapped to integer
        18: "long",  # sint64 mapped to long
    }
    return protobuf_type_mapping.get(field_type, "string")


def parse_imports(proto_file: str) -> list:
    """
    Parse import statements from a .proto file and return a list of imported file paths.
    """
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
    imported_files = re.findall(r'import\s+"(.+?)";', content)
    proto_dir = os.path.dirname(proto_file)
    return [os.path.join(proto_dir, imp) for imp in imported_files]


def compile_proto_to_binary(proto_files: list, output_file: str):
    """
    Compile the provided proto files into a single descriptor set using grpc_tools.protoc.
    """
    proto_dirs = set(os.path.dirname(proto) for proto in proto_files)
    proto_paths = [f"--proto_path={d}" for d in proto_dirs]

    args = [""] + proto_paths + [f"--descriptor_set_out={output_file}"] + proto_files
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
    """
    Search the FileDescriptorSet for an enum definition with the given name
    and return a dictionary of its values (name to number).
    """
    for file_descriptor in fds.file:
        # Check top-level enums.
        for enum in file_descriptor.enum_type:
            if enum.name == enum_name:
                return {value.name: value.number for value in enum.value}
        # Check enums defined inside messages.
        for message in file_descriptor.message_type:
            for enum in message.enum_type:
                if enum.name == enum_name:
                    return {value.name: value.number for value in enum.value}
    return {}


def extract_message_fields_from_fds(fds: descriptor_pb2.FileDescriptorSet, message_name: str) -> dict:
    """
    Given a FileDescriptorSet and a message name, return a dict with its field definitions.
    This function recurses for nested messages and handles enums.
    """
    for file_descriptor in fds.file:
        for msg in file_descriptor.message_type:
            if msg.name == message_name:
                fields = {}
                for field in msg.field:
                    if field.type == 11:  # TYPE_MESSAGE
                        nested_msg_name = field.type_name.split(".")[-1]
                        nested_fields = extract_message_fields_from_fds(fds, nested_msg_name)
                        if field.label == 3:  # repeated field
                            field_info = {
                                "description": f"List of {nested_msg_name}",
                                "type": "array",
                                "items": {"type": "object", "fields": nested_fields},
                            }
                        else:
                            field_info = {
                                "description": f"Nested object of {nested_msg_name}",
                                "type": "object",
                                "fields": nested_fields,
                            }
                    elif field.type == 14:  # TYPE_ENUM
                        enum_name = field.type_name.split(".")[-1]
                        enum_values = extract_enum_values_from_fds(fds, enum_name)
                        field_info = {
                            "description": f"Enum field {field.name}",
                            "type": "string",
                            "values": enum_values,
                            "required": (field.label == 2),
                        }
                    else:
                        field_info = {
                            "description": f"Field {field.name}",
                            "type": map_type_from_protobuf(field.type),
                            "required": (field.label == 2),
                        }
                    fields[field.name] = field_info
                return fields
    return {}


def import_protobuf(
    data_contract_specification: DataContractSpecification, sources: list, import_args: dict = None
) -> DataContractSpecification:
    """
    Gather all proto files (including those imported), compile them into one descriptor,
    then generate models with nested fields and enums resolved.

    The generated data contract uses generic defaults instead of specific hardcoded ones.
    """

    # --- Step 1: Gather all proto files (main and imported)
    proto_files_set = set()
    queue = list(sources)
    while queue:
        proto = queue.pop(0)
        if proto not in proto_files_set:
            proto_files_set.add(proto)
            for imp in parse_imports(proto):
                if os.path.exists(imp) and imp not in proto_files_set:
                    queue.append(imp)
    all_proto_files = list(proto_files_set)

    # --- Step 2: Compile all proto files into a single descriptor set.
    temp_descriptor = tempfile.NamedTemporaryFile(suffix=".pb", delete=False)
    descriptor_file = temp_descriptor.name
    temp_descriptor.close()  # Allow protoc to write to the file
    try:
        compile_proto_to_binary(all_proto_files, descriptor_file)

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

        # --- Step 3: Build models from the descriptor set.
        all_models = {}
        # Create a set of the main proto file basenames.
        source_proto_basenames = {os.path.basename(proto) for proto in sources}

        for file_descriptor in fds.file:
            # Only process file descriptors that correspond to your main proto files.
            if os.path.basename(file_descriptor.name) not in source_proto_basenames:
                continue

            for message in file_descriptor.message_type:
                fields = {}
                for field in message.field:
                    if field.type == 11:  # TYPE_MESSAGE
                        nested_msg_name = field.type_name.split(".")[-1]
                        nested_fields = extract_message_fields_from_fds(fds, nested_msg_name)
                        if field.label == 3:
                            field_info = {
                                "description": f"List of {nested_msg_name}",
                                "type": "array",
                                "items": {"type": "object", "fields": nested_fields},
                            }
                        else:
                            field_info = {
                                "description": f"Nested object of {nested_msg_name}",
                                "type": "object",
                                "fields": nested_fields,
                            }
                        fields[field.name] = field_info
                    elif field.type == 14:  # TYPE_ENUM
                        enum_name = field.type_name.split(".")[-1]
                        enum_values = extract_enum_values_from_fds(fds, enum_name)
                        field_info = {
                            "description": f"Enum field {field.name}",
                            "type": "string",
                            "values": enum_values,
                            "required": (field.label == 2),
                        }
                        fields[field.name] = field_info
                    else:
                        field_info = {
                            "description": f"Field {field.name}",
                            "type": map_type_from_protobuf(field.type),
                            "required": (field.label == 2),
                        }
                        fields[field.name] = field_info

                all_models[message.name] = {
                    "description": f"Details of {message.name}.",
                    "type": "table",
                    "fields": fields,
                }

        data_contract_specification.models = all_models

        return data_contract_specification
    finally:
        # Clean up the temporary descriptor file.
        if os.path.exists(descriptor_file):
            os.remove(descriptor_file)



class ProtoBufImporter(Importer):
    def __init__(self, name):
        # 'name' is passed by the importer factory.
        self.name = name

    def import_source(
        self,
        data_contract_specification: DataContractSpecification,
        source: str,
        import_args: dict = None,
    ) -> DataContractSpecification:
        """
        Import a protobuf file (and its imports) into the given DataContractSpecification.

        Parameters:
          - data_contract_specification: the initial specification to update.
          - source: the protobuf file path.
          - import_args: optional dictionary with additional arguments (e.g. 'output_dir').

        Returns:
          The updated DataContractSpecification.
        """
        # Wrap the source in a list because import_protobuf expects a list of sources.
        return import_protobuf(data_contract_specification, [source], import_args)

