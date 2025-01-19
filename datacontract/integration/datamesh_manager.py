import os

import requests

from datacontract.model.run import Run


def publish_test_results_to_datamesh_manager(run: Run, publish_url: str, ssl_verification: bool):
    try:
        if publish_url is None:
            # this url supports Data Mesh Manager and Data Contract Manager
            url = "https://api.datamesh-manager.com/api/test-results"
        else:
            url = publish_url

        api_key = os.getenv("DATAMESH_MANAGER_API_KEY")
        if api_key is None:
            api_key = os.getenv("DATACONTRACT_MANAGER_API_KEY")
        if api_key is None:
            raise Exception(
                "Cannot publish run results, as DATAMESH_MANAGER_API_KEY nor DATACONTRACT_MANAGER_API_KEY are not set"
            )

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
            run.log_error(f"Error publishing test results to Data Mesh Manager: {response.text}")
            return
        run.log_info(f"Published test results to {url}")
    except Exception as e:
        run.log_error(f"Failed publishing test results. Error: {str(e)}")


def publish_data_contract_to_datamesh_manager(data_contract_dict: dict, ssl_verification: bool):
    try:
        api_key = os.getenv("DATAMESH_MANAGER_API_KEY")
        host = "https://api.datamesh-manager.com"
        if os.getenv("DATAMESH_MANAGER_HOST") is not None:
            host = os.getenv("DATAMESH_MANAGER_HOST")
        if api_key is None:
            api_key = os.getenv("DATACONTRACT_MANAGER_API_KEY")
        if api_key is None:
            raise Exception(
                "Cannot publish data contract, as neither DATAMESH_MANAGER_API_KEY nor DATACONTRACT_MANAGER_API_KEY is set"
            )
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
            print(f"Error publishing data contract to Data Mesh Manager: {response.text}")
            exit(1)
        print(f"Published data contract to {url}")
    except Exception as e:
        print(f"Failed publishing data contract. Error: {str(e)}")
