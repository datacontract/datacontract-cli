import os

import yaml
from open_data_contract_standard.model import Server


def _get_custom_property(server: Server, name: str) -> str | None:
    """Get a custom property value from server.customProperties."""
    if server.customProperties:
        for prop in server.customProperties:
            if prop.property == name:
                return prop.value
    return None


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
            "username": os.getenv("DATACONTRACT_SQLSERVER_USERNAME", ""),
            "password": os.getenv("DATACONTRACT_SQLSERVER_PASSWORD", ""),
            "database": server.database,
            "schema": server.schema_,
            "trusted_connection": os.getenv("DATACONTRACT_SQLSERVER_TRUSTED_CONNECTION", False),
            "trust_server_certificate": os.getenv("DATACONTRACT_SQLSERVER_TRUST_SERVER_CERTIFICATE", False),
            "encrypt": os.getenv("DATACONTRACT_SQLSERVER_ENCRYPTED_CONNECTION", True),
            "driver": _get_custom_property(server, "driver") or os.getenv("DATACONTRACT_SQLSERVER_DRIVER"),
        }
    }

    soda_configuration_str = yaml.dump(soda_configuration)
    return soda_configuration_str
