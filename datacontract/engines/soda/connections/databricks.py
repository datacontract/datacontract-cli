import os

import yaml

from datacontract.model.exceptions import require_env


def to_databricks_soda_configuration(server):
    token = require_env("DATACONTRACT_DATABRICKS_TOKEN", server_type="databricks")
    http_path = os.getenv("DATACONTRACT_DATABRICKS_HTTP_PATH")
    host = server.host
    if host is None:
        host = require_env("DATACONTRACT_DATABRICKS_SERVER_HOSTNAME", server_type="databricks")
    soda_configuration = {
        f"data_source {server.type}": {
            "type": "spark",
            "method": "databricks",
            "host": host,
            "catalog": server.catalog,
            "schema": server.schema_,
            "http_path": http_path,
            "token": token,
        }
    }

    soda_configuration_str = yaml.dump(soda_configuration)
    return soda_configuration_str
