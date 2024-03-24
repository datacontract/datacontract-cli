import os

import yaml


def to_databricks_soda_configuration(server):
    soda_configuration = {
        f"data_source {server.type}": {
            "type": "spark",
            "method": "databricks",
            "host": server.host,
            "catalog": server.catalog,
            "schema": server.schema_,
            "http_path": os.getenv("DATACONTRACT_DATABRICKS_HTTP_PATH"),
            "token": os.getenv("DATACONTRACT_DATABRICKS_TOKEN"),
        }
    }

    soda_configuration_str = yaml.dump(soda_configuration)
    return soda_configuration_str
