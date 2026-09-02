import os
import re
from unittest.mock import MagicMock

import pytest
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


def test_test_output_rejects_unknown_extension(tmp_path):
    result = runner.invoke(
        app,
        ["test", "--output", str(tmp_path / "test-results.txt"), "./fixtures/junit/datacontract.yaml"],
    )
    assert result.exit_code == 1
    assert "Cannot infer output format from extension '.txt'" in result.stdout


def test_test_schema_name_option_in_help():
    """Test that --schema-name option is available in test command help."""
    result = runner.invoke(app, ["test", "--help"], env={"COLUMNS": "200"})
    assert result.exit_code == 0
    plain_output = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)
    assert "--schema-name" in plain_output


def test_loads_env_file_from_current_working_directory(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("DATACONTRACT_TEST_DOTENV_VAR=from-dotenv\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("DATACONTRACT_TEST_DOTENV_VAR", raising=False)
    try:
        result = runner.invoke(app, ["lint", "unknown.yaml"])
        assert result.exit_code == 1  # file does not exist, but the app callback has run
        assert os.environ.get("DATACONTRACT_TEST_DOTENV_VAR") == "from-dotenv"
    finally:
        os.environ.pop("DATACONTRACT_TEST_DOTENV_VAR", None)


def test_loads_env_file_from_parent_directory(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("DATACONTRACT_TEST_DOTENV_VAR=from-dotenv\n")
    subdir = tmp_path / "sub" / "dir"
    subdir.mkdir(parents=True)
    monkeypatch.chdir(subdir)
    monkeypatch.delenv("DATACONTRACT_TEST_DOTENV_VAR", raising=False)
    try:
        result = runner.invoke(app, ["lint", "unknown.yaml"])
        assert result.exit_code == 1  # file does not exist, but the app callback has run
        assert os.environ.get("DATACONTRACT_TEST_DOTENV_VAR") == "from-dotenv"
    finally:
        os.environ.pop("DATACONTRACT_TEST_DOTENV_VAR", None)


def test_env_file_does_not_override_existing_environment_variables(tmp_path, monkeypatch):
    (tmp_path / ".env").write_text("DATACONTRACT_TEST_DOTENV_VAR=from-dotenv\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("DATACONTRACT_TEST_DOTENV_VAR", "from-environment")
    result = runner.invoke(app, ["lint", "unknown.yaml"])
    assert result.exit_code == 1
    assert os.environ.get("DATACONTRACT_TEST_DOTENV_VAR") == "from-environment"


def test_system_truststore_option_in_help():
    result = runner.invoke(app, ["--help"], env={"COLUMNS": "200"})
    assert result.exit_code == 0
    plain_output = re.sub(r"\x1b\[[0-9;]*m", "", result.stdout)
    assert "--system-truststore" in plain_output


def test_system_truststore_flag_injects(monkeypatch):
    calls = []
    monkeypatch.setattr("datacontract.cli.inject_system_truststore", lambda: calls.append(True))
    result = runner.invoke(app, ["--system-truststore", "lint", "unknown.yaml"])
    assert result.exit_code == 1  # file does not exist, but the app callback has run
    assert calls == [True]


def test_system_truststore_env_var_injects(monkeypatch):
    calls = []
    monkeypatch.setattr("datacontract.cli.inject_system_truststore", lambda: calls.append(True))
    monkeypatch.setenv("DATACONTRACT_SYSTEM_TRUSTSTORE", "1")
    result = runner.invoke(app, ["lint", "unknown.yaml"])
    assert result.exit_code == 1
    assert calls == [True]


def test_system_truststore_not_injected_by_default(monkeypatch):
    calls = []
    monkeypatch.setattr("datacontract.cli.inject_system_truststore", lambda: calls.append(True))
    monkeypatch.delenv("DATACONTRACT_SYSTEM_TRUSTSTORE", raising=False)
    result = runner.invoke(app, ["lint", "unknown.yaml"])
    assert result.exit_code == 1
    assert calls == []


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


def test_error_message_keeps_bracketed_text(monkeypatch, capsys):
    """Rich markup must not eat hints like `pip install "botocore[crt]"`."""
    from datacontract import cli

    monkeypatch.setattr(cli, "app", MagicMock(side_effect=RuntimeError('run: pip install "botocore[crt]"')))

    with pytest.raises(SystemExit):
        cli.main()

    assert "botocore[crt]" in capsys.readouterr().out


def test_test_publish_empty_string_skips_publish(monkeypatch):
    """`--publish ''` means "don't publish" — CI templates render it when the URL is unset."""
    calls = []
    monkeypatch.setattr(
        "datacontract.data_contract.publish_test_results_to_entropy_data",
        lambda *args, **kwargs: calls.append(args),
    )
    result = runner.invoke(app, ["test", "--publish", "", "./fixtures/parquet/datacontract.yaml"])
    assert result.exit_code == 0
    assert calls == []


def test_test_publish_rejects_non_http_url():
    result = runner.invoke(app, ["test", "--publish", "ftp://foo", "./fixtures/parquet/datacontract.yaml"])
    assert result.exit_code == 1
    assert "must start with http:// or https://" in result.stdout
