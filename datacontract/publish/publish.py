import os

import requests

from datacontract.data_contract import DataContract


def publish_to_datamesh_manager(data_contract: DataContract):
    try:
        headers = {"Content-Type": "application/json", "x-api-key": _require_datamesh_manager_api_key()}
        spec = data_contract.get_data_contract_specification()
        id = spec.id
        url = "https://api.datamesh-manager.com/api/datacontracts/{0}".format(id)
        request_body = spec.model_dump_json().encode("utf-8")
        response = requests.put(
            url=url,
            data=request_body,
            headers=headers,
        )
        if response.status_code != 200:
            print(f"Error publishing data contract to Data Mesh Manager: {response.text}")
            exit(1)
        print(f"Published data contract to {url}")
    except Exception as e:
        print(f"Failed publishing data contract. Error: {str(e)}")


def _require_datamesh_manager_api_key():
    datamesh_manager_api_key = os.getenv("DATAMESH_MANAGER_API_KEY")
    if datamesh_manager_api_key is None:
        raise Exception("Cannot publish data contract, as DATAMESH_MANAGER_API_KEY is not set")
    return datamesh_manager_api_key
