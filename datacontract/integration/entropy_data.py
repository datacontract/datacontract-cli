from urllib.parse import urlparse

import requests

from datacontract.config import Config
from datacontract.model.run import ResultEnum, Run

# used to retrieve the HTML location of the published data contract or test results
RESPONSE_HEADER_LOCATION_HTML = "location-html"

# The domains the platform serves under. `datamesh-manager.com` and
# `datacontract-manager.com` are the product's former names.
_PLATFORM_DOMAINS = ("entropy-data.com", "datamesh-manager.com", "datacontract-manager.com")


def is_platform_url(url: str, config: "Config | None" = None) -> bool:
    """True when `url` points at the Entropy Data platform.

    The API key is only ever sent to a host that answers for it: one of the
    platform's own domains, or the host of a self-hosted deployment named by
    ENTROPY_DATA_HOST (or its deprecated synonyms). Contract locations and
    publish URLs are arbitrary user input -- `datacontract lint
    https://example.com/datacontract.yaml` fetches whatever URL it is given --
    so every other host is contacted anonymously rather than handed the key.
    """
    config = Config.resolve(config)
    target = urlparse(url)
    if target.hostname is None:
        return False
    if any(target.hostname == domain or target.hostname.endswith(f".{domain}") for domain in _PLATFORM_DOMAINS):
        return True
    return any(
        configured is not None and _host_and_port(configured) == _host_and_port(url)
        for configured in (
            config.get_entropy_data_host(),
            config.get_datamesh_manager_host(),
            config.get_datacontract_manager_host(),
        )
    )


def _host_and_port(url: str) -> tuple[str | None, int | None]:
    """The host and port of a URL, which a configured host may be written without a scheme."""
    try:
        parsed = urlparse(url if "//" in url else f"https://{url}")
        return parsed.hostname, parsed.port
    except ValueError:  # an unparseable port
        return None, None


def publish_test_results_to_entropy_data(
    run: Run, publish_url: str, ssl_verification: bool, config: Config | None = None
) -> bool:
    """Publish `run` to the Entropy Data instance. Returns True on success, False otherwise."""
    try:
        config = Config.resolve(config)
        host = publish_url
        if publish_url is None:
            # this url supports Data Mesh Manager and Data Contract Manager
            host = _get_host(config)
            url = "%s/api/test-results" % host
        else:
            url = publish_url

        if run.dataContractId is None:
            raise Exception("Cannot publish run results for unknown data contract ID")

        headers = {"Content-Type": "application/json"}
        # `publish_url` is arbitrary input -- a CLI option, and a query parameter on the
        # API server's /test endpoint -- so the key goes only to the platform it belongs to.
        if is_platform_url(url, config):
            headers["x-api-key"] = _get_api_key(config)
        else:
            run.log_warn(
                f"Publishing to {_extract_hostname(url)} without an API key: it is not the Entropy Data host. "
                "Set ENTROPY_DATA_HOST to publish to a self-hosted deployment."
            )
        published_run = run.model_copy(
            update={"checks": [check for check in (run.checks or []) if check.result != ResultEnum.skipped]}
        )
        request_body = published_run.model_dump_json()
        # print("Request Body:", request_body)
        response = requests.post(
            url,
            data=request_body,
            headers=headers,
            verify=ssl_verification,
        )
        # print("Status Code:", response.status_code)
        # print("Response Body:", response.text)
        if response.status_code != 200:
            display_host = _extract_hostname(host)
            run.log_error(f"Error publishing test results to {display_host}: {response.text}")
            return False
        run.log_info("Published test results successfully")

        location_html = response.headers.get(RESPONSE_HEADER_LOCATION_HTML)
        if location_html is not None and len(location_html) > 0:
            print(f"🚀 Open {location_html}")
        return True

    except Exception as e:
        run.log_error(f"Failed publishing test results. Error: {str(e)}")
        return False


def publish_data_contract_to_entropy_data(
    data_contract_dict: dict, ssl_verification: bool, config: Config | None = None
):
    try:
        config = Config.resolve(config)
        api_key = _get_api_key(config)
        host = _get_host(config)
        headers = {"Content-Type": "application/json", "x-api-key": api_key}
        id = data_contract_dict["id"]
        url = f"{host}/api/datacontracts/{id}"
        response = requests.put(
            url=url,
            json=data_contract_dict,
            headers=headers,
            verify=ssl_verification,
        )
        if response.status_code != 200:
            display_host = _extract_hostname(host)
            print(f"Error publishing data contract to {display_host}: {response.text}")
            exit(1)

        print("✅ Published data contract successfully")

        location_html = response.headers.get(RESPONSE_HEADER_LOCATION_HTML)
        if location_html is not None and len(location_html) > 0:
            print(f"🚀 Open {location_html}")

    except Exception as e:
        print(f"Failed publishing data contract. Error: {str(e)}")


def _get_api_key(config: Config) -> str:
    """
    Get API key from the config or environment variables with fallback priority:
    1. ENTROPY_DATA_API_KEY
    2. DATAMESH_MANAGER_API_KEY
    3. DATACONTRACT_MANAGER_API_KEY
    """
    api_key = _get_api_key_or_none(config)
    if api_key is None:
        raise Exception(
            "Cannot publish, as neither ENTROPY_DATA_API_KEY, DATAMESH_MANAGER_API_KEY, nor DATACONTRACT_MANAGER_API_KEY is set"
        )
    return api_key


def _get_api_key_or_none(config: Config | None = None) -> str | None:
    """Same lookup as `_get_api_key` but returns None instead of raising;
    for callers that may legitimately fall back to anonymous requests."""
    config = Config.resolve(config)
    return (
        config.get_entropy_data_api_key()
        or config.get_datamesh_manager_api_key()
        or config.get_datacontract_manager_api_key()
    )


def _get_host(config: Config | None = None) -> str:
    """
    Get host from the config or environment variables with fallback priority:
    1. ENTROPY_DATA_HOST
    2. DATAMESH_MANAGER_HOST
    3. DATACONTRACT_MANAGER_HOST
    4. Default: https://api.entropy-data.com
    """
    config = Config.resolve(config)
    host = config.get_entropy_data_host()
    if host is None:
        host = config.get_datamesh_manager_host()
    if host is None:
        host = config.get_datacontract_manager_host()
    if host is None:
        host = "https://api.entropy-data.com"
    return host


def _extract_hostname(url: str) -> str:
    """
    Extract the hostname (including subdomains and top-level domain) from a URL.

    Examples:
    - https://app.entropy-data.com/path -> app.entropy-data.com
    - http://api.example.com:8080/api -> api.example.com
    """
    parsed = urlparse(url)
    return parsed.netloc.split(":")[0] if parsed.netloc else url
