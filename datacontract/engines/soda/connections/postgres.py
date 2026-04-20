import os

import yaml


def to_postgres_soda_configuration(server):
    # with service account key, using an external json file
    soda_configuration = {
        f"data_source {server.type}": {
            "type": "postgres",
            "host": os.getenv("DATACONTRACT_POSTGRES_HOST", server.host),
            "port": os.getenv("DATACONTRACT_POSTGRES_PORT", str(server.port)),
            "username": os.getenv("DATACONTRACT_POSTGRES_USERNAME"),
            "password": os.getenv("DATACONTRACT_POSTGRES_PASSWORD"),
            "database": os.getenv("DATACONTRACT_POSTGRES_DATABASE", server.database),
            "schema": os.getenv("DATACONTRACT_POSTGRES_SCHEMA", server.schema_),
        }
    }

    soda_configuration_str = yaml.dump(soda_configuration)
    return soda_configuration_str