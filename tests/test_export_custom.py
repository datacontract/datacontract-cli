from pathlib import Path

from datacontract_specification.model import DataContractSpecification
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.export.custom_exporter import to_custom
from datacontract.imports.dcs_importer import convert_dcs_to_odcs

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
    dcs = DataContractSpecification.from_file("fixtures/custom/export/datacontract.yaml")
    data_contract = convert_dcs_to_odcs(dcs)
    template = Path("fixtures/custom/export/template.sql")
    result = to_custom(data_contract, template)

    with open("fixtures/custom/export/expected.sql", "r") as file:
        assert result == file.read()
