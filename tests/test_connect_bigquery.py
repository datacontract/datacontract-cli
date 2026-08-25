"""Unit tests for how connect_ibis resolves BigQuery credentials.

These do not hit BigQuery: ``ibis.bigquery.connect`` and the google-auth calls are
patched, and we only assert which credentials the dispatch passes along.
"""

from unittest.mock import MagicMock, patch

import pytest
from open_data_contract_standard.model import Server

from datacontract.engines.ibis.connections.connect import connect_ibis
from datacontract.model.run import Run

BIGQUERY_ENV_VARS = [
    "DATACONTRACT_BIGQUERY_ACCOUNT_INFO_JSON_PATH",
    "DATACONTRACT_BIGQUERY_BILLING_PROJECT",
    "DATACONTRACT_BIGQUERY_IMPERSONATION_ACCOUNT",
    "DATACONTRACT_BIGQUERY_PROJECT",
    "DATACONTRACT_BIGQUERY_DATASET",
]

SERVICE_ACCOUNT = "runner@my-project.iam.gserviceaccount.com"


@pytest.fixture
def env(monkeypatch):
    for name in BIGQUERY_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def _server():
    return Server(server="bigquery", type="bigquery", project="my-project", dataset="my_dataset")


def _connect():
    with patch("ibis.bigquery.connect") as connect:
        connect_ibis(Run.create_run(), None, _server())
    return connect.call_args.kwargs


def test_no_credentials_without_env_vars(env):
    """Nothing configured means ibis falls back to application default credentials."""
    kwargs = _connect()

    assert kwargs["project_id"] == "my-project"
    assert kwargs["dataset_id"] == "my_dataset"
    assert "credentials" not in kwargs


def test_impersonation_uses_the_ambient_credentials_as_source(env):
    env.setenv("DATACONTRACT_BIGQUERY_IMPERSONATION_ACCOUNT", SERVICE_ACCOUNT)
    source = MagicMock(name="adc")

    with patch("google.auth.default", return_value=(source, "my-project")) as default:
        with patch("google.auth.impersonated_credentials.Credentials") as impersonated:
            kwargs = _connect()

    default.assert_called_once()
    assert impersonated.call_args.kwargs["source_credentials"] is source
    assert impersonated.call_args.kwargs["target_principal"] == SERVICE_ACCOUNT
    assert kwargs["credentials"] is impersonated.return_value


def test_impersonation_uses_the_key_file_as_source_when_set(env, tmp_path):
    key_file = tmp_path / "key.json"
    key_file.write_text("{}")
    env.setenv("DATACONTRACT_BIGQUERY_ACCOUNT_INFO_JSON_PATH", str(key_file))
    env.setenv("DATACONTRACT_BIGQUERY_IMPERSONATION_ACCOUNT", SERVICE_ACCOUNT)
    key_credentials = MagicMock(name="key")

    with patch(
        "google.oauth2.service_account.Credentials.from_service_account_file",
        return_value=key_credentials,
    ):
        with patch("google.auth.default") as default:
            with patch("google.auth.impersonated_credentials.Credentials") as impersonated:
                kwargs = _connect()

    default.assert_not_called()
    assert impersonated.call_args.kwargs["source_credentials"] is key_credentials
    assert kwargs["credentials"] is impersonated.return_value


def test_billing_project_client_uses_the_impersonated_credentials(env):
    env.setenv("DATACONTRACT_BIGQUERY_BILLING_PROJECT", "my-billing-project")
    env.setenv("DATACONTRACT_BIGQUERY_IMPERSONATION_ACCOUNT", SERVICE_ACCOUNT)

    with patch("google.auth.default", return_value=(MagicMock(), "my-project")):
        with patch("google.auth.impersonated_credentials.Credentials") as impersonated:
            with patch("google.cloud.bigquery.Client") as client:
                kwargs = _connect()

    assert client.call_args.kwargs["project"] == "my-billing-project"
    assert client.call_args.kwargs["credentials"] is impersonated.return_value
    assert kwargs["client"] is client.return_value
    # ibis prefers client.project over project_id when a client is passed, so
    # dataset_id must carry the data project itself or queries resolve
    # against the billing project instead.
    assert kwargs["dataset_id"] == "my-project.my_dataset"


def test_env_variables_override_the_contract_project_and_dataset(env):
    env.setenv("DATACONTRACT_BIGQUERY_PROJECT", "env-project")
    env.setenv("DATACONTRACT_BIGQUERY_DATASET", "env_dataset")

    kwargs = _connect()

    assert kwargs["project_id"] == "env-project"
    assert kwargs["dataset_id"] == "env_dataset"
