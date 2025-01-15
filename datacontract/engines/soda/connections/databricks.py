import os

import yaml


def to_databricks_soda_configuration(server):
    token = os.getenv("DATACONTRACT_DATABRICKS_TOKEN")
    if token is None:
        raise ValueError("DATACONTRACT_DATABRICKS_TOKEN environment variable is not set")
    http_path = os.getenv("DATACONTRACT_DATABRICKS_HTTP_PATH")
    host = server.host
    if host is None:
        host = os.getenv("DATACONTRACT_DATABRICKS_SERVER_HOSTNAME")
    if host is None:
        raise ValueError("DATACONTRACT_DATABRICKS_SERVER_HOSTNAME environment variable is not set")
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
