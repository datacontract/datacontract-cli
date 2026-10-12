"""The API keeps serving while a request blocks on a data source.

These start a real uvicorn server, because the FastAPI TestClient handles one
request at a time and so cannot show that a slow test blocks other requests.
"""

import socket
import threading
import time
from concurrent.futures import ThreadPoolExecutor

import pytest
import requests
import uvicorn

from datacontract.api import app
from datacontract.data_contract import DataContract

LINT_CONTRACT = """apiVersion: v3.2.0
kind: DataContract
id: orders
version: 1.0.0
status: active
"""


def _postgres_contract(port: int) -> str:
    return f"""apiVersion: v3.2.0
kind: DataContract
id: orders
version: 1.0.0
status: active
schema:
  - name: orders
    properties:
      - name: order_id
        logicalType: string
servers:
  - server: production
    type: postgres
    host: 127.0.0.1
    port: {port}
    database: postgres
    schema: public
"""


@pytest.fixture(scope="module")
def api_url():
    with socket.socket() as sock:
        sock.bind(("127.0.0.1", 0))
        port = sock.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, host="127.0.0.1", port=port, log_level="warning"))
    thread = threading.Thread(target=server.run, daemon=True)
    thread.start()
    deadline = time.monotonic() + 10
    while not server.started:
        assert time.monotonic() < deadline, "the API server did not start"
        time.sleep(0.05)
    yield f"http://127.0.0.1:{port}"
    server.should_exit = True
    thread.join(timeout=10)


@pytest.fixture
def silent_server():
    """A TCP server that accepts connections and never answers, like a wrong port behind a proxy."""
    sock = socket.socket()
    sock.bind(("127.0.0.1", 0))
    sock.listen(16)
    accepted = []

    def accept():
        while True:
            try:
                accepted.append(sock.accept()[0])
            except OSError:
                return

    threading.Thread(target=accept, daemon=True).start()
    yield sock.getsockname()[1]
    sock.close()
    for conn in accepted:
        conn.close()


@pytest.fixture
def blocking_test(monkeypatch):
    """Make DataContract.test block until released, and count the runs in progress."""
    release = threading.Event()
    state = {"running": 0, "max_running": 0}
    lock = threading.Lock()

    def test(self):
        with lock:
            state["running"] += 1
            state["max_running"] = max(state["max_running"], state["running"])
        try:
            assert release.wait(timeout=30), "the test was never released"
        finally:
            with lock:
                state["running"] -= 1
        return DataContract(data_contract_str=LINT_CONTRACT).lint()

    monkeypatch.setattr(DataContract, "test", test)
    yield release, state
    release.set()


def _wait_until(condition, timeout=10):
    deadline = time.monotonic() + timeout
    while not condition():
        if time.monotonic() > deadline:
            return False
        time.sleep(0.05)
    return True


def test_a_blocked_test_does_not_block_other_requests(api_url, blocking_test):
    release, state = blocking_test
    with ThreadPoolExecutor() as pool:
        pending = pool.submit(requests.post, f"{api_url}/test", data=LINT_CONTRACT, timeout=60)
        assert _wait_until(lambda: state["running"] == 1)

        started = time.monotonic()
        lint = requests.post(f"{api_url}/lint", data=LINT_CONTRACT, timeout=10)
        docs = requests.get(f"{api_url}/openapi.json", timeout=10)

        assert lint.status_code == 200
        assert docs.status_code == 200
        assert time.monotonic() - started < 5
        assert not pending.done()

        release.set()
        assert pending.result().status_code == 200


def test_tests_run_in_parallel(api_url, blocking_test):
    release, state = blocking_test
    with ThreadPoolExecutor(max_workers=4) as pool:
        pending = [pool.submit(requests.post, f"{api_url}/test", data=LINT_CONTRACT, timeout=60) for _ in range(4)]
        assert _wait_until(lambda: state["running"] == 4), f"only {state['running']} of 4 tests ran at once"

        release.set()
        assert [response.result().status_code for response in pending] == [200] * 4
    assert state["max_running"] == 4


def test_a_failing_test_does_not_break_the_server(api_url, monkeypatch):
    def test(self):
        raise RuntimeError("the data source exploded")

    monkeypatch.setattr(DataContract, "test", test)

    failed = requests.post(f"{api_url}/test", data=LINT_CONTRACT, timeout=10)
    assert failed.status_code == 500

    assert requests.post(f"{api_url}/lint", data=LINT_CONTRACT, timeout=10).status_code == 200


def test_an_unresponsive_data_source_times_out_while_the_server_keeps_serving(api_url, silent_server):
    headers = {
        "datacontract-postgres-username": "reader",
        "datacontract-postgres-password": "secret",
        "datacontract-connect-timeout": "2",
    }
    with ThreadPoolExecutor() as pool:
        started = time.monotonic()
        pending = pool.submit(
            requests.post,
            f"{api_url}/test?server=production",
            data=_postgres_contract(silent_server),
            headers=headers,
            timeout=60,
        )
        # the server keeps answering while the test waits for the silent data source
        time.sleep(0.5)
        assert requests.post(f"{api_url}/lint", data=LINT_CONTRACT, timeout=5).status_code == 200

        response = pending.result()
        elapsed = time.monotonic() - started

    assert response.status_code == 200
    run = response.json()
    assert run["result"] in ("error", "failed")
    assert elapsed < 20, f"the test took {elapsed:.0f}s, the connect timeout did not apply"
