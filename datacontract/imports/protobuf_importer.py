import os
import sys
import subprocess
import yaml
import time
import re
from google.protobuf import descriptor_pb2
from datacontract.model.data_contract_specification import DataContractSpecification
from datacontract.imports.importer import Importer  # Import the abstract Importer class


def map_type_from_protobuf(field_type: int):
    protobuf_type_mapping = {
        1: "double",
        2: "float",
        3: "int64",
        4: "uint64",
        5: "int32",
        6: "fixed64",
        7: "fixed32",
        8: "bool",
        9: "string",
        12: "bytes",
        13: "uint32",
        15: "sfixed32",
        16: "sfixed64",
        17: "sint32",
        18: "sint64"
    }
    return protobuf_type_mapping.get(field_type, "string")


def parse_imports(proto_file: str) -> list:
    """
    Parse import statements from a .proto file and return a list of imported file paths.
    """
    with open(proto_file, "r") as f:
        content = f.read()
    imported_files = re.findall(r'import\s+"(.+?)";', content)
    proto_dir = os.path.dirname(proto_file)
    return [os.path.join(proto_dir, imp) for imp in imported_files]


def compile_proto_to_binary(proto_files: list, output_file: str):
    """
    Compile the provided proto files into a single descriptor set.
    """
    proto_dirs = set(os.path.dirname(proto) for proto in proto_files)
    proto_paths = [f"--proto_path={d}" for d in proto_dirs]
    command = ["protoc", f"--descriptor_set_out={output_file}"] + proto_paths + proto_files
    try:
        subprocess.run(command, check=True)
        print(f"Compiled proto files to {output_file}")
    except subprocess.CalledProcessError as e:
        raise RuntimeError(f"Failed to compile proto files: {e}")


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
                                "items": {
                                    "type": "object",
                                    "fields": nested_fields
                                }
                            }
                        else:
                            field_info = {
                                "description": f"Nested object of {nested_msg_name}",
                                "type": "object",
                                "fields": nested_fields
                            }
                    elif field.type == 14:  # TYPE_ENUM
                        enum_name = field.type_name.split(".")[-1]
                        enum_values = extract_enum_values_from_fds(fds, enum_name)
                        field_info = {
                            "description": f"Enum field {field.name}",
                            "type": "enum",
                            "values": enum_values,
                            "required": (field.label == 2)
                        }
                    else:
                        field_info = {
                            "description": f"Field {field.name}",
                            "type": map_type_from_protobuf(field.type),
                            "required": (field.label == 2)
                        }
                    fields[field.name] = field_info
                return fields
    return {}


def import_protobuf(data_contract_specification: DataContractSpecification, sources: list, output_dir: str) -> DataContractSpecification:
    """
    Gather all proto files (including those imported), compile them into one descriptor,
    then generate models with nested fields and enums resolved.
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
    print("All proto files:", all_proto_files)

    # --- Step 2: Compile all proto files into a single descriptor set.
    os.makedirs(output_dir, exist_ok=True)
    descriptor_file = os.path.join(output_dir, "descriptor.pb")
    compile_proto_to_binary(all_proto_files, descriptor_file)

    with open(descriptor_file, "rb") as f:
        proto_data = f.read()
    fds = descriptor_pb2.FileDescriptorSet()
    fds.ParseFromString(proto_data)
    print("File Descriptor Set:", fds)

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
                            "items": {
                                "type": "object",
                                "fields": nested_fields
                            }
                        }
                    else:
                        field_info = {
                            "description": f"Nested object of {nested_msg_name}",
                            "type": "object",
                            "fields": nested_fields
                        }
                    fields[field.name] = field_info
                elif field.type == 14:  # TYPE_ENUM
                    enum_name = field.type_name.split(".")[-1]
                    enum_values = extract_enum_values_from_fds(fds, enum_name)
                    field_info = {
                        "description": f"Enum field {field.name}",
                        "type": "enum",
                        "values": enum_values,
                        "required": (field.label == 2)
                    }
                    fields[field.name] = field_info
                else:
                    field_info = {
                        "description": f"Field {field.name}",
                        "type": map_type_from_protobuf(field.type),
                        "required": (field.label == 2)
                    }
                    fields[field.name] = field_info

            all_models[message.name] = {
                "description": f"Details of {message.name}.",
                "type": "table",
                "fields": fields
            }

    data_contract_specification.models = all_models

    # --- Step 4: Write out the data contract YAML.
    timestamp = time.strftime("%Y%m%d%H%M%S")
    output_file = os.path.join(output_dir, f"datacontract_{timestamp}.yaml")
    contract_structure = {
        "dataContractSpecification": "1.1.0",
        "id": "resolved_alerts",
        "info": {
            "title": "Alerts Data Contract",
            "version": "0.0.1",
            "status": "active",
            "description": "Data contract for alerts based on the provided protobuf schema.",
            "owner": "Global Risk Analytics Team",
            "contact": {
                "name": "Global Risk Analytics Support",
                "url": "https://risk.example.com/support",
                "email": "support@risk.example.com"
            }
        },
        "models": all_models
    }
    with open(output_file, "w") as f:
        yaml.dump(contract_structure, f, default_flow_style=False)
    print(f"Data contract file written: {output_file}")
    return data_contract_specification


###############################################################################
# Exported class for the importer factory
###############################################################################

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
        Import a protobuf file (and its imports) into the given
        DataContractSpecification.

        Parameters:
          - data_contract_specification: the initial specification to update.
          - source: the protobuf file path.
          - import_args: optional dictionary with additional arguments (e.g. 'output_dir').

        Returns:
          The updated DataContractSpecification.
        """
        if import_args is None:
            import_args = {}
        output_dir = import_args.get("output_dir", os.getcwd())
        # Wrap the source in a list because import_protobuf expects a list of sources.
        return import_protobuf(data_contract_specification, [source], output_dir)


###############################################################################
# Allow running this module as a script
###############################################################################

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python -m datacontract.imports.protobuf_importer <protobuf_file1> <protobuf_file2> ... [output_directory]")
        sys.exit(1)
    protobuf_files = sys.argv[1:-1] if len(sys.argv) > 2 else [sys.argv[1]]
    output_directory = sys.argv[-1] if len(sys.argv) > 2 else os.getcwd()
    print(f"Protobuf files: {protobuf_files}")
    print(f"Output directory: {output_directory}")

    data_contract_spec = DataContractSpecification(models={})
    import_protobuf(data_contract_spec, protobuf_files, output_directory)
