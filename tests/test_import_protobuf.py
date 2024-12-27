import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

# logging.basicConfig(level=logging.DEBUG, force=True)

protobuf_file_path = "fixtures/protobuf/data/sample_data.proto3.data"


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


def test_import_sql():
    result = DataContract().import_from_source("protobuf", protobuf_file_path)

    expected = """dataContractSpecification: 0.9.3
id: my-data-contract-id-001
info:
  title: My Data Contract
  version: 0.0.1
servers:
  production:
    type: local
    format: protobuf
    path: ./tests/fixtures/protobuf/data/sample_data.proto3.data
models:
  sample_data:
    description: ProtoBuf file with simple schema
    type: table
    fields:
      field_1:
        type: integer
      field_2:
        type: string
      field_3:
        type: string
    """
    print("Result", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
    # Disable linters so we don't get "missing description" warnings
    assert DataContract(data_contract_str=expected).lint(enabled_linters=set()).has_passed()

