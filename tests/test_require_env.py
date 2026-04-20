import pytest

from datacontract.model.exceptions import DataContractException, require_env


def test_require_env_returns_value_when_set(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_TEST_VAR", "hello")

    assert require_env("DATACONTRACT_TEST_VAR", server_type="postgres") == "hello"


def test_require_env_raises_when_unset(monkeypatch):
    monkeypatch.delenv("DATACONTRACT_TEST_VAR", raising=False)

    with pytest.raises(DataContractException) as exc_info:
        require_env("DATACONTRACT_TEST_VAR", server_type="postgres")

    reason = exc_info.value.reason
    assert "DATACONTRACT_TEST_VAR" in reason
    assert "postgres" in reason
    assert exc_info.value.type == "postgres-connection"


def test_require_env_raises_when_empty(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_TEST_VAR", "")

    with pytest.raises(DataContractException):
        require_env("DATACONTRACT_TEST_VAR", server_type="postgres")
