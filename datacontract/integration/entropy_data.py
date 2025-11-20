import os
from urllib.parse import urlparse

import requests

from datacontract.model.run import Run

# used to retrieve the HTML location of the published data contract or test results
RESPONSE_HEADER_LOCATION_HTML = "location-html"


def publish_test_results_to_entropy_data(run: Run, publish_url: str, ssl_verification: bool):
    try:
        host = publish_url
        if publish_url is None:
            # this url supports Data Mesh Manager and Data Contract Manager
            host = _get_host()
            url = "%s/api/test-results" % host
        else:
            url = publish_url

        api_key = _get_api_key()

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
            return
        run.log_info("Published test results successfully")

        location_html = response.headers.get(RESPONSE_HEADER_LOCATION_HTML)
        if location_html is not None and len(location_html) > 0:
            print(f"🚀 Open {location_html}")

    except Exception as e:
        run.log_error(f"Failed publishing test results. Error: {str(e)}")


def publish_data_contract_to_entropy_data(data_contract_dict: dict, ssl_verification: bool):
    try:
        api_key = _get_api_key()
        host = _get_host()
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


def _get_api_key() -> str:
    """
    Get API key from environment variables with fallback priority:
    1. ENTROPY_DATA_API_KEY
    2. DATAMESH_MANAGER_API_KEY
    3. DATACONTRACT_MANAGER_API_KEY
    """
    api_key = os.getenv("ENTROPY_DATA_API_KEY")
    if api_key is None:
        api_key = os.getenv("DATAMESH_MANAGER_API_KEY")
    if api_key is None:
        api_key = os.getenv("DATACONTRACT_MANAGER_API_KEY")
    if api_key is None:
        raise Exception(
            "Cannot publish, as neither ENTROPY_DATA_API_KEY, DATAMESH_MANAGER_API_KEY, nor DATACONTRACT_MANAGER_API_KEY is set"
        )
    return api_key


def _get_host() -> str:
    """
    Get host from environment variables with fallback priority:
    1. ENTROPY_DATA_HOST
    2. DATAMESH_MANAGER_HOST
    3. DATACONTRACT_MANAGER_HOST
    4. Default: https://api.entropy-data.com
    """
    host = os.getenv("ENTROPY_DATA_HOST")
    if host is None:
        host = os.getenv("DATAMESH_MANAGER_HOST")
    if host is None:
        host = os.getenv("DATACONTRACT_MANAGER_HOST")
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
