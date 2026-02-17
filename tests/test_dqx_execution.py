from types import SimpleNamespace

from datacontract.engines.data_contract_test import execute_data_contract_test
from datacontract.engines.dqx.check_dqx_execute import check_dqx_execute
from datacontract.model.run import Run


class _DummyServer:
    def __init__(self, server: str = "production", server_type: str = "databricks", fmt: str = "delta"):
        self.server = server
        self.type = server_type
        self.format = fmt


def _dummy_contract(server: _DummyServer):
    return SimpleNamespace(
        id="urn:datacontract:test",
        version="1.0.0",
        dataProduct="test-product",
        schema_=[SimpleNamespace(name="orders")],
        servers=[server],
    )


def test_execute_data_contract_test_routes_to_dqx(monkeypatch):
    server = _DummyServer()
    contract = _dummy_contract(server)
    run = Run.create_run()

    calls = {"dqx": 0, "soda": 0, "jsonschema": 0}

    monkeypatch.setattr("datacontract.engines.data_contract_test.get_server", lambda *_: server)
    monkeypatch.setattr("datacontract.engines.data_contract_test.create_checks", lambda *_: [])
    monkeypatch.setattr("datacontract.engines.data_contract_test.check_jsonschema", lambda *_: calls.__setitem__("jsonschema", 1))
    monkeypatch.setattr("datacontract.engines.data_contract_test.check_dqx_execute", lambda *_: calls.__setitem__("dqx", 1))
    monkeypatch.setattr("datacontract.engines.data_contract_test.check_soda_execute", lambda *_: calls.__setitem__("soda", 1))

    execute_data_contract_test(contract, run, test_engine="dqx")

    assert calls["dqx"] == 1
    assert calls["soda"] == 0
    assert calls["jsonschema"] == 0


def test_check_dqx_execute_skips_for_non_databricks_server():
    run = Run.create_run()
    contract = SimpleNamespace(schema_=[SimpleNamespace(name="orders")])
    server = _DummyServer(server_type="postgres", fmt="table")

    check_dqx_execute(run, contract, server)

    assert len(run.checks) == 0
    assert any("DQX execution is only available for server type 'databricks'" in log.message for log in run.logs)
