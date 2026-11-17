"""Unit tests for the Dremio connection: paths, types and sign-in, without a Dremio."""

import ibis.expr.datatypes as dt
import pytest
from open_data_contract_standard.model import Server

from datacontract.engines.ibis.connections import dremio
from datacontract.engines.ibis.connections.connect import connect_ibis
from datacontract.engines.ibis.connections.dremio import DremioRestClient, ibis_type, native_type, split_path
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import Run

DREMIO_ENV_VARS = [
    "DATACONTRACT_DREMIO_USERNAME",
    "DATACONTRACT_DREMIO_PASSWORD",
    "DATACONTRACT_DREMIO_TOKEN",
    "DATACONTRACT_DREMIO_USE_SSL",
    "DATACONTRACT_DREMIO_VALIDATE_CERTIFICATE",
    "DATACONTRACT_DREMIO_HOST",
    "DATACONTRACT_DREMIO_PORT",
    "DATACONTRACT_DREMIO_SCHEMA",
]


@pytest.fixture
def env(monkeypatch):
    for name in DREMIO_ENV_VARS:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


class Response:
    def __init__(self, status: int, body: dict):
        self.status_code = status
        self.ok = status < 400
        self.reason = "Unauthorized" if status == 401 else "OK"
        self.text = ""
        self._body = body

    def json(self):
        return self._body


class RecordingSession:
    """Answers the sign-in and the SQL API, and records what was sent."""

    def __init__(self, login_status: int = 200):
        self.requests = []
        self.login_status = login_status

    def post(self, url, json=None, **kwargs):
        self.requests.append(("POST", url, None, json))
        if self.login_status != 200:
            return Response(self.login_status, {"errorMessage": "Login failed"})
        return Response(200, {"token": "session-token"})

    def request(self, method, url, json=None, headers=None, **kwargs):
        self.requests.append((method, url, headers, json))
        if url.endswith("/api/v3/sql"):
            return Response(200, {"id": "job-1"})
        if url.endswith("/api/v3/job/job-1"):
            return Response(200, {"jobState": "COMPLETED"})
        return Response(200, {"rowCount": 1, "schema": [{"name": "n", "type": {"name": "BIGINT"}}], "rows": [{"n": 5}]})

    def close(self):
        pass


def test_a_path_splits_at_each_period_outside_quotes():
    assert split_path("sales.marts.daily") == ["sales", "marts", "daily"]
    assert split_path('$scratch."bucket.v1".sub') == ["$scratch", "bucket.v1", "sub"]
    assert split_path('"say ""hi""".x') == ['say "hi"', "x"]
    assert split_path("") == []
    assert split_path(None) == []


def test_column_types_map_to_ibis_types():
    assert ibis_type({"name": "VARCHAR"}) == dt.string
    assert ibis_type({"name": "DECIMAL", "precision": 10, "scale": 2}) == dt.Decimal(10, 2)
    assert ibis_type({"name": "TIMESTAMP"}) == dt.Timestamp(scale=3)
    assert ibis_type({"name": "LIST", "subSchema": [{"type": {"name": "INTEGER"}}]}) == dt.Array(dt.int32)
    assert ibis_type({"name": "STRUCT", "subSchema": [{"name": "city", "type": {"name": "VARCHAR"}}]}) == dt.Struct(
        {"city": dt.string}
    )
    assert ibis_type(_map("VARCHAR", "BIGINT")) == dt.Map(dt.string, dt.int64)
    assert ibis_type({"name": "SOMETHING_NEW"}) == dt.unknown


def test_column_types_are_written_as_a_contract_declares_them():
    assert native_type({"name": "VARCHAR"}) == "VARCHAR"
    assert native_type({"name": "DECIMAL", "precision": 10, "scale": 2}) == "DECIMAL(10,2)"
    assert native_type({"name": "LIST", "subSchema": [{"type": {"name": "VARCHAR"}}]}) == "ARRAY<VARCHAR>"
    assert (
        native_type(
            {
                "name": "STRUCT",
                "subSchema": [
                    {"name": "city", "type": {"name": "VARCHAR"}},
                    {"name": "zip", "type": {"name": "VARCHAR"}},
                ],
            }
        )
        == "STRUCT<city VARCHAR, zip VARCHAR>"
    )
    assert native_type(_map("VARCHAR", "INTEGER")) == "MAP<VARCHAR, INTEGER>"


def test_a_personal_access_token_is_sent_as_bearer_token_without_signing_in():
    session = RecordingSession()
    client = DremioRestClient("http://dremio:9047", token="pat", context=["sales", "marts"], session=session)

    schema, rows = client.run("SELECT COUNT(*) AS n FROM orders")

    assert rows == [{"n": 5}]
    method, url, headers, body = session.requests[0]
    assert (method, url, headers["Authorization"]) == ("POST", "http://dremio:9047/api/v3/sql", "Bearer pat")
    assert body == {"sql": "SELECT COUNT(*) AS n FROM orders", "context": ["sales", "marts"]}


def test_a_user_signs_in_once_and_sends_the_session_token():
    session = RecordingSession()
    client = DremioRestClient("http://dremio:9047", username="ada", password="secret", session=session)

    client.run("SELECT 1")
    client.run("SELECT 2")

    logins = [r for r in session.requests if r[1].endswith("/apiv2/login")]
    assert logins == [("POST", "http://dremio:9047/apiv2/login", None, {"userName": "ada", "password": "secret"})]
    assert session.requests[-1][2]["Authorization"] == "_dremiosession-token"


def test_a_failed_sign_in_names_the_status():
    client = DremioRestClient("http://dremio:9047", username="ada", password="wrong", session=RecordingSession(401))

    with pytest.raises(ConnectionError, match=r"Dremio login failed \(HTTP 401\): Login failed"):
        client.authorization()


def test_the_connection_takes_its_location_from_the_contract_and_the_overrides(env, monkeypatch):
    clients = []
    monkeypatch.setattr(dremio.DremioRestClient, "authorization", lambda self: clients.append(self) or "Bearer x")
    env.setenv("DATACONTRACT_DREMIO_TOKEN", "pat")

    connect_ibis(Run.create_run(), None, Server(type="dremio", host="dremio.example.com", schema='$scratch."b.v1".raw'))
    env.setenv("DATACONTRACT_DREMIO_HOST", "other.example.com")
    env.setenv("DATACONTRACT_DREMIO_PORT", "443")
    env.setenv("DATACONTRACT_DREMIO_USE_SSL", "true")
    env.setenv("DATACONTRACT_DREMIO_SCHEMA", "sales.marts")
    connect_ibis(Run.create_run(), None, Server(type="dremio", host="dremio.example.com", port=9047, schema="x"))

    assert [(c.base_url, c.context) for c in clients] == [
        ("http://dremio.example.com:9047", ["$scratch", "b.v1", "raw"]),
        ("https://other.example.com:443", ["sales", "marts"]),
    ]


def test_without_a_token_the_user_name_is_required(env):
    with pytest.raises(DataContractException, match="DATACONTRACT_DREMIO_USERNAME"):
        connect_ibis(Run.create_run(), None, Server(type="dremio", host="dremio.example.com"))


def _map(key: str, value: str) -> dict:
    entry = {
        "name": "STRUCT",
        "subSchema": [{"name": "key", "type": {"name": key}}, {"name": "value", "type": {"name": value}}],
    }
    return {"name": "MAP", "subSchema": [{"type": entry}]}
