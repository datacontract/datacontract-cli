"""`datacontract test` against a GET endpoint, with the contract imported from its OpenAPI document."""

import json
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

import pytest

from datacontract.data_contract import DataContract

ORDERS = "fixtures/import/openapi/orders.yaml"

ORDER_YAML = """\
order_id: ORD-1001
order_timestamp: 2024-01-01T10:00:00Z
status: shipped
total: null
customer:
  customer_id: C-1
  email: jane@example.com
items:
  - sku: SKU-1
    quantity: 2
"""

ORDERS_JSON = [
    {
        "order_id": f"ORD-100{n}",
        "order_timestamp": f"2024-01-0{n}T10:00:00Z",
        "status": status,
        "total": total,
        "customer": {"customer_id": f"C-{n}", "email": f"c{n}@example.com"},
        "items": [{"sku": f"SKU-{n}", "quantity": n}],
    }
    for n, status, total in [(1, "placed", 12.5), (2, "delivered", None)]
]


@pytest.fixture
def api():
    """A local API that answers every GET with the body and content type set on it, and records the paths."""
    state = {"body": "", "content_type": "application/json", "paths": []}

    class Handler(BaseHTTPRequestHandler):
        def do_GET(self):
            state["paths"].append(self.path)
            body = state["body"].encode()
            self.send_response(200)
            self.send_header("Content-Type", state["content_type"])
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    state["url"] = f"http://127.0.0.1:{server.server_port}"
    yield state
    server.shutdown()
    server.server_close()


def contract_for(api, operation):
    """The imported contract, its production server pointed at the local API."""
    contract = DataContract.import_from_source("openapi", ORDERS, openapi_operation=operation)
    server = contract.servers[0]
    server.location = server.location.replace("https://eu.api.example.com", api["url"])
    return DataContract(data_contract=contract)


def test_yaml_response(api):
    api["body"] = ORDER_YAML
    api["content_type"] = "application/yaml; charset=utf-8"

    run = contract_for(api, "getOrder").test()

    assert run.result == "passed", run.pretty()
    # the path parameter defaults to its example
    assert api["paths"] == ["/v1/orders/ORD-1001"]


def test_yaml_response_violates_the_contract(api):
    api["body"] = ORDER_YAML.replace("status: shipped", "status: lost").replace("order_id: ORD-1001\n", "")
    api["content_type"] = "application/x-yaml"

    run = contract_for(api, "getOrder").test()

    assert run.result == "failed"
    failed = {check.key for check in run.checks if check.result == "failed"}
    assert {"getOrder__order_id__field_is_present", "getOrder__status__field_enum"} <= failed


def test_yaml_stream_holds_one_record_per_document(api):
    api["body"] = "\n---\n".join(json.dumps(order) for order in ORDERS_JSON)
    api["content_type"] = "text/yaml"

    run = contract_for(api, "listOrders").test()

    assert run.result == "passed", run.pretty()


def test_json_response(api, monkeypatch):
    api["body"] = json.dumps(ORDERS_JSON)
    monkeypatch.setenv("limit", "2")

    run = contract_for(api, "listOrders").test()

    assert run.result == "passed", run.pretty()
    # the required query parameter is a variable, set in the environment
    assert api["paths"] == ["/v1/orders?limit=2"]


def test_json_response_violates_the_contract(api):
    api["body"] = json.dumps([*ORDERS_JSON, {**ORDERS_JSON[0], "order_id": "1003", "status": "lost"}])

    run = contract_for(api, "listOrders").test()

    assert run.result == "failed"
    failed = {check.key for check in run.checks if check.result == "failed"}
    assert {"listOrders__order_id__field_regex", "listOrders__status__field_enum"} <= failed
