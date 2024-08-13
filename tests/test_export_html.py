import os
from pathlib import Path

from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.export.html_export import to_html
from datacontract.model.data_contract_specification import DataContractSpecification

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(app, ["export", "./fixtures/export/datacontract.yaml", "--format", "html"])
    assert result.exit_code == 0


def test_cli_with_output(tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "./fixtures/export/datacontract.yaml",
            "--format",
            "html",
            "--output",
            tmp_path / "datacontract.html",
        ],
    )
    assert result.exit_code == 0
    assert os.path.exists(tmp_path / "datacontract.html")


def test_to_html():
    data_contract = DataContractSpecification.from_file("fixtures/export/datacontract.yaml")
    expected_html = """<html"""

    html = to_html(data_contract)

    assert expected_html in html
