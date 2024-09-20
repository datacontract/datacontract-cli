import os

import requests

from datacontract.model.exceptions import DataContractException


def fetch_resource(url: str):
    headers = {
        "accept": "application/yaml",
    }

    _set_api_key(headers, url)
    response = requests.get(url, headers=headers)
    if response.status_code == 200:
        return response.text
    else:
        raise DataContractException(
            type="lint",
            name=f"Reading data contract from {url}",
            reason=f"Cannot read resource from URL {url}. Response status is {response.status_code}",
            engine="datacontract",
            result="error",
        )


def _set_api_key(headers, url):
    if ".datamesh-manager.com/" in url:
        datamesh_manager_api_key = os.getenv("DATAMESH_MANAGER_API_KEY")
        if datamesh_manager_api_key is None or datamesh_manager_api_key == "":
            print("Error: Data Mesh Manager API Key is not set. Set env variable DATAMESH_MANAGER_API_KEY.")
            raise DataContractException(
                type="lint",
                name=f"Reading data contract from {url}",
                reason="Error: Data Mesh Manager API Key is not set. Set env variable DATAMESH_MANAGER_API_KEY.",
                engine="datacontract",
                result="error",
            )
        headers["x-api-key"] = datamesh_manager_api_key
    elif ".datacontract-manager.com/" in url:
        datacontract_manager_api_key = os.getenv("DATACONTRACT_MANAGER_API_KEY")
        if datacontract_manager_api_key is None or datacontract_manager_api_key == "":
            print("Error: Data Contract Manager API Key is not set. Set env variable DATACONTRACT_MANAGER_API_KEY.")
            raise DataContractException(
                type="lint",
                name=f"Reading data contract from {url}",
                reason="Error: Data Contract Manager API Key is not set. Set env variable DATACONTRACT_MANAGER_API_KEY.",
                engine="datacontract",
                result="error",
            )
        headers["x-api-key"] = datacontract_manager_api_key
    else:
        # do nothing
        pass
