"""Unit tests for programmatic configuration (datacontract.config).

Covers the Config class (env snapshot, overrides, validation, secrets), value
resolution (config wins over env, env fallback), input normalization, and the
drift guard that keeps Config in sync with the env vars the code actually reads.
"""

import re
from pathlib import Path

import pytest
from pydantic import ValidationError

from datacontract import Config
from datacontract.config import known_env_names, unknown_snowflake_env_names


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


def test_accessors_prefer_config_values_over_the_environment(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_POSTGRES_USERNAME", "from_env")

    config = Config(postgres_username="from_config")

    assert config.get_postgres_username() == "from_config"


def test_accessors_fall_back_to_the_environment_for_unset_values(monkeypatch):
    monkeypatch.delenv("DATACONTRACT_MYSQL_USERNAME", raising=False)
    config = Config.model_construct()  # empty: nothing read from env at construction

    monkeypatch.setenv("DATACONTRACT_MYSQL_USERNAME", "from_env")

    assert config.get_mysql_username() == "from_env"
    assert config.get_mysql_password() is None


def test_accessors_unwrap_secrets():
    assert Config(snowflake_password="secret").get_snowflake_password() == "secret"


def test_required_accessor_raises_for_missing_values(monkeypatch):
    from datacontract.model.exceptions import DataContractException

    monkeypatch.delenv("DATACONTRACT_POSTGRES_PASSWORD", raising=False)

    with pytest.raises(DataContractException, match="DATACONTRACT_POSTGRES_PASSWORD"):
        Config.model_construct().get_postgres_password(required=True)


def test_bool_accessor_parses_config_and_env_values(monkeypatch):
    assert Config(sqlserver_encrypted_connection=False).get_sqlserver_encrypted_connection(default=True) is False

    monkeypatch.setenv("DATACONTRACT_IMPALA_USE_SSL", "yes")
    assert Config.model_construct().get_impala_use_ssl(default=False) is True

    monkeypatch.delenv("DATACONTRACT_IMPALA_USE_SSL")
    assert Config.model_construct().get_impala_use_ssl(default=True) is True


def test_int_accessor_parses_env_values_and_rejects_garbage(monkeypatch):
    from datacontract.model.exceptions import DataContractException

    monkeypatch.setenv("DATACONTRACT_SNOWFLAKE_LOGIN_TIMEOUT", "45")
    assert Config.model_construct().get_snowflake_login_timeout() == 45

    monkeypatch.setenv("DATACONTRACT_SNOWFLAKE_LOGIN_TIMEOUT", "abc")
    with pytest.raises(DataContractException, match="DATACONTRACT_SNOWFLAKE_LOGIN_TIMEOUT"):
        Config.model_construct().get_snowflake_login_timeout()


def test_every_field_has_a_typed_accessor():
    for name in Config.model_fields:
        assert callable(getattr(Config, f"get_{name}", None)), f"missing accessor get_{name}"


def test_resolve_accepts_a_dict_keyed_by_env_var_names():
    config = Config.resolve({"DATACONTRACT_SNOWFLAKE_USERNAME": "svc_test", "ENTROPY_DATA_API_KEY": "key"})

    assert config.snowflake_username == "svc_test"
    assert config.entropy_data_api_key.get_secret_value() == "key"


def test_resolve_rejects_unknown_env_var_names():
    with pytest.raises(ValueError, match="DATACONTRACT_SNOWFLAKE_TYPO"):
        Config.resolve({"DATACONTRACT_SNOWFLAKE_TYPO": "x"})


def test_resolve_passes_through_config_and_normalizes_none():
    config = Config(postgres_username="u")

    assert Config.resolve(config) is config
    assert Config.resolve(None).to_env_dict() == {}


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


def test_deprecated_manager_options_warn_when_they_supply_a_value(caplog):
    config = Config(datamesh_manager_api_key="legacy-key")

    with caplog.at_level("WARNING"):
        value = config.get_datamesh_manager_api_key()

    assert value == "legacy-key"
    messages = [record.getMessage() for record in caplog.records]
    assert any("DATAMESH_MANAGER_API_KEY is deprecated" in m and "ENTROPY_DATA_API_KEY" in m for m in messages)


def test_deprecated_manager_options_stay_silent_when_unset(caplog, monkeypatch):
    for name in ("DATAMESH_MANAGER_API_KEY", "DATACONTRACT_MANAGER_API_KEY"):
        monkeypatch.delenv(name, raising=False)

    with caplog.at_level("WARNING"):
        assert Config.model_construct().get_datamesh_manager_api_key() is None
        assert Config.model_construct().get_datacontract_manager_api_key() is None

    assert not caplog.records


def test_entropy_data_options_do_not_warn(caplog):
    with caplog.at_level("WARNING"):
        assert Config(entropy_data_api_key="key").get_entropy_data_api_key() == "key"

    assert not caplog.records
