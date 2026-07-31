"""Unit tests for how connect_ibis builds the Athena connection.

These do not hit Athena or AWS: ``ibis.athena.connect`` is patched, and we only
assert which connection kwargs the dispatch passes for a given server block and
set of env vars.
"""

from unittest.mock import patch

import pytest
from open_data_contract_standard.model import Server

from datacontract.engines.ibis.connections.connect import connect_ibis
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import Run

ATHENA_ENV_VARS = [
    "DATACONTRACT_S3_REGION",
    "DATACONTRACT_S3_ACCESS_KEY_ID",
    "DATACONTRACT_S3_SECRET_ACCESS_KEY",
    "DATACONTRACT_S3_SESSION_TOKEN",
]

STAGING_DIR = "s3://my-bucket/athena-results/"


@pytest.fixture
def env(monkeypatch):
    for name in ATHENA_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def _server(**kwargs):
    return Server(server="athena", type="athena", schema="my_database", stagingDir=STAGING_DIR, **kwargs)


def _connect(server):
    with patch("ibis.athena.connect") as connect:
        connect_ibis(Run.create_run(), None, server)
    return connect.call_args.kwargs


def test_region_comes_from_the_server_block(env):
    """regionName is documented as part of the servers block, so it must be used."""
    kwargs = _connect(_server(regionName="eu-central-1"))

    assert kwargs["region_name"] == "eu-central-1"


def test_environment_region_wins_over_the_server_block(env):
    env.setenv("DATACONTRACT_S3_REGION", "us-east-1")

    kwargs = _connect(_server(regionName="eu-central-1"))

    assert kwargs["region_name"] == "us-east-1"


def test_staging_dir_and_schema_are_passed(env):
    kwargs = _connect(_server(regionName="eu-central-1"))

    assert kwargs["s3_staging_dir"] == STAGING_DIR
    assert kwargs["schema_name"] == "my_database"


def test_catalog_comes_from_the_server_block(env):
    """catalog is documented as part of the servers block, so it must be used."""
    kwargs = _connect(_server(catalog="my_catalog"))

    assert kwargs["catalog_name"] == "my_catalog"


def test_catalog_is_omitted_when_not_set(env):
    """Without a catalog, pyathena's own `awsdatacatalog` default applies."""
    kwargs = _connect(_server())

    assert "catalog_name" not in kwargs


def test_credentials_come_from_the_s3_variables(env):
    env.setenv("DATACONTRACT_S3_ACCESS_KEY_ID", "AKIA_TEST")
    env.setenv("DATACONTRACT_S3_SECRET_ACCESS_KEY", "secret")
    env.setenv("DATACONTRACT_S3_SESSION_TOKEN", "token")

    kwargs = _connect(_server())

    assert kwargs["aws_access_key_id"] == "AKIA_TEST"
    assert kwargs["aws_secret_access_key"] == "secret"
    assert kwargs["aws_session_token"] == "token"


def test_missing_staging_dir_is_rejected(env):
    server = Server(server="athena", type="athena", schema="my_database")

    with pytest.raises(DataContractException) as exc_info:
        _connect(server)

    assert "staging directory is required" in exc_info.value.reason


def test_missing_schema_is_rejected(env):
    server = Server(server="athena", type="athena", stagingDir=STAGING_DIR)

    with pytest.raises(DataContractException) as exc_info:
        _connect(server)

    assert "Schema is required" in exc_info.value.reason
