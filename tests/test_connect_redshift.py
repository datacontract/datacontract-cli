"""Unit tests for Redshift auth-method selection in connect_ibis.

These do not hit Redshift or AWS: ``ibis.postgres.connect`` and the boto3 client
are patched, and we only assert which connection kwargs the dispatch passes for
a given set of env vars. The point is that ``test`` authenticates exactly like
``import redshift`` — both go through ``resolve_redshift_login``.
"""

from unittest.mock import MagicMock, patch

import ibis
import pytest
from open_data_contract_standard.model import Server

from datacontract.engines.ibis.connections.connect import connect_ibis
from datacontract.model.run import Run

HOST = "my-workgroup.123456789012.us-east-1.redshift-serverless.amazonaws.com"

REDSHIFT_ENV_VARS = [
    "DATACONTRACT_REDSHIFT_AUTHENTICATION",
    "DATACONTRACT_REDSHIFT_USERNAME",
    "DATACONTRACT_REDSHIFT_PASSWORD",
    "DATACONTRACT_REDSHIFT_SSLMODE",
    "DATACONTRACT_S3_REGION",
]


@pytest.fixture
def env(monkeypatch):
    for name in REDSHIFT_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


@pytest.fixture
def captured_connect(monkeypatch):
    calls = {}

    def fake_connect(**kwargs):
        calls.update(kwargs)
        return MagicMock()

    monkeypatch.setattr(ibis.postgres, "connect", fake_connect)
    return calls


def _server():
    return Server(type="redshift", host=HOST, port=5439, database="dev", schema="analytics")


def test_password_authentication(env, captured_connect):
    env.setenv("DATACONTRACT_REDSHIFT_USERNAME", "awsuser")
    env.setenv("DATACONTRACT_REDSHIFT_PASSWORD", "mysecret")

    connect_ibis(Run.create_run(), None, _server())

    assert captured_connect["user"] == "awsuser"
    assert captured_connect["password"] == "mysecret"
    assert captured_connect["host"] == HOST
    assert captured_connect["port"] == 5439
    assert captured_connect["database"] == "dev"
    assert captured_connect["schema"] == "analytics"
    assert "sslmode" not in captured_connect
    # Redshift reports client_encoding as "UNICODE", which psycopg can't map.
    assert captured_connect["client_encoding"] == "utf8"


def test_iam_authentication_uses_temporary_credentials(env, captured_connect):
    env.setenv("DATACONTRACT_REDSHIFT_AUTHENTICATION", "iam")
    client = MagicMock()
    client.get_credentials.return_value = {"dbUser": "IAM:alice", "dbPassword": "temporary"}

    with patch("boto3.client", return_value=client):
        connect_ibis(Run.create_run(), None, _server())

    assert captured_connect["user"] == "IAM:alice"
    assert captured_connect["password"] == "temporary"
    assert captured_connect["sslmode"] == "require"
    client.get_credentials.assert_called_once_with(workgroupName="my-workgroup", dbName="dev")
