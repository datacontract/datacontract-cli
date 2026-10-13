"""Unit tests for how connect_ibis attaches MySQL through DuckDB.

These do not hit MySQL: most patch ``duckdb.connect`` and assert the ATTACH
connection string; the failed-attach test points the real extension at a closed port.
"""

import os
import socket
import threading
import time
import traceback

import duckdb
import ibis
import pytest
from open_data_contract_standard.model import OpenDataContractStandard, Server

from datacontract.engines.ibis.connections import duckdb_connection
from datacontract.engines.ibis.connections.connect import connect_ibis
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import Run


@pytest.fixture
def env(monkeypatch):
    """The tests assert the exact connection string, so start from a clean slate."""
    for name in list(os.environ):
        if name.startswith("DATACONTRACT_MYSQL_"):
            monkeypatch.delenv(name, raising=False)
    monkeypatch.setenv("DATACONTRACT_MYSQL_USERNAME", "reader")
    monkeypatch.setenv("DATACONTRACT_MYSQL_PASSWORD", "secret")
    return monkeypatch


# captured before the autouse fixture below replaces it
wait_for_mysql_greeting = duckdb_connection._wait_for_mysql_greeting


@pytest.fixture(autouse=True)
def no_handshake_probe(monkeypatch):
    """The probe opens a real socket; test_wait_for_mysql_greeting covers it on its own."""
    monkeypatch.setattr(
        "datacontract.engines.ibis.connections.duckdb_connection._wait_for_mysql_greeting",
        lambda host, port, timeout: None,
    )


@pytest.fixture
def captured_statements(monkeypatch):
    statements = []

    class FakeConnection:
        def execute(self, sql, parameters=None):
            statements.append(sql)

    monkeypatch.setattr(duckdb, "connect", lambda: FakeConnection())
    monkeypatch.setattr(
        "datacontract.engines.ibis.connections.duckdb_connection._load_extension", lambda con, ext, name: None
    )
    monkeypatch.setattr(ibis.duckdb, "from_connection", lambda con: con)
    return statements


def _server():
    return Server(server="mysql", type="mysql", host="contract-host", port=3307, database="contract_db")


def _connect():
    data_contract = OpenDataContractStandard(apiVersion="v3.0.2", kind="DataContract", id="test", version="1.0.0")
    return connect_ibis(Run.create_run(), data_contract=data_contract, server=_server())


def _attach_statement(statements):
    return next(sql for sql in statements if sql.startswith("ATTACH"))


def test_server_details_come_from_the_contract_by_default(env, captured_statements):
    _connect()

    attach = _attach_statement(captured_statements)
    assert "host=contract-host" in attach
    assert "port=3307" in attach
    assert "database=contract_db" in attach


def test_env_variables_override_the_contract_server_details(env, captured_statements):
    env.setenv("DATACONTRACT_MYSQL_HOST", "env-host")
    env.setenv("DATACONTRACT_MYSQL_PORT", "3308")
    env.setenv("DATACONTRACT_MYSQL_DATABASE", "env_db")

    _connect()

    attach = _attach_statement(captured_statements)
    assert "host=env-host" in attach
    assert "port=3308" in attach
    assert "database=env_db" in attach


def test_a_failed_attach_does_not_show_the_password(env):
    env.setenv("DATACONTRACT_MYSQL_PASSWORD", "s3cret-pw")
    env.setenv("DATACONTRACT_MYSQL_HOST", "127.0.0.1")
    env.setenv("DATACONTRACT_MYSQL_PORT", "1")

    with pytest.raises(duckdb.Error) as exc_info:
        _connect()

    assert "s3cret-pw" not in "".join(traceback.format_exception(exc_info.value))


@pytest.fixture
def tcp_server():
    """A local TCP server; ``greeting`` is sent on accept, ``None`` keeps the connection silent."""
    servers = []

    def start(greeting):
        sock = socket.socket()
        sock.bind(("127.0.0.1", 0))
        sock.listen(8)
        accepted = []

        def serve():
            while True:
                try:
                    conn, _ = sock.accept()
                except OSError:
                    return
                accepted.append(conn)
                if greeting is not None:
                    conn.sendall(greeting)

        threading.Thread(target=serve, daemon=True).start()
        servers.append((sock, accepted))
        return sock.getsockname()[1]

    yield start
    for sock, accepted in servers:
        sock.close()
        for conn in accepted:
            conn.close()


def test_wait_for_mysql_greeting_accepts_a_server_that_greets(tcp_server):
    port = tcp_server(b"\x4a\x00\x00\x00\x0a8.0.36")

    wait_for_mysql_greeting("127.0.0.1", port, timeout=5)


def test_wait_for_mysql_greeting_fails_fast_on_a_silent_server(tcp_server):
    port = tcp_server(None)

    started = time.monotonic()
    with pytest.raises(DataContractException) as exc_info:
        wait_for_mysql_greeting("127.0.0.1", port, timeout=1)

    assert time.monotonic() - started < 5
    assert "did not answer within 1 seconds" in exc_info.value.reason


def test_wait_for_mysql_greeting_reports_a_refused_connection():
    unused = socket.socket()
    unused.bind(("127.0.0.1", 0))
    closed_port = unused.getsockname()[1]
    unused.close()

    with pytest.raises(DataContractException) as exc_info:
        wait_for_mysql_greeting("127.0.0.1", closed_port, timeout=1)

    assert exc_info.value.reason.startswith(f"Could not connect to MySQL server 127.0.0.1:{closed_port}")


def test_wait_for_mysql_greeting_skips_localhost():
    # the MySQL client uses the Unix socket for localhost, so there is no TCP port to probe
    wait_for_mysql_greeting("localhost", 1, timeout=1)
