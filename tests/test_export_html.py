import os
from pathlib import Path

from typer.testing import CliRunner

from datacontract.cli import app

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(app, ["export", "./fixtures/export/datacontract.odcs.yaml", "--format", "html"])
    assert result.exit_code == 0


def test_cli_with_output(tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "./fixtures/export/datacontract.odcs.yaml",
            "--format",
            "html",
            "--output",
            tmp_path / "datacontract.html",
        ],
    )
    assert result.exit_code == 0
    assert os.path.exists(tmp_path / "datacontract.html")


def test_schemas_are_rendered():
    """Regression test for #880: schemas should render in the ODCS HTML template."""
    runner = CliRunner()
    result = runner.invoke(app, ["export", "./fixtures/export/datacontract.odcs.yaml", "--format", "html"])
    assert result.exit_code == 0
    # The schema name 'orders' and a property name 'order_id' should appear in the output
    assert "orders" in result.output
    assert "order_id" in result.output
