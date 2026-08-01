"""Tests for Config.require, the required-configuration lookup used by the connection builders."""

import pytest

from datacontract import Config
from datacontract.model.exceptions import DataContractException


def test_require_returns_value_when_set_in_the_environment(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_POSTGRES_USERNAME", "hello")

    assert Config.from_input(None).require("DATACONTRACT_POSTGRES_USERNAME", server_type="postgres") == "hello"


def test_require_returns_value_when_set_programmatically(monkeypatch):
    monkeypatch.delenv("DATACONTRACT_POSTGRES_USERNAME", raising=False)

    config = Config(postgres_username="hello")

    assert config.require("DATACONTRACT_POSTGRES_USERNAME", server_type="postgres") == "hello"


def test_require_raises_when_unset(monkeypatch):
    monkeypatch.delenv("DATACONTRACT_POSTGRES_USERNAME", raising=False)

    with pytest.raises(DataContractException) as exc_info:
        Config.from_input(None).require("DATACONTRACT_POSTGRES_USERNAME", server_type="postgres")

    reason = exc_info.value.reason
    assert "DATACONTRACT_POSTGRES_USERNAME" in reason
    assert "postgres" in reason
    assert exc_info.value.type == "postgres-connection"


def test_require_raises_when_empty(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_POSTGRES_USERNAME", "")

    with pytest.raises(DataContractException):
        Config.from_input(None).require("DATACONTRACT_POSTGRES_USERNAME", server_type="postgres")
