import pytest

from datacontract.integration.entropy_data import is_platform_url
from datacontract.lint.urls import _set_api_key
from datacontract.model.exceptions import DataContractException


@pytest.fixture(autouse=True)
def _clean_env(monkeypatch):
    for name in (
        "ENTROPY_DATA_API_KEY",
        "ENTROPY_DATA_HOST",
        "DATAMESH_MANAGER_API_KEY",
        "DATAMESH_MANAGER_HOST",
        "DATACONTRACT_MANAGER_API_KEY",
        "DATACONTRACT_MANAGER_HOST",
    ):
        monkeypatch.delenv(name, raising=False)


@pytest.mark.parametrize(
    "url",
    [
        "https://api.entropy-data.com/api/datacontracts/orders",
        "https://demo.entropy-data.com/tenant/datacontracts/orders/datacontract.yaml",
        "https://app.datamesh-manager.com/datacontracts/orders",
        "https://datacontract-manager.com/datacontracts/orders",
    ],
)
def test_platform_urls_are_recognized(url):
    assert is_platform_url(url)


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com/datacontract.yaml",
        # a domain that merely ends in the platform's name, and one that only prefixes it
        "https://notentropy-data.com/datacontract.yaml",
        "https://entropy-data.com.attacker.example/datacontract.yaml",
    ],
)
def test_other_urls_are_not_platform_urls(url):
    assert not is_platform_url(url)


def test_configured_self_hosted_host_is_a_platform_url(monkeypatch):
    monkeypatch.setenv("ENTROPY_DATA_HOST", "https://entropy.internal.example:8443")

    assert is_platform_url("https://entropy.internal.example:8443/datacontracts/orders")
    # same host, different deployment
    assert not is_platform_url("https://entropy.internal.example:9000/datacontracts/orders")


def test_api_key_is_not_sent_to_an_unrelated_host(monkeypatch):
    """A contract location is whatever the user names it, so a third party that
    happens to serve a contract must not receive the Entropy Data API key."""
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    headers = {}

    _set_api_key(headers, "https://example.com/datacontract.yaml", None)

    assert headers == {}


def test_api_key_is_sent_to_the_platform(monkeypatch):
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    headers = {}

    _set_api_key(headers, "https://demo.entropy-data.com/tenant/datacontract.yaml", None)

    assert headers["x-api-key"] == "test-key"


def test_missing_api_key_for_a_platform_url_is_reported(monkeypatch):
    with pytest.raises(DataContractException, match="ENTROPY_DATA_API_KEY"):
        _set_api_key({}, "https://api.entropy-data.com/api/datacontracts/orders", None)


def test_missing_api_key_for_another_host_is_not_an_error():
    headers = {}

    _set_api_key(headers, "https://example.com/datacontract.yaml", None)

    assert headers == {}
