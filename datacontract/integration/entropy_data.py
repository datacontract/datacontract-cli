from urllib.parse import urlparse

import requests

from datacontract.config import Config
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import ResultEnum, Run

# used to retrieve the HTML location of the published data contract or test results
RESPONSE_HEADER_LOCATION_HTML = "location-html"


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

        api_key = _get_api_key(config)

        if run.dataContractId is None:
            raise Exception("Cannot publish run results for unknown data contract ID")

        headers = {"Content-Type": "application/json", "x-api-key": api_key}
        request_body = run.model_dump_json()
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
    data_contract_dict: dict, ssl_verification: bool = True, config: Config | None = None
) -> str | None:
    """Publish the data contract to the Entropy Data instance.

    Returns the HTML location of the published data contract, if the server reports one.
    Raises a DataContractException if publishing failed, so that callers (the CLI as well
    as library users) can handle the failure themselves.
    """
    config = Config.resolve(config)
    api_key = _get_api_key(config)
    host = _get_host(config)
    display_host = _extract_hostname(host)
    headers = {"Content-Type": "application/json", "x-api-key": api_key}
    id = data_contract_dict.get("id")
    if not id:
        raise _publish_error("Cannot publish a data contract without an id")
    url = f"{host}/api/datacontracts/{id}"
    try:
        response = requests.put(
            url=url,
            json=data_contract_dict,
            headers=headers,
            verify=ssl_verification,
        )
    except Exception as e:
        raise _publish_error(f"Failed publishing data contract to {display_host}: {str(e)}", e)

    if response.status_code != 200:
        raise _publish_error(f"Error publishing data contract to {display_host}: {response.text}")

    return response.headers.get(RESPONSE_HEADER_LOCATION_HTML) or None


def _publish_error(reason: str, original_exception: Exception | None = None) -> DataContractException:
    return DataContractException(
        type="publish",
        name="Publish data contract",
        reason=reason,
        result=ResultEnum.error,
        original_exception=original_exception,
    )


def _get_api_key(config: Config) -> str:
    """
    Get API key from the config or environment variables with fallback priority:
    1. ENTROPY_DATA_API_KEY
    2. DATAMESH_MANAGER_API_KEY
    3. DATACONTRACT_MANAGER_API_KEY
    """
    api_key = _get_api_key_or_none(config)
    if api_key is None:
        raise _publish_error(
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
