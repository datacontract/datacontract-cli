import yaml

from datacontract.model.exceptions import require_env


def to_postgres_soda_configuration(server):
    # with service account key, using an external json file
    soda_configuration = {
        f"data_source {server.type}": {
            "type": "postgres",
            "host": server.host,
            "port": str(server.port),
            "username": require_env("DATACONTRACT_POSTGRES_USERNAME", server_type="postgres"),
            "password": require_env("DATACONTRACT_POSTGRES_PASSWORD", server_type="postgres"),
            "database": server.database,
            "schema": server.schema_,
        }
    }

    soda_configuration_str = yaml.dump(soda_configuration)
    return soda_configuration_str
