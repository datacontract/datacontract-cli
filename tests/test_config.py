"""Unit tests for programmatic configuration (datacontract.config).

Covers the Config class (env snapshot, overrides, validation, secrets), the
ContextVar resolution (precedence, scoping, thread isolation), and the drift
guard that keeps Config in sync with the env vars the code actually reads.
"""

import re
import threading
from pathlib import Path

import pytest
from pydantic import ValidationError

from datacontract import Config
from datacontract.config import config_context, getenv, known_env_names, unknown_snowflake_env_names


def test_field_names_map_to_env_var_names():
    config = Config(
        snowflake_username="svc_test",
        snowflake_password="secret",
        snowflake_login_timeout=30,
        snowflake_create_object_udfs=True,
        postgres_username="reader",
    )

    env_dict = config.to_env_dict()

    assert env_dict["DATACONTRACT_SNOWFLAKE_USERNAME"] == "svc_test"
    assert env_dict["DATACONTRACT_SNOWFLAKE_PASSWORD"] == "secret"
    assert env_dict["DATACONTRACT_SNOWFLAKE_LOGIN_TIMEOUT"] == "30"
    assert env_dict["DATACONTRACT_SNOWFLAKE_CREATE_OBJECT_UDFS"] == "true"
    assert env_dict["DATACONTRACT_POSTGRES_USERNAME"] == "reader"
    assert "DATACONTRACT_MYSQL_USERNAME" not in env_dict


def test_aliased_fields_keep_their_unprefixed_env_var_names(monkeypatch):
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "key-from-env")

    config = Config()

    assert config.entropy_data_api_key.get_secret_value() == "key-from-env"
    assert config.to_env_dict()["ENTROPY_DATA_API_KEY"] == "key-from-env"


def test_config_snapshots_the_environment(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_POSTGRES_USERNAME", "from_env")

    assert Config().postgres_username == "from_env"


def test_explicit_arguments_win_over_the_environment(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_POSTGRES_USERNAME", "from_env")

    assert Config(postgres_username="explicit").postgres_username == "explicit"


def test_secrets_do_not_leak_into_repr():
    config = Config(snowflake_password="super-secret")

    assert "super-secret" not in repr(config)
    assert config.snowflake_password.get_secret_value() == "super-secret"


def test_unknown_options_raise():
    with pytest.raises(ValueError, match="snowflake_pasword"):
        Config(snowflake_pasword="typo")


def test_invalid_typed_env_values_fail_loudly(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_SNOWFLAKE_LOGIN_TIMEOUT", "not-a-number")

    with pytest.raises(ValidationError):
        Config()


def test_unrelated_environment_variables_are_ignored(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_CLI_DEBUG", "1")

    Config()  # must not raise


def test_getenv_prefers_the_active_config_over_the_environment(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_POSTGRES_USERNAME", "from_env")

    with config_context({"DATACONTRACT_POSTGRES_USERNAME": "from_config"}):
        assert getenv("DATACONTRACT_POSTGRES_USERNAME") == "from_config"

    assert getenv("DATACONTRACT_POSTGRES_USERNAME") == "from_env"


def test_getenv_falls_back_to_the_environment_inside_a_context(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_MYSQL_USERNAME", "from_env")

    with config_context({"DATACONTRACT_POSTGRES_USERNAME": "x"}):
        assert getenv("DATACONTRACT_MYSQL_USERNAME") == "from_env"


def test_config_context_accepts_a_config_instance():
    with config_context(Config(snowflake_username="svc_test")):
        assert getenv("DATACONTRACT_SNOWFLAKE_USERNAME") == "svc_test"


def test_config_context_is_isolated_between_threads():
    results = {}
    barrier = threading.Barrier(2)

    def worker(name: str, value: str):
        with config_context({"DATACONTRACT_POSTGRES_PASSWORD": value}):
            barrier.wait(timeout=5)  # both threads hold their context at the same time
            results[name] = getenv("DATACONTRACT_POSTGRES_PASSWORD")

    threads = [
        threading.Thread(target=worker, args=("a", "password-a")),
        threading.Thread(target=worker, args=("b", "password-b")),
    ]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    assert results == {"a": "password-a", "b": "password-b"}


def test_unknown_snowflake_env_names_reports_undeclared_variables(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_SNOWFLAKE_SESSION_PARAMETERS", "{}")

    assert "DATACONTRACT_SNOWFLAKE_SESSION_PARAMETERS" in unknown_snowflake_env_names()


def test_declared_snowflake_variables_are_not_reported(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_SNOWFLAKE_WAREHOUSE", "COMPUTE_WH")

    assert "DATACONTRACT_SNOWFLAKE_WAREHOUSE" not in unknown_snowflake_env_names()


# Env vars the code reads that are deliberately not Config fields: process-level
# concerns, not per-operation connection config.
_NON_CONFIG_ENV_VARS = {
    "DATACONTRACT_CLI_DEBUG",
    "DATACONTRACT_CLI_API_KEY",
    "DATACONTRACT_SYSTEM_TRUSTSTORE",
}


def test_every_env_var_the_code_reads_is_a_config_field():
    """Drift guard: a new DATACONTRACT_* variable needs a Config field (or an
    explicit entry in _NON_CONFIG_ENV_VARS)."""
    package_dir = Path(__file__).parent.parent / "datacontract"
    known = known_env_names()
    pattern = re.compile(r"DATACONTRACT_[A-Z0-9]+(?:_[A-Z0-9]+)*")

    unknown = set()
    for path in package_dir.rglob("*.py"):
        for name in pattern.findall(path.read_text()):
            if name in known or name in _NON_CONFIG_ENV_VARS:
                continue
            # Prefix fragments from f-strings like "DATACONTRACT_SNOWFLAKE_{suffix}"
            if any(field_name.startswith(name + "_") for field_name in known):
                continue
            unknown.add(name)

    assert unknown == set(), (
        f"Env vars read in code but not declared as Config fields: {sorted(unknown)}. "
        "Add a field to datacontract.config.Config or list the name in _NON_CONFIG_ENV_VARS."
    )
