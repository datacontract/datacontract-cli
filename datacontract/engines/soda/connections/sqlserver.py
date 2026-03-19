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
        authentication: sql
        trusted_connection: false
        encrypt: false
        trust_server_certificate: false
        driver: ODBC Driver 18 for SQL Server

    ### Supported authentication modes:
        - sql (default): SQL Server authentication with username/password
        - windows: Windows integrated authentication (Kerberos/NTLM), sets trusted_connection
        - ActiveDirectoryPassword: Azure AD / Entra ID with username/password
        - ActiveDirectoryServicePrincipal: Azure AD / Entra ID with client_id/client_secret
        - ActiveDirectoryInteractive: Azure AD / Entra ID with browser-based login
    """
    authentication_env = os.getenv("DATACONTRACT_SQLSERVER_AUTHENTICATION", "sql").lower()
    # Legacy for Windows authentication
    trusted_connection_env = os.getenv("DATACONTRACT_SQLSERVER_TRUSTED_CONNECTION", "false").lower()

    if trusted_connection_env == "true" or authentication_env == "windows":
        authentication_soda = "sql"
        trusted_connection_soda = True
    else:
        authentication_soda = authentication_env
        trusted_connection_soda = False

    soda_configuration = {
        f"data_source {server.type}": {
            "type": "sqlserver",
            "host": server.host,
            "port": str(server.port),
            "username": os.getenv("DATACONTRACT_SQLSERVER_USERNAME", ""),
            "password": os.getenv("DATACONTRACT_SQLSERVER_PASSWORD", ""),
            "database": server.database,
            "schema": server.schema_,
            "authentication": authentication_soda,
            "trusted_connection": trusted_connection_soda,
            "client_id": os.getenv("DATACONTRACT_SQLSERVER_CLIENT_ID", ""),
            "client_secret": os.getenv("DATACONTRACT_SQLSERVER_CLIENT_SECRET", ""),
            "trust_server_certificate": os.getenv("DATACONTRACT_SQLSERVER_TRUST_SERVER_CERTIFICATE", False),
            "encrypt": os.getenv("DATACONTRACT_SQLSERVER_ENCRYPTED_CONNECTION", True),
            "driver": _get_custom_property(server, "driver") or os.getenv("DATACONTRACT_SQLSERVER_DRIVER"),
        }
    }

    soda_configuration_str = yaml.dump(soda_configuration)
    return soda_configuration_str
