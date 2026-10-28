from unittest.mock import MagicMock

import pytest
from open_data_contract_standard.model import Server

from datacontract.config import Config
from datacontract.engines.ibis.connections import duckdb_connection as dc
from datacontract.model.exceptions import DataContractException

LOCATION = "azure://container@myaccount.blob.core.windows.net/path/*.parquet"
SPN = {"azure_tenant_id": "tenant", "azure_client_id": "client", "azure_client_secret": "secret"}


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for name in ["TENANT_ID", "CLIENT_ID", "CLIENT_SECRET", "CREDENTIAL_CHAIN"]:
        monkeypatch.delenv(f"DATACONTRACT_AZURE_{name}", raising=False)
    monkeypatch.setattr(dc, "_load_extension", lambda *a, **k: None)


def _run(monkeypatch, supported=True, **options):
    monkeypatch.setattr(dc, "_duckdb_supports_azure_credential_chain", lambda: supported)
    con = MagicMock()
    dc.setup_azure_connection(con, Server(type="azure", location=LOCATION), Config(**options))
    return con.sql.call_args[0][0]


def test_service_principal_when_all_options_set(monkeypatch):
    sql = _run(monkeypatch, **SPN)
    assert "PROVIDER SERVICE_PRINCIPAL" in sql
    assert "ACCOUNT_NAME 'myaccount'" in sql


def test_credential_chain_when_spn_missing(monkeypatch):
    sql = _run(monkeypatch)
    assert "PROVIDER CREDENTIAL_CHAIN" in sql
    assert "CHAIN '" not in sql
    assert "ACCOUNT_NAME 'myaccount'" in sql


def test_credential_chain_when_spn_partially_set(monkeypatch):
    assert "PROVIDER CREDENTIAL_CHAIN" in _run(monkeypatch, azure_tenant_id="tenant")


def test_credential_chain_custom_chain(monkeypatch):
    assert "CHAIN 'cli;env'" in _run(monkeypatch, azure_credential_chain="cli;env")


def test_credential_chain_is_escaped(monkeypatch):
    sql = _run(monkeypatch, azure_credential_chain="cli'); DROP")
    assert "CHAIN 'cli''); DROP'" in sql


def test_credential_chain_read_from_env(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_AZURE_CREDENTIAL_CHAIN", "managed_identity")
    assert "CHAIN 'managed_identity'" in _run(monkeypatch)


def test_old_duckdb_requires_spn_options(monkeypatch):
    with pytest.raises(DataContractException):
        _run(monkeypatch, supported=False)
