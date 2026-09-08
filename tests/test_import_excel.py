import os
import sys

import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.imports.excel_importer import import_excel_as_odcs, parse_port

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "excel",
            "--source",
            "./fixtures/excel/shipments-odcs.xlsx",
        ],
    )
    assert result.exit_code == 0
    assert "kind: DataContract" in result.stdout


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


def test_parse_port_keeps_variable_references():
    assert parse_port(5432) == 5432
    assert parse_port(5432.0) == 5432
    assert parse_port(" 5432 ") == 5432
    assert parse_port("${DB_PORT:-5432}") == "${DB_PORT:-5432}"
    assert parse_port("") is None
    assert parse_port(None) is None
