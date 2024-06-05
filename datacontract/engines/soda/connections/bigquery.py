import os

import yaml


# https://docs.soda.io/soda/connect-bigquery.html#authentication-methods
def to_bigquery_soda_configuration(server):
    # with service account key, using an external json file

    # check for our own environment variable first
    account_info = os.getenv("DATACONTRACT_BIGQUERY_ACCOUNT_INFO_JSON_PATH")
    if account_info is None:
        # but as a fallback look for the default google one
        account_info = os.getenv("GOOGLE_APPLICATION_CREDENTIALS")

    soda_configuration = {
        f"data_source {server.type}": {
            "type": "bigquery",
            "account_info_json_path": account_info,
            "auth_scopes": ["https://www.googleapis.com/auth/bigquery"],
            "project_id": server.project,
            "dataset": server.dataset,
        }
    }

    soda_configuration_str = yaml.dump(soda_configuration)
    return soda_configuration_str
