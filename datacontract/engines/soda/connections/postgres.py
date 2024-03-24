import os

import yaml


def to_postgres_soda_configuration(server):
    # with service account key, using an external json file
    soda_configuration = {
        f"data_source {server.type}": {
            "type": "postgres",
            "host": server.host,
            "port": str(server.port),
            "username": os.getenv("DATACONTRACT_POSTGRES_USERNAME"),
            "password": os.getenv("DATACONTRACT_POSTGRES_PASSWORD"),
            "database": server.database,
            "schema": server.schema_,
        }
    }

    soda_configuration_str = yaml.dump(soda_configuration)
    return soda_configuration_str
