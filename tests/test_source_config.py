"""Unit tests for programmatic source configs.

Covers the config objects themselves, the Snowflake dispatch in connect_ibis, and
that a config passed to ``DataContract`` actually reaches the connector. The
Databricks dispatch is covered in ``test_connect_databricks.py``, alongside the
env-driven cases it shares fixtures with.
"""

import os

import ibis
import pytest
from open_data_contract_standard.model import Server

from datacontract.data_contract import DataContract
from datacontract.engines.ibis.connections.connect import connect_ibis
from datacontract.imports.importer import Importer
from datacontract.model.run import Run
from datacontract.model.source_config import (
    DatabricksSourceConfig,
    SnowflakeSourceConfig,
    normalize_source_configs,
    select_source_config,
)


@pytest.fixture
def clean_env(monkeypatch):
    for name in list(os.environ):
        if name.startswith(("DATACONTRACT_DATABRICKS_", "DATACONTRACT_SNOWFLAKE_", "SNOWFLAKE_")):
            monkeypatch.delenv(name, raising=False)
    return monkeypatch


@pytest.fixture
def captured_snowflake(monkeypatch):
    calls = {}
    monkeypatch.setattr(ibis.snowflake, "connect", lambda **kwargs: calls.update(kwargs) or "connection")
    return calls


def _connect_snowflake(source_configs=(), **server_kwargs):
    return connect_ibis(
        Run.create_run(),
        data_contract=None,
        server=Server(type="snowflake", **server_kwargs),
        source_configs=source_configs,
    )


# --- the config object itself -------------------------------------------------


def test_config_falls_back_to_env_field_by_field(clean_env):
    clean_env.setenv("DATACONTRACT_DATABRICKS_TOKEN", "dapiFROM_ENV")
    clean_env.setenv("DATACONTRACT_DATABRICKS_SERVER_HOSTNAME", "env-host.databricks.com")

    config = DatabricksSourceConfig(http_path="/sql/1.0/warehouses/passed")

    assert config.http_path == "/sql/1.0/warehouses/passed"
    assert config.token.get_secret_value() == "dapiFROM_ENV"
    assert config.server_hostname == "env-host.databricks.com"


def test_secrets_are_not_exposed_by_repr(clean_env):
    config = DatabricksSourceConfig(token="dapiSECRET")

    assert "dapiSECRET" not in repr(config)
    assert "dapiSECRET" not in str(config.model_dump())


def test_undeclared_parameters_are_masked_but_still_reach_the_driver(clean_env):
    config = SnowflakeSourceConfig(connection_parameters={"oauth_client_secret": "sekret"})

    assert "sekret" not in repr(config)
    assert "sekret" not in str(config)
    assert "sekret" not in config.model_dump_json()
    assert config.driver_parameters()["oauth_client_secret"] == "sekret"


def test_a_config_survives_a_model_dump_round_trip(clean_env):
    """Masking the dump would silently turn every connection parameter into the mask itself."""
    config = SnowflakeSourceConfig(user="u", connection_parameters={"passcode": "123456", "login_timeout": 30})

    assert SnowflakeSourceConfig(**config.model_dump()).driver_parameters() == config.driver_parameters()


def test_unknown_field_is_rejected_without_echoing_its_value(clean_env):
    """A mistyped field name is usually a secret's; the rejected value must stay out of the error."""
    with pytest.raises(ValueError, match="tokne") as excinfo:
        DatabricksSourceConfig(tokne="dapiSECRET")

    assert "dapiSECRET" not in str(excinfo.value)
    # the chained pydantic error would carry it back into the traceback
    assert excinfo.value.__cause__ is None
    assert excinfo.value.__context__ is None


def test_aliased_field_is_settable_by_its_own_name(clean_env):
    """A validation_alias makes a field alias-only unless populate_by_name is set."""
    assert SnowflakeSourceConfig(user="jakob").user == "jakob"


def test_user_falls_back_to_the_username_variable(clean_env):
    clean_env.setenv("DATACONTRACT_SNOWFLAKE_USERNAME", "from-username")

    assert SnowflakeSourceConfig().user == "from-username"


def test_user_variable_wins_over_username(clean_env):
    clean_env.setenv("DATACONTRACT_SNOWFLAKE_USERNAME", "from-username")
    clean_env.setenv("DATACONTRACT_SNOWFLAKE_USER", "from-user")

    assert SnowflakeSourceConfig().user == "from-user"


def test_undeclared_variables_are_swept_into_connection_parameters(clean_env):
    clean_env.setenv("DATACONTRACT_SNOWFLAKE_WAREHOUSE", "COMPUTE_WH")
    clean_env.setenv("DATACONTRACT_SNOWFLAKE_PASSCODE", "123456")

    config = SnowflakeSourceConfig()

    assert config.warehouse == "COMPUTE_WH"
    assert config.connection_parameters == {"passcode": "123456"}


def test_no_declared_variable_is_swept(clean_env):
    """A declared variable swept as well would reach the driver twice, under two spellings."""
    for name in (
        "USER",
        "USERNAME",
        "PASSWORD",
        "ROLE",
        "WAREHOUSE",
        "AUTHENTICATOR",
        "CONNECTION_TIMEOUT",
        "PRIVATE_KEY",
        "PRIVATE_KEY_PASSPHRASE",
        "PRIVATE_KEY_PATH",
        "PRIVATE_KEY_FILE",
        "PRIVATE_KEY_FILE_PWD",
        "HOME",
        "CONNECTIONS_FILE",
        "DEFAULT_CONNECTION_NAME",
    ):
        clean_env.setenv(f"DATACONTRACT_SNOWFLAKE_{name}", "x")
    clean_env.setenv("DATACONTRACT_SNOWFLAKE_CREATE_OBJECT_UDFS", "true")
    clean_env.setenv("DATACONTRACT_SNOWFLAKE_CONNECTION_PARAMETERS", "{}")

    assert SnowflakeSourceConfig().connection_parameters == {}


def test_importer_only_variables_are_not_driver_parameters(clean_env):
    clean_env.setenv("DATACONTRACT_SNOWFLAKE_HOME", "/home/jakob/.snowflake")

    config = SnowflakeSourceConfig()

    assert config.home == "/home/jakob/.snowflake"
    assert "home" not in config.driver_parameters()


def test_connection_parameters_keep_non_string_values(clean_env):
    """The driver takes bools and ints for several parameters; forwarding must not stringify them."""
    config = SnowflakeSourceConfig(connection_parameters={"insecure_mode": True, "login_timeout": 30})

    assert config.driver_parameters()["insecure_mode"] is True
    assert config.driver_parameters()["login_timeout"] == 30


def test_bare_snowflake_home_variable_is_honoured(clean_env):
    clean_env.setenv("SNOWFLAKE_HOME", "/home/jakob/.snowflake")

    assert SnowflakeSourceConfig().home == "/home/jakob/.snowflake"


def test_normalize_accepts_a_single_config(clean_env):
    config = DatabricksSourceConfig(token="dapi")

    assert normalize_source_configs(config) == (config,)


def test_normalize_rejects_two_configs_of_one_family(clean_env):
    with pytest.raises(ValueError, match="more than one DatabricksSourceConfig"):
        normalize_source_configs([DatabricksSourceConfig(), DatabricksSourceConfig()])


def test_normalize_rejects_a_non_config(clean_env):
    with pytest.raises(ValueError, match="must be a source config object"):
        normalize_source_configs(["DATACONTRACT_DATABRICKS_TOKEN=dapi"])


def test_select_returns_a_bare_config_when_the_family_is_absent(clean_env):
    clean_env.setenv("DATACONTRACT_DATABRICKS_TOKEN", "dapiFROM_ENV")

    config = select_source_config((SnowflakeSourceConfig(user="jakob"),), DatabricksSourceConfig)

    assert config.token.get_secret_value() == "dapiFROM_ENV"


# --- snowflake, through connect_ibis -----------------------------------------


def test_snowflake_credentials_from_config(clean_env, captured_snowflake):
    configs = (SnowflakeSourceConfig(user="jakob", password="pw", warehouse="COMPUTE_WH"),)

    assert _connect_snowflake(configs, account="acc", database="db", schema="sch") == "connection"
    assert captured_snowflake["user"] == "jakob"
    assert captured_snowflake["password"] == "pw"
    assert captured_snowflake["warehouse"] == "COMPUTE_WH"
    assert captured_snowflake["account"] == "acc"


def test_snowflake_undeclared_parameters_reach_the_driver(clean_env, captured_snowflake):
    configs = (SnowflakeSourceConfig(user="jakob", connection_parameters={"passcode": "123456"}),)

    _connect_snowflake(configs, account="acc")

    assert captured_snowflake["passcode"] == "123456"


def test_snowflake_contract_account_wins_over_the_environment(clean_env, captured_snowflake):
    """Setting the variable used to collide with the contract's value and raise TypeError."""
    clean_env.setenv("DATACONTRACT_SNOWFLAKE_ACCOUNT", "from-env")

    _connect_snowflake(account="from-contract")

    assert captured_snowflake["account"] == "from-contract"


def test_snowflake_account_from_the_environment_when_the_contract_omits_it(clean_env, captured_snowflake):
    clean_env.setenv("DATACONTRACT_SNOWFLAKE_ACCOUNT", "from-env")

    _connect_snowflake()

    assert captured_snowflake["account"] == "from-env"


def test_snowflake_importer_only_variables_do_not_reach_the_driver(clean_env, captured_snowflake):
    clean_env.setenv("DATACONTRACT_SNOWFLAKE_HOME", "/home/jakob/.snowflake")

    _connect_snowflake(account="acc")

    assert "home" not in captured_snowflake


def test_snowflake_udf_creation_stays_off_by_default(clean_env, captured_snowflake):
    _connect_snowflake(account="acc")

    assert captured_snowflake["create_object_udfs"] is False


def test_snowflake_udf_creation_can_be_enabled(clean_env, captured_snowflake):
    clean_env.setenv("DATACONTRACT_SNOWFLAKE_CREATE_OBJECT_UDFS", "true")

    _connect_snowflake(account="acc")

    assert captured_snowflake["create_object_udfs"] is True


# --- the config reaches the connector from the public entry points ------------


def test_test_passes_the_config_down_to_the_connector(clean_env, monkeypatch):
    captured = {}

    def fake_connect_ibis(run, data_contract, server, *args, **kwargs):
        captured["source_configs"] = kwargs.get("source_configs", args[3] if len(args) > 3 else ())
        return None

    monkeypatch.setattr(
        "datacontract.engines.ibis.ibis_check_execute.connect_ibis",
        fake_connect_ibis,
    )
    config = DatabricksSourceConfig(token="dapiPASSED")

    DataContract(data_contract_file="fixtures/databricks-sql/datacontract.yaml", source_config=config).test()

    assert captured["source_configs"] == (config,)


def test_import_passes_only_the_importers_own_family_to_it(clean_env, monkeypatch):
    captured = {}

    def fake_import(unity_table_full_name_list, config):
        captured["config"] = config
        from datacontract.imports.odcs_helper import create_odcs

        return create_odcs()

    monkeypatch.setattr("datacontract.imports.unity_importer.import_unity_from_api", fake_import)
    config = DatabricksSourceConfig(token="dapiPASSED", server_hostname="h")

    DataContract.import_from_source(
        "unity",
        unity_table_full_name=["a.b.c"],
        source_config=[config, SnowflakeSourceConfig(password="pw")],
    )

    assert captured["config"] is config


def test_import_hands_no_config_to_an_importer_that_declares_no_family(clean_env, monkeypatch):
    captured = {}

    class FakeImporter(Importer):
        def import_source(self, source, import_args):
            captured["import_args"] = import_args
            from datacontract.imports.odcs_helper import create_odcs

            return create_odcs()

    monkeypatch.setattr("datacontract.data_contract.importer_factory.create", lambda format: FakeImporter(format))

    DataContract.import_from_source("sql", source="some.sql", source_config=SnowflakeSourceConfig(password="pw"))

    assert "source_config" not in captured["import_args"]


def test_unity_import_without_credentials_says_what_to_set(clean_env):
    """The actionable reason has to survive to the message the user sees, not just the attribute."""
    from datacontract.model.exceptions import DataContractException

    with pytest.raises(DataContractException) as excinfo:
        DataContract.import_from_source("unity", unity_table_full_name=["a.b.c"])

    assert "DATACONTRACT_DATABRICKS_TOKEN" in str(excinfo.value)
    assert "DatabricksSourceConfig" in str(excinfo.value)
