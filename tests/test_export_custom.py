from pathlib import Path

from typer.testing import CliRunner
from datacontract.export.exporter import Spec

from datacontract.cli import app
from datacontract.export.custom_converter import to_custom
from datacontract.model.data_contract_specification import DataContractSpecification
from open_data_contract_standard.model import OpenDataContractStandard

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "./fixtures/custom/export/datacontract.yaml",
            "--format",
            "custom",
            "--template",
            "./fixtures/custom/export/template.sql",
        ],
    )
    assert result.exit_code == 0

def test_cli_odcs():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "./fixtures/custom/export/full-example.odcs.yaml",
            "--format",
            "custom",
            "--template",
            "./fixtures/custom/export/expected_from_odcs.txt",
            "--spec",
            "odcs",
        ],
    )
    assert result.exit_code == 0

def test_cli_dcs():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "./fixtures/custom/export/datacontract.yaml",
            "--format",
            "custom",
            "--template",
            "./fixtures/custom/export/expected_from_dcs.txt",
            "--spec",
            "datacontract_specification",
        ],
    )
    assert result.exit_code == 0

def test_to_custom():
    data_contract = DataContractSpecification.from_file("fixtures/custom/export/datacontract.yaml")
    template = Path("fixtures/custom/export/template.sql")
    result = to_custom(data_contract, template)

    with open("fixtures/custom/export/expected.sql", "r") as file:
        assert result == file.read()

def test_to_custom_from_dcs():
    data_contract_dcs = DataContractSpecification.from_file("fixtures/custom/export/datacontract.yaml")
    template_path = Path("fixtures/custom/export/template_odcs.jinja")
    spec = Spec.datacontract_specification

    result = to_custom(data_contract_dcs, str(template_path), spec)

    with open("fixtures/custom/export/expected_from_dcs.txt", "r") as file:
        assert result == file.read()

def test_to_custom_from_odcs():
    data_contract_odcs = OpenDataContractStandard.from_file("fixtures/custom/export/full-example.odcs.yaml")
    template_path = Path("fixtures/custom/export/template_odcs.jinja")
    spec = Spec.odcs

    result = to_custom(data_contract_odcs, str(template_path), spec)

    with open("fixtures/custom/export/expected_from_odcs.txt", "r") as file:
        assert result == file.read()
