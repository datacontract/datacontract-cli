from unittest import mock

import pytest
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.config import Config
from datacontract.data_contract import DataContract
from datacontract.model.exceptions import DataContractException

runner = CliRunner()

CONTRACT = "fixtures/lint/valid.odcs.yaml"


def _response(status_code: int = 200, text: str = "", location_html: str | None = None):
    response = mock.MagicMock()
    response.status_code = status_code
    response.text = text
    response.headers = {"location-html": location_html} if location_html else {}
    return response


@pytest.fixture(autouse=True)
def no_ambient_credentials(monkeypatch):
    """Never let a developer's own .env leak into these tests."""
    for name in (
        "ENTROPY_DATA_API_KEY",
        "ENTROPY_DATA_HOST",
        "DATAMESH_MANAGER_API_KEY",
        "DATAMESH_MANAGER_HOST",
        "DATACONTRACT_MANAGER_API_KEY",
        "DATACONTRACT_MANAGER_HOST",
    ):
        monkeypatch.delenv(name, raising=False)


def test_publish_puts_the_contract_and_returns_its_url(monkeypatch):
    put = mock.MagicMock(return_value=_response(location_html="https://app.entropy-data.com/datacontracts/valid_odcs"))
    monkeypatch.setattr("datacontract.integration.entropy_data.requests.put", put)

    url = DataContract(
        data_contract_file=CONTRACT,
        config=Config(entropy_data_api_key="abc", entropy_data_host="https://api.example.com"),
    ).publish()

    assert url == "https://app.entropy-data.com/datacontracts/valid_odcs"
    kwargs = put.call_args.kwargs
    assert kwargs["url"] == "https://api.example.com/api/datacontracts/valid_odcs"
    assert kwargs["headers"]["x-api-key"] == "abc"
    assert kwargs["json"]["id"] == "valid_odcs"
    assert kwargs["verify"] is True


def test_publish_from_a_contract_string(monkeypatch):
    put = mock.MagicMock(return_value=_response())
    monkeypatch.setattr("datacontract.integration.entropy_data.requests.put", put)

    with open(CONTRACT) as f:
        contract_str = f.read()

    assert (
        DataContract(data_contract_str=contract_str, config=Config(entropy_data_api_key="abc")).publish() is None
    )  # no location-html header, so there is no URL to return
    assert put.call_args.kwargs["json"]["id"] == "valid_odcs"


def test_publish_honors_ssl_verification(monkeypatch):
    put = mock.MagicMock(return_value=_response())
    monkeypatch.setattr("datacontract.integration.entropy_data.requests.put", put)

    DataContract(
        data_contract_file=CONTRACT,
        ssl_verification=False,
        config=Config(entropy_data_api_key="abc"),
    ).publish()

    assert put.call_args.kwargs["verify"] is False


def test_publish_raises_on_server_error(monkeypatch):
    """A library caller must be able to handle the failure; publishing must not kill the process."""
    monkeypatch.setattr(
        "datacontract.integration.entropy_data.requests.put",
        mock.MagicMock(return_value=_response(status_code=403, text="Forbidden")),
    )

    with pytest.raises(DataContractException) as e:
        DataContract(data_contract_file=CONTRACT, config=Config(entropy_data_api_key="abc")).publish()

    assert "Forbidden" in e.value.reason
    assert "api.entropy-data.com" in e.value.reason


def test_publish_raises_on_connection_error(monkeypatch):
    monkeypatch.setattr(
        "datacontract.integration.entropy_data.requests.put",
        mock.MagicMock(side_effect=OSError("connection refused")),
    )

    with pytest.raises(DataContractException) as e:
        DataContract(data_contract_file=CONTRACT, config=Config(entropy_data_api_key="abc")).publish()

    assert "connection refused" in e.value.reason


def test_publish_raises_without_api_key():
    with pytest.raises(DataContractException) as e:
        DataContract(data_contract_file=CONTRACT).publish()

    assert "ENTROPY_DATA_API_KEY" in e.value.reason


def test_cli_publish(monkeypatch):
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "abc")
    monkeypatch.setattr(
        "datacontract.integration.entropy_data.requests.put",
        mock.MagicMock(return_value=_response(location_html="https://app.entropy-data.com/datacontracts/valid_odcs")),
    )

    result = runner.invoke(app, ["publish", CONTRACT])

    assert result.exit_code == 0, result.output
    assert "Published data contract successfully" in result.output
    assert "https://app.entropy-data.com/datacontracts/valid_odcs" in result.output


def test_cli_publish_fails_with_exit_code_1(monkeypatch, capsys):
    """`datacontract publish` must exit non-zero on failure so CI scripts catch it."""
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "abc")
    monkeypatch.setattr(
        "datacontract.integration.entropy_data.requests.put",
        mock.MagicMock(return_value=_response(status_code=500, text="Internal Server Error")),
    )
    monkeypatch.setattr("sys.argv", ["datacontract", "publish", CONTRACT])

    from datacontract import cli

    with pytest.raises(SystemExit) as e:
        cli.main()

    assert e.value.code == 1
    # the console wraps long lines, so compare with the inserted line breaks collapsed
    output = " ".join(capsys.readouterr().out.split())
    assert "Error publishing data contract to api.entropy-data.com: Internal Server Error" in output
