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


def test_mermaid_structure(tmp_path: Path):
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

    with open(tmp_path / "datacontract.mermaid") as file:
        content = file.read()

    # Check structure
    assert "erDiagram" in content
    assert "orders" in content
    assert "order_id" in content
    assert "order_total" in content
    assert "order_status" in content
