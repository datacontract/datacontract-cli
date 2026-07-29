"""How the S3 duckdb connection resolves credentials.

No S3 or MinIO involved: duckdb and boto3 are faked and we assert which secret
the setup creates. The point is that an `aws sso login` session reaches S3 the
way it already reaches Athena and Redshift.
"""

from unittest.mock import MagicMock, patch

import pytest
from open_data_contract_standard.model import Server

from datacontract.engines.ibis.connections.duckdb_connection import setup_s3_connection

S3_ENV = [
    "DATACONTRACT_S3_REGION",
    "DATACONTRACT_S3_ACCESS_KEY_ID",
    "DATACONTRACT_S3_SECRET_ACCESS_KEY",
    "DATACONTRACT_S3_SESSION_TOKEN",
]


@pytest.fixture(autouse=True)
def env(monkeypatch):
    for name in S3_ENV:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def _session(access_key="ASIA_SSO", secret_key="sso-secret", token="sso-token", region="eu-central-1"):
    """A boto3 session that resolves credentials, as after `aws sso login`."""
    session = MagicMock()
    session.region_name = region
    if access_key is None:
        session.get_credentials.return_value = None
    else:
        frozen = MagicMock(access_key=access_key, secret_key=secret_key, token=token)
        session.get_credentials.return_value.get_frozen_credentials.return_value = frozen
    return session


def _setup(server=None, session=None):
    con = MagicMock()
    server = server or Server(server="production", type="s3", location="s3://bucket/orders/*.csv", format="csv")
    with patch("boto3.Session", return_value=session or _session()):
        setup_s3_connection(con, server)
    return "\n".join(str(call.args[0]) for call in con.sql.call_args_list)


def test_an_aws_session_is_used_when_no_key_is_configured():
    sql = _setup()

    assert "ASIA_SSO" in sql
    assert "sso-secret" in sql
    assert "sso-token" in sql
    assert "eu-central-1" in sql


def test_explicit_keys_take_precedence_over_the_session(env):
    env.setenv("DATACONTRACT_S3_ACCESS_KEY_ID", "AKIA_EXPLICIT")
    env.setenv("DATACONTRACT_S3_SECRET_ACCESS_KEY", "explicit-secret")

    sql = _setup()

    assert "AKIA_EXPLICIT" in sql
    assert "ASIA_SSO" not in sql


def test_no_secret_is_created_when_nothing_resolves():
    """Public buckets are read without credentials; a secret would sign the request."""
    sql = _setup(session=_session(access_key=None))

    assert "CREATE OR REPLACE SECRET" not in sql


def test_a_session_without_a_token_omits_the_token_clause():
    sql = _setup(session=_session(token=None))

    assert "SESSION_TOKEN" not in sql
    assert "ASIA_SSO" in sql


def test_a_custom_endpoint_still_uses_path_style(env):
    server = Server(
        server="production",
        type="s3",
        location="s3://bucket/orders/*.csv",
        format="csv",
        endpointUrl="http://localhost:9000",
    )

    sql = _setup(server=server)

    assert "localhost:9000" in sql
    assert "URL_STYLE 'path'" in sql
    assert "USE_SSL 'false'" in sql


# ---------------------------------------------------------------------------
# One place resolves the DATACONTRACT_S3_* variables for every AWS service
# ---------------------------------------------------------------------------
def test_glue_honours_the_configured_credentials(env):
    """`import athena` reads the Glue catalog, and used to ignore these entirely."""
    env.setenv("DATACONTRACT_S3_ACCESS_KEY_ID", "AKIA_CONFIGURED")
    env.setenv("DATACONTRACT_S3_SECRET_ACCESS_KEY", "configured-secret")
    from datacontract.imports.glue_importer import glue_client

    with patch("boto3.client") as boto3_client:
        glue_client("eu-central-1")

    assert boto3_client.call_args.kwargs["aws_access_key_id"] == "AKIA_CONFIGURED"
    assert boto3_client.call_args.kwargs["region_name"] == "eu-central-1"


def test_an_unset_variable_leaves_boto3_to_its_own_chain(env):
    from datacontract.imports.glue_importer import glue_client

    with patch("boto3.client") as boto3_client:
        glue_client()

    assert boto3_client.call_args.kwargs["aws_access_key_id"] is None


def test_an_explicit_region_wins_over_the_variable(env):
    """--region and the Redshift endpoint host are more specific than the variable."""
    env.setenv("DATACONTRACT_S3_REGION", "us-east-1")
    from datacontract.imports.glue_importer import glue_client

    with patch("boto3.client") as boto3_client:
        glue_client("eu-central-1")

    assert boto3_client.call_args.kwargs["region_name"] == "eu-central-1"


def test_the_region_variable_is_used_when_no_region_is_passed(env):
    env.setenv("DATACONTRACT_S3_REGION", "us-east-1")
    from datacontract.imports.glue_importer import glue_client

    with patch("boto3.client") as boto3_client:
        glue_client()

    assert boto3_client.call_args.kwargs["region_name"] == "us-east-1"


def test_an_expired_session_falls_back_to_no_credentials():
    """boto3 raises while refreshing an expired SSO session; a public bucket still reads."""
    from datacontract.engines.ibis.connections.aws_credentials import resolve_aws_credentials

    session = MagicMock()
    session.get_credentials.return_value.get_frozen_credentials.side_effect = Exception("session expired")

    with patch("boto3.Session", return_value=session):
        assert resolve_aws_credentials() is None


def test_a_quote_in_the_endpoint_cannot_end_the_sql_literal(env):
    """endpointUrl comes from the contract, and a contract can be someone else's URL.

    A single quote is a legal URI sub-delimiter, so the schema's `format: uri`
    check lets it through; without escaping it ended the literal and the rest
    was parsed as SQL.
    """
    env.setenv("DATACONTRACT_S3_ACCESS_KEY_ID", "AKIA_TEST")
    env.setenv("DATACONTRACT_S3_SECRET_ACCESS_KEY", "secret")
    server = Server(
        server="production",
        type="s3",
        location="s3://bucket/orders/*.csv",
        format="csv",
        endpointUrl="http://a',SCOPE,'b",
    )

    sql = _setup(server=server)

    # the quotes are doubled, so the whole thing stays one literal
    assert "a'',SCOPE,''b" in sql
    assert "SCOPE," not in sql.replace("a'',SCOPE,''b", "")


def test_a_quote_in_a_credential_is_escaped(env):
    env.setenv("DATACONTRACT_S3_ACCESS_KEY_ID", "AKIA'X")
    env.setenv("DATACONTRACT_S3_SECRET_ACCESS_KEY", "se'cret")

    sql = _setup()

    assert "AKIA''X" in sql
    assert "se''cret" in sql
