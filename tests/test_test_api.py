import json
import logging
import socket
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
import yaml
from urllib3.exceptions import NewConnectionError

from datacontract.config import Config
from datacontract.data_contract import DataContract
from datacontract.engines.http_api import _is_public, _PublicHTTPSConnection

logging.basicConfig(level=logging.DEBUG, force=True)


datacontract = Path(__file__).parent / "fixtures/api/weather-service.odcs.yaml"
datacontract_array = Path(__file__).parent / "fixtures/api/weather-service-array.odcs.yaml"


def mock_get(*args, **kwargs):
    mock_response = MagicMock()
    mock_response.status_code = 200
    json_data = {
        "latitude": 52.52,
        "longitude": 13.419998,
        "generationtime_ms": 0.141263008117676,
        "utc_offset_seconds": 0,
        "timezone": "GMT",
        "timezone_abbreviation": "GMT",
        "elevation": 38,
        "current_units": {"time": "iso8601", "interval": "seconds", "temperature_2m": "°C", "wind_speed_10m": "km/h"},
        "current": {"time": "2025-08-01T11:15", "interval": 900, "temperature_2m": 19.1, "wind_speed_10m": 11.1},
        "hourly_units": {
            "time": "iso8601",
            "temperature_2m": "°C",
            "relative_humidity_2m": "%",
            "wind_speed_10m": "km/h",
        },
        "hourly": {
            "time": ["2025-08-01T00:00", "2025-08-01T01:00"],
            "temperature_2m": [16.3, 16.2],
            "relative_humidity_2m": [81, 83],
            "wind_speed_10m": [6.2, 6.9],
        },
    }
    mock_response.json.return_value = json_data
    mock_response.text = json.dumps(json_data)
    mock_response.raise_for_status.return_value = None
    return mock_response


@patch("datacontract.engines.http_api.ApiSession.request", side_effect=mock_get)
def test_test_api(_mock_get):
    with open(datacontract) as data_contract_file:
        data_contract_str = data_contract_file.read()
    data_contract = DataContract(data_contract_str=data_contract_str)

    run = data_contract.test()

    print(run)
    assert run.result == "passed"
    assert all(check.result == "passed" for check in run.checks)


def mock_get_array(*args, **kwargs):
    mock_response = MagicMock()
    mock_response.status_code = 200
    json_data = [
        {"temperature": 19.1, "humidity": 65, "wind_speed": 11.1, "condition": "sunny"},
        {"temperature": 17.3, "humidity": 70, "wind_speed": 8.4, "condition": "cloudy"},
    ]
    mock_response.json.return_value = json_data
    mock_response.text = json.dumps(json_data)
    mock_response.raise_for_status.return_value = None
    return mock_response


@patch("datacontract.engines.http_api.ApiSession.request", side_effect=mock_get_array)
def test_test_api_array_delimiter(_mock_get):
    with open(datacontract_array) as data_contract_file:
        data_contract_str = data_contract_file.read()
    data_contract = DataContract(data_contract_str=data_contract_str)

    run = data_contract.test()

    print(run)
    assert run.result == "passed"
    assert all(check.result == "passed" for check in run.checks)


def search_contract(api, custom_properties: dict, location_query: str = "", **kwargs) -> DataContract:
    """A contract for the local API's search endpoint, its request shaped by the custom properties."""
    contract = {
        "apiVersion": "v3.2.0",
        "kind": "DataContract",
        "id": "orders",
        "version": "1.0.0",
        "status": "active",
        "servers": [
            {
                "server": "search",
                "type": "api",
                "location": f"{api.url}/orders/search{location_query}",
                "customProperties": [{"property": k, "value": v} for k, v in custom_properties.items()],
            }
        ],
        "schema": [{"name": "orders", "properties": [{"name": "order_id", "logicalType": "string", "required": True}]}],
    }
    return DataContract(data_contract_str=yaml.safe_dump(contract, sort_keys=False), **kwargs)


def test_post_request(api, monkeypatch):
    api.body = json.dumps([{"order_id": "ORD-1"}])
    monkeypatch.setenv("SIZE", "5")
    contract = search_contract(
        api,
        {
            "method": "post",
            "params": {"limit": "${LIMIT:-100}", "status": ["placed", "shipped"], "archived": False},
            "body": {"query": {"customer": "${CUSTOMER:-C-1}"}, "size": "${SIZE}"},
        },
        location_query="?tenant=eu",
    )

    run = contract.test()

    assert run.result == "passed", run.pretty()
    assert api.methods == ["POST"]
    assert api.paths == ["/orders/search?tenant=eu&limit=100&status=placed&status=shipped&archived=false"]
    assert api.headers[0]["Content-Type"] == "application/json"
    # a variable stays a string, such as a numeric customer or zip code
    assert json.loads(api.request_bodies[0]) == {"query": {"customer": "C-1"}, "size": "5"}


def test_credential_headers(api):
    api.body = json.dumps([{"order_id": "ORD-1"}])
    config = Config(api_header_authorization="Bearer token", api_header_x_api_key="key")

    run = search_contract(api, {}, config=config).test()

    assert run.result == "passed", run.pretty()
    assert api.methods == ["GET"]
    assert (api.headers[0]["Authorization"], api.headers[0]["X-API-Key"]) == ("Bearer token", "key")


def test_error_response_is_explained(api):
    api.status = 400
    api.body = '{"error": "unknown field size"}'

    run = search_contract(api, {}).test()

    assert run.result == "error"
    assert any("400" in c.reason and "unknown field size" in c.reason for c in run.checks), run.pretty()


@pytest.mark.parametrize("dry_run", [False, True])
@pytest.mark.parametrize(
    "custom_properties, location_query, reason",
    [
        ({"method": "PUT"}, "", "Method 'PUT' is not supported; use GET or POST."),
        ({"body": {"q": "a"}}, "", "A body requires method POST."),
        ({"method": "GET", "body": {"q": "a"}}, "", "A body requires method POST."),
        ({"params": ["limit"]}, "", "The params custom property must map each query parameter name to its value."),
        ({"params": {"filter": {"status": "a"}}}, "", "Query parameter 'filter' must be a string, number, or boolean"),
        (
            {"params": {"limit": 10}},
            "?limit=100",
            "Query parameter 'limit' is set both in the location and in the params custom property.",
        ),
    ],
)
def test_invalid_request(api, dry_run, custom_properties, location_query, reason):
    run = search_contract(api, custom_properties, location_query, dry_run=dry_run).test()

    assert run.result == "failed"
    assert any(c.name == "Build the API request" and c.reason.startswith(reason) for c in run.checks), run.pretty()
    assert api.paths == []


def test_untrusted_contract_stays_off_private_networks(api):
    api.body = json.dumps([{"order_id": "ORD-1"}])
    run = search_contract(api, {"method": "POST", "body": {"q": "a"}}, untrusted_contract=True).test()

    assert run.result == "error"
    assert any(
        c.reason.startswith(
            f"Failed to fetch API response from {api.url}/orders/search: Refused to connect to 127.0.0.1:"
        )
        for c in run.checks
    ), run.pretty()
    assert api.paths == []

    run = search_contract(api, {}, untrusted_contract=True, allow_private_network=True).test()
    assert run.result == "passed", run.pretty()


def test_https_connection_stays_off_private_networks(api):
    """The address is checked before the TLS handshake, so a plain HTTP server stands in for an HTTPS one."""
    port = int(api.url.rsplit(":", 1)[1])

    with pytest.raises(NewConnectionError, match="Refused to connect to 127.0.0.1"):
        _PublicHTTPSConnection("127.0.0.1", port)._new_conn()


def test_private_address_refused_before_connecting():
    """A closed port answers like an open one, and a hostname's private address is not disclosed."""
    with socket.socket() as probe:
        probe.bind(("127.0.0.1", 0))
        closed_port = probe.getsockname()[1]

    with pytest.raises(NewConnectionError, match="Refused to connect to localhost:"):
        _PublicHTTPSConnection("localhost", closed_port)._new_conn()


@pytest.mark.parametrize(
    "address, public",
    [
        ("93.184.215.14", True),
        ("2606:2800:21f:cb07:6820:80da:af6b:8b2c", True),
        ("::ffff:127.0.0.1", False),
        ("64:ff9b::a9fe:a9fe", False),
        ("64:ff9b::5db8:d70e", True),
        ("::127.0.0.1", False),
        ("::ffff:0:7f00:1", False),
        ("::1", False),
    ],
)
def test_embedded_ipv4_address_is_checked(address, public):
    assert _is_public(address) is public
