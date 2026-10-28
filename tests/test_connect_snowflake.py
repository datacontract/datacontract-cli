"""Unit tests for how connect_ibis maps Snowflake connection parameters.

These do not hit Snowflake: ``ibis.snowflake.connect`` is patched and we only assert
which kwargs the dispatch passes for a given set of env vars.
"""

import os
import warnings

import ibis
import pytest
from open_data_contract_standard.model import Server

from datacontract import Config
from datacontract.engines.ibis.connections.connect import connect_ibis
from datacontract.model.run import Run

KEY_FILE = "/keys/rsa_key.p8"


@pytest.fixture
def env(monkeypatch):
    """The tests assert the exact kwargs, so start from a clean slate."""
    for name in list(os.environ):
        if name.startswith("DATACONTRACT_SNOWFLAKE_"):
            monkeypatch.delenv(name, raising=False)
    return monkeypatch


@pytest.fixture
def captured_connect(monkeypatch):
    calls = {}

    def fake_connect(**kwargs):
        calls.update(kwargs)
        return "connection"

    monkeypatch.setattr(ibis.snowflake, "connect", fake_connect)
    return calls


def _server():
    return Server(server="snowflake", type="snowflake", account="abc-xy123", database="ORDER_DB", schema="ORDERS")


def _connect(run=None, config=None):
    return connect_ibis(run or Run.create_run(), data_contract=None, server=_server(), config=config)


def test_username_maps_to_the_drivers_user_parameter(env, captured_connect):
    env.setenv("DATACONTRACT_SNOWFLAKE_USERNAME", "analytics_user")

    _connect()

    assert captured_connect["user"] == "analytics_user"
    assert "username" not in captured_connect


def test_deprecated_private_key_path_maps_to_private_key_file(env, captured_connect):
    env.setenv("DATACONTRACT_SNOWFLAKE_PRIVATE_KEY_PATH", KEY_FILE)
    run = Run.create_run()

    _connect(run)

    assert captured_connect["private_key_file"] == KEY_FILE
    assert "private_key_path" not in captured_connect
    assert any("PRIVATE_KEY_PATH is deprecated" in log.message for log in run.logs)


def test_deprecated_private_key_passphrase_maps_to_private_key_file_pwd(env, captured_connect):
    env.setenv("DATACONTRACT_SNOWFLAKE_PRIVATE_KEY_PASSPHRASE", "secret")

    _connect()

    assert captured_connect["private_key_file_pwd"] == "secret"
    assert "private_key_passphrase" not in captured_connect


def test_deprecated_connection_timeout_maps_to_login_timeout(env, captured_connect):
    env.setenv("DATACONTRACT_SNOWFLAKE_CONNECTION_TIMEOUT", "30")

    _connect()

    assert captured_connect["login_timeout"] == 30
    assert "connection_timeout" not in captured_connect


def test_the_replacement_wins_over_the_deprecated_synonym(env, captured_connect):
    env.setenv("DATACONTRACT_SNOWFLAKE_PRIVATE_KEY_PATH", "/keys/old.p8")
    env.setenv("DATACONTRACT_SNOWFLAKE_PRIVATE_KEY_FILE", KEY_FILE)

    _connect()

    assert captured_connect["private_key_file"] == KEY_FILE


def test_current_names_are_passed_through_without_a_warning(env, captured_connect):
    env.setenv("DATACONTRACT_SNOWFLAKE_PRIVATE_KEY_FILE", KEY_FILE)
    env.setenv("DATACONTRACT_SNOWFLAKE_PRIVATE_KEY_FILE_PWD", "secret")
    run = Run.create_run()

    _connect(run)

    assert captured_connect["private_key_file"] == KEY_FILE
    assert captured_connect["private_key_file_pwd"] == "secret"
    assert not any("deprecated" in log.message for log in run.logs)


def test_timeouts_are_passed_as_integers(env, captured_connect):
    env.setenv("DATACONTRACT_SNOWFLAKE_LOGIN_TIMEOUT", "45")
    env.setenv("DATACONTRACT_SNOWFLAKE_NETWORK_TIMEOUT", "120")

    _connect()

    assert captured_connect["login_timeout"] == 45
    assert captured_connect["network_timeout"] == 120


def test_create_object_udfs_defaults_off_and_can_be_enabled(env, captured_connect):
    _connect()
    assert captured_connect["create_object_udfs"] is False

    env.setenv("DATACONTRACT_SNOWFLAKE_CREATE_OBJECT_UDFS", "true")
    _connect()
    assert captured_connect["create_object_udfs"] is True


def test_unknown_snowflake_variables_are_ignored_with_a_warning(env, captured_connect):
    env.setenv("DATACONTRACT_SNOWFLAKE_SESSION_PARAMETERS", '{"QUERY_TAG": "dc"}')
    run = Run.create_run()

    _connect(run)

    assert "session_parameters" not in captured_connect
    assert any("DATACONTRACT_SNOWFLAKE_SESSION_PARAMETERS" in log.message for log in run.logs)


def test_programmatic_config_reaches_the_connector(env, captured_connect):
    config = Config(
        snowflake_username="svc_test",
        snowflake_password="secret",
        snowflake_role="TESTER",
        snowflake_warehouse="COMPUTE_WH",
    )

    _connect(config=config)

    assert captured_connect["user"] == "svc_test"
    assert captured_connect["password"] == "secret"
    assert captured_connect["role"] == "TESTER"
    assert captured_connect["warehouse"] == "COMPUTE_WH"


def test_programmatic_config_wins_over_the_environment(env, captured_connect):
    env.setenv("DATACONTRACT_SNOWFLAKE_USERNAME", "from_env")

    _connect(config=Config(snowflake_username="from_config"))

    assert captured_connect["user"] == "from_config"


def test_env_variables_override_the_contract_server_details(env, captured_connect):
    """Setting DATACONTRACT_SNOWFLAKE_ACCOUNT alongside a server account used to raise
    ``TypeError: got multiple values for keyword argument 'account'``, then warn-and-ignore;
    it is a supported override now."""
    env.setenv("DATACONTRACT_SNOWFLAKE_ACCOUNT", "env-account")
    env.setenv("DATACONTRACT_SNOWFLAKE_DATABASE", "ENV_DB")
    env.setenv("DATACONTRACT_SNOWFLAKE_SCHEMA", "ENV_SCHEMA")

    _connect()

    assert captured_connect["account"] == "env-account"
    assert captured_connect["database"] == "ENV_DB"
    assert captured_connect["schema"] == "ENV_SCHEMA"


def test_every_option_reaches_a_parameter_the_installed_connector_knows(env, captured_connect):
    """The connector ignores parameter names it does not know, so one it renames or drops would silently stop
    working."""
    for name, value in {
        "USERNAME": "svc_test",
        "PASSWORD": "secret",
        "AUTHENTICATOR": "WORKLOAD_IDENTITY",
        "WORKLOAD_IDENTITY_PROVIDER": "OIDC",
        "ROLE": "TESTER",
        "TOKEN": "token",
        "TOKEN_FILE_PATH": "/var/run/secrets/tokens/snowflake-token",
        "PASSCODE": "123456",
        "PRIVATE_KEY": "TUlJ",
        "PRIVATE_KEY_FILE": KEY_FILE,
        "PRIVATE_KEY_FILE_PWD": "secret",
        "WAREHOUSE": "COMPUTE_WH",
        "HOST": "abc-xy123.snowflakecomputing.com",
        "LOGIN_TIMEOUT": "10",
        "NETWORK_TIMEOUT": "20",
        "SOCKET_TIMEOUT": "30",
        "PORT": "443",
    }.items():
        env.setenv(f"DATACONTRACT_SNOWFLAKE_{name}", value)

    _connect()

    parameters = {name: value for name, value in captured_connect.items() if name != "create_object_udfs"}
    assert parameters.keys() == {
        "user",
        "password",
        "authenticator",
        "workload_identity_provider",
        "role",
        "token",
        "token_file_path",
        "passcode",
        "private_key",
        "private_key_file",
        "private_key_file_pwd",
        "warehouse",
        "host",
        "login_timeout",
        "network_timeout",
        "socket_timeout",
        "port",
        "account",
        "database",
        "schema",
    }
    try:
        from snowflake.connector.connection_config import ConnectionConfig
    except ImportError:  # connector 4.x and earlier
        from snowflake.connector.connection import DEFAULT_CONFIGURATION

        assert parameters.keys() <= DEFAULT_CONFIGURATION.keys()
    else:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", DeprecationWarning)
            assert ConnectionConfig.from_kwargs(**parameters)._extra == {}
