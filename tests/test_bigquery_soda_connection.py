from unittest.mock import MagicMock

import yaml

from datacontract.engines.soda.connections.bigquery import to_bigquery_soda_configuration


def _make_server(type_="bigquery", project="my-project", dataset="my_dataset"):
    server = MagicMock()
    server.type = type_
    server.project = project
    server.dataset = dataset
    return server


def test_key_file_set(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_BIGQUERY_ACCOUNT_INFO_JSON_PATH", "/path/to/key.json")
    monkeypatch.delenv("DATACONTRACT_BIGQUERY_IMPERSONATION_ACCOUNT", raising=False)
    result = yaml.safe_load(to_bigquery_soda_configuration(_make_server()))
    ds = result["data_source bigquery"]
    assert ds["account_info_json_path"] == "/path/to/key.json"
    assert ds["auth_scopes"] == ["https://www.googleapis.com/auth/bigquery"]
    assert "use_context_auth" not in ds


def test_no_key_file_uses_context_auth(monkeypatch):
    monkeypatch.delenv("DATACONTRACT_BIGQUERY_ACCOUNT_INFO_JSON_PATH", raising=False)
    monkeypatch.delenv("DATACONTRACT_BIGQUERY_IMPERSONATION_ACCOUNT", raising=False)
    result = yaml.safe_load(to_bigquery_soda_configuration(_make_server()))
    ds = result["data_source bigquery"]
    assert ds["use_context_auth"] is True
    assert "account_info_json_path" not in ds
    assert "auth_scopes" not in ds


def test_impersonation_only(monkeypatch):
    monkeypatch.delenv("DATACONTRACT_BIGQUERY_ACCOUNT_INFO_JSON_PATH", raising=False)
    monkeypatch.setenv("DATACONTRACT_BIGQUERY_IMPERSONATION_ACCOUNT", "sa@project.iam.gserviceaccount.com")
    result = yaml.safe_load(to_bigquery_soda_configuration(_make_server()))
    ds = result["data_source bigquery"]
    assert ds["impersonation_account"] == "sa@project.iam.gserviceaccount.com"
    assert ds["use_context_auth"] is True


def test_key_file_and_impersonation(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_BIGQUERY_ACCOUNT_INFO_JSON_PATH", "/path/to/key.json")
    monkeypatch.setenv("DATACONTRACT_BIGQUERY_IMPERSONATION_ACCOUNT", "sa@project.iam.gserviceaccount.com")
    result = yaml.safe_load(to_bigquery_soda_configuration(_make_server()))
    ds = result["data_source bigquery"]
    assert ds["account_info_json_path"] == "/path/to/key.json"
    assert ds["impersonation_account"] == "sa@project.iam.gserviceaccount.com"


def test_adc_and_impersonation(monkeypatch):
    monkeypatch.delenv("DATACONTRACT_BIGQUERY_ACCOUNT_INFO_JSON_PATH", raising=False)
    monkeypatch.setenv("DATACONTRACT_BIGQUERY_IMPERSONATION_ACCOUNT", "sa@project.iam.gserviceaccount.com")
    result = yaml.safe_load(to_bigquery_soda_configuration(_make_server()))
    ds = result["data_source bigquery"]
    assert ds["use_context_auth"] is True
    assert ds["impersonation_account"] == "sa@project.iam.gserviceaccount.com"
    assert "account_info_json_path" not in ds
