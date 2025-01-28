from typer.testing import CliRunner

from datacontract.cli import app

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
            "template.sql",
        ],
    )
    assert result.exit_code == 0
