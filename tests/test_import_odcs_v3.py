import os
import sys

import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--format",
            "odcs",
            "--source",
            "./fixtures/odcs_v3/full-example.odcs.yaml",
        ],
    )
    assert result.exit_code == 0


def test_import_full_odcs():
    result = DataContract().import_from_source("odcs", "./fixtures/odcs_v3/full-example.odcs.yaml")
    expected_datacontract = read_file("fixtures/odcs_v3/full-example.datacontract.yml")
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected_datacontract)
    assert DataContract(data_contract_str=expected_datacontract).lint(enabled_linters="none").has_passed()


def test_import_complex_odcs():
    result = DataContract().import_from_source("odcs", "./fixtures/odcs_v3/adventureworks.odcs.yaml")
    expected_datacontract = read_file("fixtures/odcs_v3/adventureworks.datacontract.yml")
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected_datacontract)
    assert DataContract(data_contract_str=expected_datacontract).lint(enabled_linters="none").has_passed()


def read_file(file):
    if not os.path.exists(file):
        print(f"The file '{file}' does not exist.")
        sys.exit(1)
    with open(file, "r") as file:
        file_content = file.read()
    return file_content
