import pytest
import yaml
from open_data_contract_standard.model import Server

from datacontract.engines.soda.connections.redshift import to_redshift_soda_configuration
from datacontract.model.exceptions import DataContractException


def _server() -> Server:
    return Server(
        type="redshift",
        host="my-wg.123456789012.us-east-1.redshift-serverless.amazonaws.com",
        port=5439,
        database="dev",
        schema="analytics",
    )


def test_to_redshift_soda_configuration_minimal(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_REDSHIFT_USERNAME", "admin")
    monkeypatch.setenv("DATACONTRACT_REDSHIFT_PASSWORD", "secret")

    yaml_str = to_redshift_soda_configuration(_server())
    config = yaml.safe_load(yaml_str)["data_source redshift"]

    assert config == {
        "type": "redshift",
        "host": "my-wg.123456789012.us-east-1.redshift-serverless.amazonaws.com",
        "port": "5439",
        "username": "admin",
        "password": "secret",
        "database": "dev",
        "schema": "analytics",
    }


def test_to_redshift_soda_configuration_passes_through_extra_env_vars(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_REDSHIFT_USERNAME", "admin")
    monkeypatch.setenv("DATACONTRACT_REDSHIFT_PASSWORD", "secret")
    monkeypatch.setenv("DATACONTRACT_REDSHIFT_REGION", "us-east-1")
    monkeypatch.setenv("DATACONTRACT_REDSHIFT_ACCESS_KEY_ID", "AKIA...")

    yaml_str = to_redshift_soda_configuration(_server())
    config = yaml.safe_load(yaml_str)["data_source redshift"]

    assert config["region"] == "us-east-1"
    assert config["access_key_id"] == "AKIA..."


def test_to_redshift_soda_configuration_missing_username_raises(monkeypatch):
    monkeypatch.delenv("DATACONTRACT_REDSHIFT_USERNAME", raising=False)
    monkeypatch.setenv("DATACONTRACT_REDSHIFT_PASSWORD", "secret")

    with pytest.raises(DataContractException) as exc_info:
        to_redshift_soda_configuration(_server())
    assert exc_info.value.type == "redshift-connection"
