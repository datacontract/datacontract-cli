import logging

import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

logging.basicConfig(level=logging.DEBUG, force=True)

datacontract = "fixtures/postgres/datacontract.yaml"
sql_file_path = "fixtures/postgres/data/data.sql"


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--format",
            "sql",
            "--source",
            sql_file_path,
        ],
    )
    assert result.exit_code == 0


def test_import_sql():
    result = DataContract().import_from_source("sql", sql_file_path)

    expected = """
dataContractSpecification: 0.9.3
id: my-data-contract-id
info:
  title: My Data Contract
  version: 0.0.1
models:
  my_table:
    type: table
    fields:
      field_one:
        type: varchar
        required: true
        primary: true
        unique: true
        maxLength: 10
      field_two:
        type: integer
        required: true
      field_three:
        type: timestamp
    """
    print("Result", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
    # Disable linters so we don't get "missing description" warnings
    assert DataContract(data_contract_str=expected).lint(enabled_linters=set()).has_passed()
