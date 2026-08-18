import requests

from datacontract.config import Config
from datacontract.integration.entropy_data import _get_api_key_or_none, is_platform_url
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import ResultEnum


def fetch_resource(url: str, config: Config | None = None):
    config = Config.resolve(config)
    headers = {
        "accept": "application/yaml",
    }

    _set_api_key(headers, url, config)
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.text
    else:
        raise DataContractException(
            type="lint",
            name=f"Reading data contract from {url}",
            reason=f"Cannot read resource from URL {url}. Response status is {response.status_code}",
            engine="datacontract",
            result=ResultEnum.error,
        )


def _set_api_key(headers, url, config: Config):
    """Attach the API key, but only when the URL is on the Entropy Data host.

    A data contract location is whatever the user names, so a URL on any other
    host is fetched anonymously: the key must never be handed to a third party
    that happens to serve a contract.
    """
    if not is_platform_url(url, config):
        return

    api_key = _get_api_key_or_none(config)
    if api_key is None:
        raise DataContractException(
            type="lint",
            name=f"Reading data contract from {url}",
            reason="Error: Entropy Data API key is not set. Set env variable ENTROPY_DATA_API_KEY.",
            engine="datacontract",
            result=ResultEnum.error,
        )
    headers["x-api-key"] = api_key
