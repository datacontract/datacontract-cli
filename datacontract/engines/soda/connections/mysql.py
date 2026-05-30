import yaml

from datacontract.model.exceptions import require_env


def to_mysql_soda_configuration(server):
    soda_configuration = {
        f"data_source {server.type}": {
            "type": "mysql",
            "host": server.host,
            "port": str(server.port),
            "username": require_env("DATACONTRACT_MYSQL_USERNAME", server_type="mysql"),
            "password": require_env("DATACONTRACT_MYSQL_PASSWORD", server_type="mysql"),
            "database": server.database,
        }
    }

    soda_configuration_str = yaml.dump(soda_configuration)
    return soda_configuration_str
