from datacontract_specification.model import DataContractSpecification
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.export.markdown_exporter import to_markdown
from datacontract.imports.dcs_importer import convert_dcs_to_odcs

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "./fixtures/markdown/export/datacontract.yaml",
            "--format",
            "markdown",
        ],
    )
    assert result.exit_code == 0
    assert result.output.startswith("# urn:datacontract:checkout:orders-latest")


def test_to_markdown():
    dcs = DataContractSpecification.from_file("fixtures/markdown/export/datacontract.yaml")
    data_contract = convert_dcs_to_odcs(dcs)
    result = to_markdown(data_contract)

    with open("fixtures/markdown/export/expected.md", "r") as file:
        assert result == file.read()
