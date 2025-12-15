import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

# logging.basicConfig(level=logging.DEBUG, force=True)

protobuf_file_path = "fixtures/protobuf/data/sample_data.proto3.data"
nested_imports_c_proto = "fixtures/protobuf/nested_imports/C.proto"
nested_imports_subdirs_main = "fixtures/protobuf/nested_imports_subdirs/main.proto"


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--format",
            "protobuf",
            "--source",
            protobuf_file_path,
        ],
    )
    assert result.exit_code == 0


def test_import_protobuf():
    result = DataContract.import_from_source("protobuf", protobuf_file_path)

    with open("fixtures/protobuf/expected/sample_data.odcs.yaml") as file:
        expected = file.read()

    print("Result", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)


def test_import_protobuf_nested_imports():
    """
    Test transitive imports: C.proto imports A.proto which imports B.proto.
    C.proto -> A.proto -> B.proto

    This tests that when importing C.proto, the importer correctly resolves
    the transitive dependency on B.proto through A.proto.

    See: https://github.com/datacontract/datacontract-cli/issues/943
    """
    result = DataContract.import_from_source("protobuf", nested_imports_c_proto)

    with open("fixtures/protobuf/expected/nested_imports.odcs.yaml") as file:
        expected = file.read()

    print("Result", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)


def test_import_protobuf_nested_imports_subdirs():
    """
    Test transitive imports across subdirectories:
    main.proto imports models/person.proto which imports common/address.proto.
    main.proto -> models/person.proto -> common/address.proto

    This tests that when importing main.proto, the importer correctly resolves
    the transitive dependency on common/address.proto through models/person.proto.

    See: https://github.com/datacontract/datacontract-cli/issues/943
    """
    result = DataContract.import_from_source("protobuf", nested_imports_subdirs_main)

    with open("fixtures/protobuf/expected/nested_imports_subdirs.odcs.yaml") as file:
        expected = file.read()

    print("Result", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
