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


def test_import_protobuf():
    result = DataContract().import_from_source("protobuf", protobuf_file_path)

    expected = """dataContractSpecification: 1.1.0
id: my-data-contract-id
info:
  title: My Data Contract
  version: 0.0.1
models:
  Product:
    description: Details of Product.
    type: table
    fields:
      id:
        description: Field id
        type: string
        required: false
      name:
        description: Field name
        type: string
        required: false
      price:
        description: Field price
        type: double
        required: false
"""

    print("Result", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
    # Disable linters so we don't get "missing description" warnings
    assert DataContract(data_contract_str=expected).lint(enabled_linters=set()).has_passed()

