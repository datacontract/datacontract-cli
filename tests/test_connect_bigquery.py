"""Unit tests for how connect_ibis resolves BigQuery credentials.

These do not hit BigQuery: ``ibis.bigquery.connect`` and the google-auth calls are
patched, and we only assert which credentials the dispatch passes along.
"""

from unittest.mock import MagicMock, patch

import pytest
from open_data_contract_standard.model import Server

from datacontract.engines.ibis.connections.connect import connect_ibis
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import Run

BIGQUERY_ENV_VARS = [
    "DATACONTRACT_BIGQUERY_ACCOUNT_INFO_JSON_PATH",
    "DATACONTRACT_BIGQUERY_BILLING_PROJECT",
    "DATACONTRACT_BIGQUERY_IMPERSONATION_ACCOUNT",
    "DATACONTRACT_BIGQUERY_LOCATION",
    "DATACONTRACT_BIGQUERY_KMS_KEY_NAME",
    "DATACONTRACT_BIGQUERY_PROJECT",
    "DATACONTRACT_BIGQUERY_DATASET",
]

SERVICE_ACCOUNT = "runner@my-project.iam.gserviceaccount.com"
KMS_KEY = "projects/my-kms-project/locations/europe-west3/keyRings/my-ring/cryptoKeys/my-key"


@pytest.fixture
def env(monkeypatch):
    for name in BIGQUERY_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def _server(**overrides):
    kwargs = dict(server="bigquery", type="bigquery", project="my-project", dataset="my_dataset")
    return Server(**{**kwargs, **overrides})


def _connect(**overrides):
    with patch("ibis.bigquery.connect") as connect:
        connect_ibis(Run.create_run(), None, _server(**overrides))
    return connect.call_args.kwargs


def _connect_ibis(**overrides):
    """Connect through the real ibis BigQuery backend, stubbing out only the
    Google clients, so the assertions cover how ibis reads our arguments.
    Returns the connection and the patched ``bigquery.Client``.
    Without credentials, ibis would look up application default credentials."""
    with patch("ibis.backends.bigquery.bq.Client") as client:
        client.return_value.default_query_job_config = None
        with patch("ibis.backends.bigquery.bqstorage.BigQueryReadClient"):
            with patch("ibis.backends.bigquery.pydata_google_auth.default", return_value=(MagicMock(), None)):
                return connect_ibis(Run.create_run(), None, _server(**overrides)), client


def _custom_properties(**values):
    return [dict(property=name, value=value) for name, value in values.items()]


def test_no_credentials_without_env_vars(env):
    """Nothing configured means ibis falls back to application default credentials."""
    kwargs = _connect()

    assert kwargs["project_id"] == "my-project"
    assert kwargs["dataset_id"] == "my-project.my_dataset"
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


def test_billing_project_keeps_the_contract_project_as_the_data_project(env):
    """The billing project pays for the query jobs; the tables still live in the
    contract's project. Drives the real ibis backend, as asserting our own kwargs
    would not catch ibis resolving the data project differently."""
    env.setenv("DATACONTRACT_BIGQUERY_BILLING_PROJECT", "my-billing-project")
    env.setenv("DATACONTRACT_BIGQUERY_IMPERSONATION_ACCOUNT", SERVICE_ACCOUNT)

    with patch("google.auth.default", return_value=(MagicMock(), "my-project")):
        with patch("google.auth.impersonated_credentials.Credentials") as impersonated:
            con, client = _connect_ibis()

    assert con.data_project == "my-project"
    assert con.billing_project == "my-billing-project"
    assert con.dataset == "my_dataset"
    assert client.call_args.kwargs["credentials"] is impersonated.return_value


def test_env_variables_override_the_contract_project_and_dataset(env):
    env.setenv("DATACONTRACT_BIGQUERY_PROJECT", "env-project")
    env.setenv("DATACONTRACT_BIGQUERY_DATASET", "env_dataset")

    kwargs = _connect()

    assert kwargs["project_id"] == "env-project"
    assert kwargs["dataset_id"] == "env-project.env_dataset"


def test_dataset_is_required(env):
    with pytest.raises(DataContractException) as e:
        _connect(dataset=None)

    assert e.value.name == "missing_dataset"


def test_project_is_left_to_ibis_to_resolve_from_the_credentials(env):
    """Without a project, ibis falls back to the project of the credentials."""
    kwargs = _connect(project=None)

    assert kwargs["project_id"] is None
    assert kwargs["dataset_id"] == "my_dataset"


def test_project_is_required_with_a_billing_project(env):
    """The data project cannot be resolved from the credentials once ``project_id``
    carries the billing project."""
    env.setenv("DATACONTRACT_BIGQUERY_BILLING_PROJECT", "my-billing-project")

    with pytest.raises(DataContractException) as e:
        _connect(project=None)

    assert e.value.name == "missing_project"


def test_no_location_or_kms_key_without_configuration(env):
    con, client = _connect_ibis()

    assert client.call_args.kwargs["location"] is None
    assert con.client.default_query_job_config.destination_encryption_configuration is None


def test_location_comes_from_env_variable(env):
    env.setenv("DATACONTRACT_BIGQUERY_LOCATION", "europe-west3")

    assert _connect()["location"] == "europe-west3"


def test_location_comes_from_server_custom_property(env):
    kwargs = _connect(customProperties=_custom_properties(location="europe-west3"))

    assert kwargs["location"] == "europe-west3"


def test_env_variable_wins_over_custom_property(env):
    env.setenv("DATACONTRACT_BIGQUERY_LOCATION", "europe-west4")

    kwargs = _connect(customProperties=_custom_properties(location="europe-west3"))

    assert kwargs["location"] == "europe-west4"


def test_kms_key_is_set_on_the_default_query_job_config(env):
    """Every query ibis runs merges the client's default query job config, so a key
    set there also encrypts the anonymous tables that hold the query results."""
    env.setenv("DATACONTRACT_BIGQUERY_KMS_KEY_NAME", KMS_KEY)

    con, _ = _connect_ibis()

    assert con.client.default_query_job_config.destination_encryption_configuration.kms_key_name == KMS_KEY


def test_kms_key_comes_from_server_custom_property(env):
    con, _ = _connect_ibis(customProperties=_custom_properties(kmsKeyName=KMS_KEY))

    assert con.client.default_query_job_config.destination_encryption_configuration.kms_key_name == KMS_KEY
