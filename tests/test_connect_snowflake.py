"""Unit tests for how connect_ibis maps Snowflake connection parameters.

These do not hit Snowflake: ``ibis.snowflake.connect`` is patched and we only assert
which kwargs the dispatch passes for a given set of env vars.
"""

import os

import ibis
import pytest
from open_data_contract_standard.model import Server

from datacontract.engines.ibis.connections.connect import connect_ibis
from datacontract.model.run import Run

KEY_FILE = "/keys/rsa_key.p8"


@pytest.fixture
def env(monkeypatch):
    """Every DATACONTRACT_SNOWFLAKE_ variable is forwarded, so start from a clean slate."""
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


def _connect(run=None):
    return connect_ibis(run or Run.create_run(), data_contract=None, server=_server())


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

    assert captured_connect["login_timeout"] == "30"
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
