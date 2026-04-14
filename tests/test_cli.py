import re

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


def test_test_schema_name_option_in_help():
    """Test that --schema-name option is available in test command help."""
    result = runner.invoke(app, ["test", "--help"], env={"COLUMNS": "200"})
    assert result.exit_code == 0
    plain_output = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)
    assert "--schema-name" in plain_output


def test_changelog_help():
    result = runner.invoke(app, ["changelog", "--help"])
    assert result.exit_code == 0


def test_changelog_with_changes():
    result = runner.invoke(
        app,
        [
            "changelog",
            "fixtures/changelog/integration/changelog_integration_v1.yaml",
            "fixtures/changelog/integration/changelog_integration_v2.yaml",
        ],
    )
    assert result.exit_code == 0
    assert "Summary" in result.output
    assert "Details" in result.output
    assert "Removed" in result.output
    assert "Updated" in result.output
    assert "Added" in result.output
