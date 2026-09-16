import sys
import types

import pytest
from open_data_contract_standard.model import Server

from datacontract.engines.hana.hana_connection import get_connection
from datacontract.model.exceptions import DataContractException


class FakeDbApi:
    def __init__(self):
        self.kwargs = None

    def connect(self, **kwargs):
        self.kwargs = kwargs
        return object()


def install_hdbcli(monkeypatch):
    dbapi = FakeDbApi()
    hdbcli = types.ModuleType("hdbcli")
    hdbcli.dbapi = dbapi
    monkeypatch.setitem(sys.modules, "hdbcli", hdbcli)
    return dbapi


def hana_server(**kwargs):
    defaults = {"type": "hana", "host": "hana.example.com", "schema": "SALES"}
    defaults.update(kwargs)
    return Server(**defaults)


def test_connection_missing_username(monkeypatch):
    install_hdbcli(monkeypatch)
    monkeypatch.delenv("DATACONTRACT_HANA_USERNAME", raising=False)
    monkeypatch.setenv("DATACONTRACT_HANA_PASSWORD", "secret")

    with pytest.raises(DataContractException) as exc_info:
        get_connection(hana_server())

    assert exc_info.value.type == "hana-connection"


def test_connection_missing_password(monkeypatch):
    install_hdbcli(monkeypatch)
    monkeypatch.setenv("DATACONTRACT_HANA_USERNAME", "user")
    monkeypatch.delenv("DATACONTRACT_HANA_PASSWORD", raising=False)

    with pytest.raises(DataContractException) as exc_info:
        get_connection(hana_server())

    assert exc_info.value.type == "hana-connection"


def test_connection_default_port_443(monkeypatch):
    dbapi = install_hdbcli(monkeypatch)
    monkeypatch.setenv("DATACONTRACT_HANA_USERNAME", "user")
    monkeypatch.setenv("DATACONTRACT_HANA_PASSWORD", "secret")

    get_connection(hana_server())

    assert dbapi.kwargs["port"] == 443


def test_connection_encrypt_default_true(monkeypatch):
    dbapi = install_hdbcli(monkeypatch)
    monkeypatch.setenv("DATACONTRACT_HANA_USERNAME", "user")
    monkeypatch.setenv("DATACONTRACT_HANA_PASSWORD", "secret")
    monkeypatch.delenv("DATACONTRACT_HANA_ENCRYPT", raising=False)

    get_connection(hana_server())

    assert dbapi.kwargs["encrypt"] is True


def test_connection_encrypt_env_override(monkeypatch):
    dbapi = install_hdbcli(monkeypatch)
    monkeypatch.setenv("DATACONTRACT_HANA_USERNAME", "user")
    monkeypatch.setenv("DATACONTRACT_HANA_PASSWORD", "secret")
    monkeypatch.setenv("DATACONTRACT_HANA_ENCRYPT", "false")

    get_connection(hana_server())

    assert dbapi.kwargs["encrypt"] is False


def test_connection_ssl_validate_certificate(monkeypatch):
    dbapi = install_hdbcli(monkeypatch)
    monkeypatch.setenv("DATACONTRACT_HANA_USERNAME", "user")
    monkeypatch.setenv("DATACONTRACT_HANA_PASSWORD", "secret")
    monkeypatch.setenv("DATACONTRACT_HANA_SSL_VALIDATE_CERTIFICATE", "0")
    monkeypatch.setenv("DATACONTRACT_HANA_SSL_HOSTNAME_IN_CERTIFICATE", "*.example.com")

    get_connection(hana_server(port=30015))

    assert dbapi.kwargs["sslValidateCertificate"] is False
    assert dbapi.kwargs["sslHostnameInCertificate"] == "*.example.com"
    assert dbapi.kwargs["port"] == 30015
