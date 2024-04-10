import os

import requests

from datacontract.model.run import Run


def publish_datamesh_manager(run: Run, publish_url: str):
    try:
        if publish_url is None:
            url = "https://api.datamesh-manager.com/api/runs"
        else:
            url = publish_url
        datamesh_manager_api_key = os.getenv("DATAMESH_MANAGER_API_KEY")

        if run.dataContractId is None:
            raise Exception("Cannot publish run results, as data contract ID is unknown")

        if datamesh_manager_api_key is None:
            raise Exception("Cannot publish run results, as DATAMESH_MANAGER_API_KEY is not set")

        headers = {"Content-Type": "application/json", "x-api-key": datamesh_manager_api_key}
        request_body = run.model_dump_json()
        # print("Request Body:", request_body)
        response = requests.post(url, data=request_body, headers=headers)
        # print("Status Code:", response.status_code)
        # print("Response Body:", response.text)
        if response.status_code != 200:
            run.log_error(f"Error publishing test results to Data Mesh Manager: {response.text}")
            return
        run.log_info(f"Published test results to {url}")
    except Exception as e:
        run.log_error(f"Failed publishing test results. Error: {str(e)}")
