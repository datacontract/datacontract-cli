import logging
import os
from datetime import datetime, timezone

import requests

from datacontract.model.run import \
    Run, Log


def publish_datamesh_manager(run: Run, publish_url: str):
    if publish_url is None:
        url = f"https://api.datamesh-manager.com/api/checks/runs/{run.runId}"
    else:
        url = publish_url
    datamesh_manager_api_key = os.getenv('DATAMESH_MANAGER_API_KEY')

    if run.dataContractId is None:
        raise Exception("Cannot publish run results, as data contract ID is not set")

    if datamesh_manager_api_key is None:
        raise Exception("Cannot publish run results, as DATAMESH_MANAGER_API_KEY is not set")

    headers = {
        'Content-Type': 'application/json',
        'x-api-key': datamesh_manager_api_key
    }
    request_body = run.model_dump_json()
    # print("Request Body:", request_body)
    response = requests.put(url, data=request_body, headers=headers)
    # print("Status Code:", response.status_code)
    # print("Response Body:", response.text)
    if response.status_code != 200:
        logging.error(
            f"Error publishing test results to Data Mesh Manager: {response.text}")
        run.logs.append(Log(
            level="error",
            message=f"Error publishing test results to Data Mesh Manager: {response.text}",
            timestamp=datetime.now(timezone.utc)
        ))
        return
    logging.info("Published run summary to %s", url)
