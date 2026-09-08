"""Tests for the YAML config file: Config.from_yaml and the CLI --config-file option."""

import pytest
from typer.testing import CliRunner

from datacontract import Config
from datacontract.cli import app
from datacontract.config import cli_config, set_cli_config

runner = CliRunner()


def message(result) -> str:
    """The CLI output as one line.

    Typer renders errors in a Rich box, wrapping the text to the terminal width.
    Where it wraps depends on how long the path in the message is -- under
    `pytest -n` the tmp_path carries a worker id and the wrap lands mid-phrase --
    so the box drawing and the line breaks are removed before matching.
    """
    stripped = "".join(" " if character in "│╭╮╰╯─" else character for character in result.output)
    return " ".join(stripped.split())


@pytest.fixture(autouse=True)
def reset_cli_config():
    yield
    set_cli_config(None)


def _write_config(tmp_path, content: str):
    path = tmp_path / "datacontract-config.yaml"
    path.write_text(content)
    return path


def test_from_yaml_maps_sections_to_fields(tmp_path):
    path = _write_config(
        tmp_path,
        """
snowflake:
  username: svc_test
  login_timeout: 30
entropy_data:
  api_key: key
max_errors: 10
""",
    )

    config = Config.from_yaml(path)

    assert config.snowflake_username == "svc_test"
    assert config.snowflake_login_timeout == 30
    assert config.get_entropy_data_api_key() == "key"
    assert config.max_errors == 10


def test_from_yaml_interpolates_environment_references(tmp_path, monkeypatch):
    monkeypatch.setenv("SNOWFLAKE_PASSWORD", "pw-from-env")
    path = _write_config(tmp_path, "snowflake:\n  password: ${SNOWFLAKE_PASSWORD}\n")

    assert Config.from_yaml(path).get_snowflake_password() == "pw-from-env"


def test_from_yaml_uses_the_inline_default_when_the_variable_is_unset(tmp_path, monkeypatch):
    monkeypatch.delenv("SNOWFLAKE_WAREHOUSE", raising=False)
    path = _write_config(tmp_path, "snowflake:\n  warehouse: ${SNOWFLAKE_WAREHOUSE:-COMPUTE_WH}\n")

    assert Config.from_yaml(path).get_snowflake_warehouse() == "COMPUTE_WH"


def test_from_yaml_rejects_references_to_unset_environment_variables(tmp_path, monkeypatch):
    monkeypatch.delenv("SNOWFLAKE_PASSWORD", raising=False)
    path = _write_config(tmp_path, "snowflake:\n  password: ${SNOWFLAKE_PASSWORD}\n")

    with pytest.raises(ValueError, match="SNOWFLAKE_PASSWORD"):
        Config.from_yaml(path)


def test_from_yaml_rejects_unknown_option_names(tmp_path):
    path = _write_config(tmp_path, "snowflake:\n  warehose: TYPO\n")

    with pytest.raises(ValueError, match="snowflake_warehose"):
        Config.from_yaml(path)


def test_config_file_option_is_resolved_for_commands(tmp_path, monkeypatch):
    monkeypatch.setenv("SNOWFLAKE_PASSWORD", "pw-from-env")
    path = _write_config(
        tmp_path,
        """
snowflake:
  username: svc_test
  password: ${SNOWFLAKE_PASSWORD}
""",
    )

    result = runner.invoke(app, ["--config-file", str(path), "lint", "fixtures/lint/valid_datacontract.yaml"])

    assert result.exit_code == 0, result.output
    assert cli_config().get_snowflake_username() == "svc_test"
    assert cli_config().get_snowflake_password() == "pw-from-env"


def test_config_file_defaults_to_the_working_directory(tmp_path, monkeypatch):
    contract = (tmp_path / "contract.yaml").resolve()
    import shutil

    shutil.copy("fixtures/lint/valid_datacontract.yaml", contract)
    _write_config(tmp_path, "postgres:\n  username: reader\n")
    monkeypatch.chdir(tmp_path)

    result = runner.invoke(app, ["lint", str(contract)])

    assert result.exit_code == 0, result.output
    assert cli_config().get_postgres_username() == "reader"


def test_no_config_file_means_no_config(monkeypatch, tmp_path):
    monkeypatch.chdir(tmp_path)  # no datacontract-config.yaml here

    runner.invoke(app, ["--version"])

    assert cli_config() is None


def test_invalid_config_file_fails_with_a_clear_message(tmp_path):
    path = _write_config(tmp_path, "snowflake:\n  warehose: TYPO\n")

    result = runner.invoke(app, ["--config-file", str(path), "lint", "fixtures/lint/valid_datacontract.yaml"])

    assert result.exit_code != 0
    assert "snowflake_warehose" in message(result)


def test_missing_config_file_fails_with_a_clear_message(tmp_path):
    result = runner.invoke(
        app, ["--config-file", str(tmp_path / "nope.yaml"), "lint", "fixtures/lint/valid_datacontract.yaml"]
    )

    assert result.exit_code != 0
    assert "does not exist" in message(result)


def test_from_yaml_names_the_file_on_invalid_yaml(tmp_path):
    path = _write_config(tmp_path, "snowflake: [unclosed\n")

    with pytest.raises(ValueError, match="datacontract-config.yaml"):
        Config.from_yaml(path)


def test_config_file_works_despite_unrelated_malformed_env_var(tmp_path, monkeypatch):
    monkeypatch.setenv("DATACONTRACT_SNOWFLAKE_LOGIN_TIMEOUT", "not-a-number")
    path = _write_config(tmp_path, "postgres:\n  username: reader\n")

    result = runner.invoke(app, ["--config-file", str(path), "lint", "fixtures/lint/valid_datacontract.yaml"])

    assert result.exit_code == 0, result.output
    assert cli_config().get_postgres_username() == "reader"
