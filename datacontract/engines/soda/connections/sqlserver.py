import os

import yaml
from datacontract.model.data_contract_specification import Server

def to_sqlserver_soda_configuration(server: Server) -> str:
    """Serialize server config to soda configuration.


    ### Example:
        type: sqlserver
        host: host
        port: '1433'
        username: simple
        password: simple_pass
        database: database
        schema: dbo
        trusted_connection: false
        encrypt: false
        trust_server_certificate: false
        driver: ODBC Driver 18 for SQL Server
  """
    # with service account key, using an external json file
    soda_configuration = {
        f"data_source {server.type}": {
            "type": "sqlserver",
            "host": server.host,
            "port": str(server.port),
            "username": os.getenv("DATACONTRACT_SQLSERVER_USERNAME"),
            "password": os.getenv("DATACONTRACT_SQLSERVER_PASSWORD"),
            "database": server.database,
            "schema": server.schema_,
            "trusted_connection": server.trusted_connection,
            "trust_server_certificate": server.trust_server_certificate,
            "encrypt": server.encrypt_connection,
            "driver": server.driver
        }
    }

    soda_configuration_str = yaml.dump(soda_configuration)
    return soda_configuration_str
