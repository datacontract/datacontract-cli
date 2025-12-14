import json
import logging
from pathlib import Path
from unittest.mock import MagicMock, patch

from datacontract.data_contract import DataContract

logging.basicConfig(level=logging.DEBUG, force=True)


datacontract = Path(__file__).parent / "fixtures/api/weather-service.odcs.yaml"


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


@patch("datacontract.engines.data_contract_test.requests.get", side_effect=mock_get)
def test_test_api(_mock_get):
    with open(datacontract) as data_contract_file:
        data_contract_str = data_contract_file.read()
    data_contract = DataContract(data_contract_str=data_contract_str)

    run = data_contract.test()

    print(run)
    assert run.result == "passed"
    assert all(check.result == "passed" for check in run.checks)
