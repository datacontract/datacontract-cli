import os

import yaml

from datacontract.model.data_contract_specification import Server


def to_oracle_soda_configuration(server: Server) -> str:
    """Serialize server config to soda configuration.


    ### Example:
        type: sqlserver
        host: host
        port: '1433'
        username: simple
        password: simple_pass
        database: database (service name at oracle)
        schema: dbo
        trusted_connection: false
        encrypt: false
        trust_server_certificate: false
        driver: ODBC Driver 18 for SQL Server
    """
    # with service account key, using an external json file
    soda_configuration = {
        f"data_source {server.type}": {
            "type": "oracle",
            "host": server.host,
            "port": str(server.port),
            "username": os.getenv("DATACONTRACT_ORACLE_USERNAME", ""),
            "password": os.getenv("DATACONTRACT_ORACLE_PASSWORD", ""),
            "connectstring": f"{server.host}:{server.port}/{server.database}",
            "schema": server.schema_,
            "driver": server.driver,
        }
    }

    soda_configuration_str = yaml.dump(soda_configuration)
    return soda_configuration_str
