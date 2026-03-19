import os

import yaml


# https://docs.soda.io/soda/connect-bigquery.html#authentication-methods
def to_bigquery_soda_configuration(server):
    data_source = {
        "type": "bigquery",
        "project_id": server.project,
        "dataset": server.dataset,
    }

    if "DATACONTRACT_BIGQUERY_ACCOUNT_INFO_JSON_PATH" in os.environ:
        data_source["account_info_json_path"] = os.environ["DATACONTRACT_BIGQUERY_ACCOUNT_INFO_JSON_PATH"]
        data_source["auth_scopes"] = ["https://www.googleapis.com/auth/bigquery"]
    else:
        data_source["use_context_auth"] = True

    if "DATACONTRACT_BIGQUERY_IMPERSONATION_ACCOUNT" in os.environ:
        data_source["impersonation_account"] = os.environ["DATACONTRACT_BIGQUERY_IMPERSONATION_ACCOUNT"]

    soda_configuration_str = yaml.dump({f"data_source {server.type}": data_source})
    return soda_configuration_str
