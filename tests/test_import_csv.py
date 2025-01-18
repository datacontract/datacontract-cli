import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

# logging.basicConfig(level=logging.DEBUG, force=True)

csv_file_path = "fixtures/csv/data/sample_data.csv"


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--format",
            "csv",
            "--source",
            csv_file_path,
        ],
    )
    assert result.exit_code == 0


def test_import_sql():
    result = DataContract().import_from_source("csv", csv_file_path)

    expected = """dataContractSpecification: 1.1.0
id: my-data-contract-id
info:
  title: My Data Contract
  version: 0.0.1
servers:
  production:
    type: local
    format: csv
    path: fixtures/csv/data/sample_data.csv
    delimiter: ','
models:
  sample_data:
    description: Csv file with encoding ascii
    type: table
    fields:
      field_one:
        type: string
      field_two:
        type: integer
      field_three:
        type: string
    """
    print("Result", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
    # Disable linters so we don't get "missing description" warnings
    assert DataContract(data_contract_str=expected).lint(enabled_linters=set()).has_passed()
