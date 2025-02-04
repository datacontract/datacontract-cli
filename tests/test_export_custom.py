from pathlib import Path

from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.export.custom_converter import to_custom
from datacontract.model.data_contract_specification import DataContractSpecification

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


def test_to_custom():
    data_contract = DataContractSpecification.from_file("fixtures/custom/export/datacontract.yaml")
    template = Path("fixtures/custom/export/template.sql")
    result = to_custom(data_contract, template)

    with open("fixtures/custom/export/expected.sql", "r") as file:
        assert result == file.read()
