from typer.testing import CliRunner

from datacontract.cli import app

runner = CliRunner()

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_test_help():
    result = runner.invoke(app, ["test", "--help"])
    assert result.exit_code == 0


def test_file_does_not_exist():
    result = runner.invoke(app, ["test", "unknown.yaml"])
    assert result.exit_code == 1
    assert "The file 'unknown.yaml' does not \nexist." in result.stdout


def test_diff_help():
    result = runner.invoke(app, ["diff", "--help"])
    assert result.exit_code == 0


def test_diff_with_valid_files():
    result = runner.invoke(app, [
        "diff", 
        "fixtures/diff/integration/report_renderer_integration_v1.yaml",
        "fixtures/diff/integration/report_renderer_integration_v2.yaml"
    ])
    assert result.exit_code == 0
    assert "CHANGE SUMMARY" in result.stdout
    assert "CHANGE DETAILS" in result.stdout
