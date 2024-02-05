import os
import yaml

# https://docs.soda.io/soda/connect-bigquery.html#authentication-methods
def to_bigquery_soda_configuration(server):
    soda_configuration = {
        f"data_source {server.type}": {
            "type": "bigquery",
            "use_context_auth": True,
            "auth_scopes": ["https://www.googleapis.com/auth/bigquery"],
            "project_id": server.project,
            "dataset": server.dataset
        }
    }
    soda_configuration_str = yaml.dump(soda_configuration)
    return soda_configuration_str