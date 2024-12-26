from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.export.markdown_converter import to_markdown
from datacontract.model.data_contract_specification import DataContractSpecification

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
    data_contract = DataContractSpecification.from_file("fixtures/markdown/export/datacontract.yaml")
    result = to_markdown(data_contract)

    with open("fixtures/markdown/export/expected.md", "r") as file:
        assert result == file.read()
