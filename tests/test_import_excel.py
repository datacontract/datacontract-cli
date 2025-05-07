import os
import sys

import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.imports.excel_importer import import_excel_as_odcs

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--format",
            "excel",
            "--source",
            "./fixtures/excel/shipments-odcs.xlsx",
        ],
    )
    assert result.exit_code == 0


def test_import_excel_odcs():
    result = import_excel_as_odcs("./fixtures/excel/shipments-odcs.xlsx")
    expected_datacontract = read_file("fixtures/excel/shipments-odcs.yaml")
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected_datacontract)


def read_file(file):
    if not os.path.exists(file):
        print(f"The file '{file}' does not exist.")
        sys.exit(1)
    with open(file, "r") as file:
        file_content = file.read()
    return file_content
