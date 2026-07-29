"""Tests for resolving the Redshift login (static password or IAM)."""

from unittest.mock import MagicMock, patch

import pytest

from datacontract.engines.ibis.connections.redshift_credentials import resolve_redshift_login
from datacontract.model.exceptions import DataContractException

SERVERLESS_HOST = "my-workgroup.123456789012.us-east-1.redshift-serverless.amazonaws.com"
PROVISIONED_HOST = "my-cluster.123456789012.eu-central-1.redshift.amazonaws.com"

REDSHIFT_ENV = [
    "DATACONTRACT_REDSHIFT_AUTHENTICATION",
    "DATACONTRACT_REDSHIFT_USERNAME",
    "DATACONTRACT_REDSHIFT_PASSWORD",
    "DATACONTRACT_REDSHIFT_SSLMODE",
    "DATACONTRACT_REDSHIFT_DB_USER",
    "DATACONTRACT_REDSHIFT_DB_GROUPS",
    "DATACONTRACT_REDSHIFT_AUTO_CREATE",
    "DATACONTRACT_REDSHIFT_DURATION_SECONDS",
    "DATACONTRACT_REDSHIFT_REGION",
    "DATACONTRACT_REDSHIFT_WORKGROUP",
    "DATACONTRACT_REDSHIFT_CLUSTER_IDENTIFIER",
    "DATACONTRACT_S3_REGION",
    "DATACONTRACT_S3_ACCESS_KEY_ID",
    "DATACONTRACT_S3_SECRET_ACCESS_KEY",
    "DATACONTRACT_S3_SESSION_TOKEN",
]


@pytest.fixture(autouse=True)
def clean_env(monkeypatch, tmp_path):
    """A developer's own AWS/Redshift variables must not leak into these tests.

    Authentication is now inferred, so an ambient `aws sso login` would other-
    wise decide the outcome. Point boto3 at empty config files and switch the
    metadata service off so its chain resolves nothing, deterministically.
    """
    for name in (
        "AWS_PROFILE",
        "AWS_DEFAULT_PROFILE",
        "AWS_ACCESS_KEY_ID",
        "AWS_SECRET_ACCESS_KEY",
        "AWS_SESSION_TOKEN",
    ):
        monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("AWS_CONFIG_FILE", str(tmp_path / "no-config"))
    monkeypatch.setenv("AWS_SHARED_CREDENTIALS_FILE", str(tmp_path / "no-credentials"))
    monkeypatch.setenv("AWS_EC2_METADATA_DISABLED", "true")
    for name in REDSHIFT_ENV:
        monkeypatch.delenv(name, raising=False)


@pytest.fixture
def boto3_client():
    client = MagicMock()
    client.get_credentials.return_value = {"dbUser": "IAM:alice", "dbPassword": "serverless-secret"}
    client.get_cluster_credentials.return_value = {"DbUser": "IAMA:alice", "DbPassword": "legacy-secret"}
    client.get_cluster_credentials_with_iam.return_value = {"DbUser": "IAM:alice", "DbPassword": "iam-secret"}
    with patch("boto3.client", return_value=client) as factory:
        client.factory = factory
        yield client


def test_password_authentication_is_the_default(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_REDSHIFT_USERNAME", "awsuser")
    monkeypatch.setenv("DATACONTRACT_REDSHIFT_PASSWORD", "mysecret")

    login = resolve_redshift_login(SERVERLESS_HOST, "dev")

    assert (login.user, login.password) == ("awsuser", "mysecret")
    # Unset by default, so an existing setup keeps psycopg's own sslmode handling.
    assert login.sslmode is None


def test_password_authentication_requires_a_username(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_REDSHIFT_PASSWORD", "secret")

    with pytest.raises(DataContractException) as exc_info:
        resolve_redshift_login(SERVERLESS_HOST, "dev")

    assert "DATACONTRACT_REDSHIFT_USERNAME" in exc_info.value.reason


def test_iam_serverless_derives_workgroup_and_region_from_the_host(monkeypatch, boto3_client):
    monkeypatch.setenv("DATACONTRACT_REDSHIFT_AUTHENTICATION", "iam")

    login = resolve_redshift_login(SERVERLESS_HOST, "dev")

    assert (login.user, login.password) == ("IAM:alice", "serverless-secret")
    assert login.sslmode == "require"
    assert boto3_client.factory.call_args.args[0] == "redshift-serverless"
    assert boto3_client.factory.call_args.kwargs["region_name"] == "us-east-1"
    boto3_client.get_credentials.assert_called_once_with(workgroupName="my-workgroup", dbName="dev")


def test_iam_provisioned_derives_the_db_user_from_the_caller_identity(monkeypatch, boto3_client):
    monkeypatch.setenv("DATACONTRACT_REDSHIFT_AUTHENTICATION", "iam")

    login = resolve_redshift_login(PROVISIONED_HOST, "dev")

    assert (login.user, login.password) == ("IAM:alice", "iam-secret")
    assert boto3_client.factory.call_args.args[0] == "redshift"
    assert boto3_client.factory.call_args.kwargs["region_name"] == "eu-central-1"
    boto3_client.get_cluster_credentials_with_iam.assert_called_once_with(ClusterIdentifier="my-cluster", DbName="dev")
    boto3_client.get_cluster_credentials.assert_not_called()


def test_iam_provisioned_uses_the_legacy_api_when_a_db_user_is_configured(monkeypatch, boto3_client):
    monkeypatch.setenv("DATACONTRACT_REDSHIFT_AUTHENTICATION", "iam")
    monkeypatch.setenv("DATACONTRACT_REDSHIFT_USERNAME", "analyst")
    monkeypatch.setenv("DATACONTRACT_REDSHIFT_AUTO_CREATE", "true")
    monkeypatch.setenv("DATACONTRACT_REDSHIFT_DB_GROUPS", "readers, writers")
    monkeypatch.setenv("DATACONTRACT_REDSHIFT_DURATION_SECONDS", "900")

    login = resolve_redshift_login(PROVISIONED_HOST, "dev")

    assert (login.user, login.password) == ("IAMA:alice", "legacy-secret")
    boto3_client.get_cluster_credentials.assert_called_once_with(
        DbUser="analyst",
        ClusterIdentifier="my-cluster",
        DbName="dev",
        DurationSeconds=900,
        AutoCreate=True,
        DbGroups=["readers", "writers"],
    )


def test_iam_reuses_the_athena_s3_credentials_and_region(monkeypatch, boto3_client):
    monkeypatch.setenv("DATACONTRACT_REDSHIFT_AUTHENTICATION", "iam")
    monkeypatch.setenv("DATACONTRACT_S3_REGION", "us-west-2")
    monkeypatch.setenv("DATACONTRACT_S3_ACCESS_KEY_ID", "AKIA...")
    monkeypatch.setenv("DATACONTRACT_S3_SECRET_ACCESS_KEY", "secret")
    monkeypatch.setenv("DATACONTRACT_S3_SESSION_TOKEN", "token")

    resolve_redshift_login(SERVERLESS_HOST, "dev")

    kwargs = boto3_client.factory.call_args.kwargs
    assert kwargs["region_name"] == "us-west-2"
    assert kwargs["aws_access_key_id"] == "AKIA..."
    assert kwargs["aws_secret_access_key"] == "secret"
    assert kwargs["aws_session_token"] == "token"


def test_iam_falls_back_to_the_ambient_aws_chain(monkeypatch, boto3_client):
    """Without explicit keys, boto3 resolves aws sso login / AWS_PROFILE / instance roles."""
    monkeypatch.setenv("DATACONTRACT_REDSHIFT_AUTHENTICATION", "iam")

    resolve_redshift_login(SERVERLESS_HOST, "dev")

    kwargs = boto3_client.factory.call_args.kwargs
    assert kwargs["aws_access_key_id"] is None
    assert kwargs["aws_secret_access_key"] is None
    assert kwargs["aws_session_token"] is None


def test_iam_overrides_win_over_the_host(monkeypatch, boto3_client):
    """Custom domains and VPC endpoints don't follow the standard endpoint shape."""
    monkeypatch.setenv("DATACONTRACT_REDSHIFT_AUTHENTICATION", "iam")
    monkeypatch.setenv("DATACONTRACT_REDSHIFT_WORKGROUP", "other-workgroup")
    monkeypatch.setenv("DATACONTRACT_REDSHIFT_REGION", "ap-south-1")

    resolve_redshift_login("redshift.internal.example.com", "dev")

    assert boto3_client.factory.call_args.kwargs["region_name"] == "ap-south-1"
    boto3_client.get_credentials.assert_called_once_with(workgroupName="other-workgroup", dbName="dev")


def test_iam_reports_an_unrecognizable_endpoint(monkeypatch, boto3_client):
    monkeypatch.setenv("DATACONTRACT_REDSHIFT_AUTHENTICATION", "iam")

    with pytest.raises(DataContractException) as exc_info:
        resolve_redshift_login("redshift.internal.example.com", "dev")

    assert "DATACONTRACT_REDSHIFT_WORKGROUP" in exc_info.value.reason
    assert "DATACONTRACT_REDSHIFT_CLUSTER_IDENTIFIER" in exc_info.value.reason


def test_iam_sslmode_can_be_overridden(monkeypatch, boto3_client):
    monkeypatch.setenv("DATACONTRACT_REDSHIFT_AUTHENTICATION", "iam")
    monkeypatch.setenv("DATACONTRACT_REDSHIFT_SSLMODE", "verify-full")

    assert resolve_redshift_login(SERVERLESS_HOST, "dev").sslmode == "verify-full"


def test_iam_wraps_an_aws_failure_with_the_api_name(monkeypatch, boto3_client):
    monkeypatch.setenv("DATACONTRACT_REDSHIFT_AUTHENTICATION", "iam")
    boto3_client.get_credentials.side_effect = RuntimeError("AccessDeniedException")

    with pytest.raises(DataContractException) as exc_info:
        resolve_redshift_login(SERVERLESS_HOST, "dev")

    assert "redshift-serverless:GetCredentials" in exc_info.value.reason
    assert "AccessDeniedException" in exc_info.value.reason


def test_invalid_duration_is_reported(monkeypatch, boto3_client):
    monkeypatch.setenv("DATACONTRACT_REDSHIFT_AUTHENTICATION", "iam")
    monkeypatch.setenv("DATACONTRACT_REDSHIFT_DURATION_SECONDS", "an hour")

    with pytest.raises(DataContractException) as exc_info:
        resolve_redshift_login(SERVERLESS_HOST, "dev")

    assert "DATACONTRACT_REDSHIFT_DURATION_SECONDS" in exc_info.value.reason


def test_unsupported_authentication_mode(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_REDSHIFT_AUTHENTICATION", "kerberos")

    with pytest.raises(DataContractException) as exc_info:
        resolve_redshift_login(SERVERLESS_HOST, "dev")

    assert "Supported values are: password, iam" in exc_info.value.reason


# ---------------------------------------------------------------------------
# Inferring the authentication method
# ---------------------------------------------------------------------------
def test_password_is_inferred_from_the_password_variable(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_REDSHIFT_USERNAME", "awsuser")
    monkeypatch.setenv("DATACONTRACT_REDSHIFT_PASSWORD", "secret")

    login = resolve_redshift_login(SERVERLESS_HOST, "dev")

    assert (login.user, login.password) == ("awsuser", "secret")


def test_iam_is_inferred_from_an_aws_session(monkeypatch):
    """No Redshift variable at all: AWS credentials are enough."""
    monkeypatch.setenv("DATACONTRACT_S3_ACCESS_KEY_ID", "AKIA_TEST")
    monkeypatch.setenv("DATACONTRACT_S3_SECRET_ACCESS_KEY", "secret")
    aws = MagicMock()
    aws.get_credentials.return_value = {"dbUser": "IAM:alice", "dbPassword": "temporary"}

    with patch("boto3.client", return_value=aws):
        login = resolve_redshift_login(SERVERLESS_HOST, "dev")

    assert (login.user, login.password) == ("IAM:alice", "temporary")


def test_a_username_alone_does_not_force_password_auth(monkeypatch):
    """IAM on a provisioned cluster reads USERNAME as the database user."""
    monkeypatch.setenv("DATACONTRACT_REDSHIFT_USERNAME", "awsuser")
    monkeypatch.setenv("DATACONTRACT_S3_ACCESS_KEY_ID", "AKIA_TEST")
    monkeypatch.setenv("DATACONTRACT_S3_SECRET_ACCESS_KEY", "secret")
    aws = MagicMock()
    aws.get_cluster_credentials.return_value = {"DbUser": "IAM:awsuser", "DbPassword": "temporary"}

    with patch("boto3.client", return_value=aws):
        login = resolve_redshift_login(PROVISIONED_HOST, "dev")

    assert login.user == "IAM:awsuser"
    aws.get_cluster_credentials.assert_called_once()


def test_the_override_still_wins(monkeypatch):
    """The explicit variable stays available when inference guesses wrong."""
    monkeypatch.setenv("DATACONTRACT_REDSHIFT_AUTHENTICATION", "password")
    monkeypatch.setenv("DATACONTRACT_REDSHIFT_USERNAME", "awsuser")

    login = resolve_redshift_login(SERVERLESS_HOST, "dev")

    assert (login.user, login.password) == ("awsuser", None)


def test_no_password_and_no_aws_session_explains_both_options():
    with pytest.raises(DataContractException) as exc_info:
        resolve_redshift_login(SERVERLESS_HOST, "dev")

    reason = exc_info.value.reason
    assert "DATACONTRACT_REDSHIFT_PASSWORD" in reason
    assert "aws sso login" in reason
