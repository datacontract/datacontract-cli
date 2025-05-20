import os
from pathlib import Path

from typer.testing import CliRunner

from datacontract.cli import app


def test_cli():
    runner = CliRunner()
    result = runner.invoke(app, ["export", "./fixtures/export/datacontract.yaml", "--format", "mermaid"])
    assert result.exit_code == 0


def test_cli_with_output(tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "./fixtures/export/datacontract.yaml",
            "--format",
            "mermaid",
            "--output",
            tmp_path / "datacontract.mermaid",
        ],
    )
    assert result.exit_code == 0
    assert os.path.exists(tmp_path / "datacontract.mermaid")


def test_mermaid_content(tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "./fixtures/export/datacontract.yaml",
            "--format",
            "mermaid",
            "--output",
            tmp_path / "datacontract.mermaid",
        ],
    )
    assert result.exit_code == 0

    # Read the generated file
    with open(tmp_path / "datacontract.mermaid", "r") as f:
        content = f.read()

    # Basic content validation
    assert "erDiagram" in content


def test_mermaid_expected(tmp_path: Path):
    expected = (
        """erDiagram\n\t\t"ðŸ“‘orders"{\n\torder_idðŸ”‘ varchar\n\torder_total bigint\n\torder_status text\n}\n\n"""
    )
    datacontract_file = "fixtures/export/datacontract.yaml"
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            datacontract_file,
            "--format",
            "mermaid",
            "--output",
            tmp_path / "datacontract.mermaid",
        ],
    )
    assert result.exit_code == 0
    assert os.path.exists(tmp_path / "datacontract.mermaid")

    with open(tmp_path / "datacontract.mermaid") as file:
        actual = file.read()
    assert actual == expected
