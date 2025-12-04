import os

import yaml


def to_impala_soda_configuration(server):
    """
    Build a Soda configuration for an Impala data source.

    Expects the datacontract `server` object to have at least:
      - type     (e.g. "impala")
      - host
      - port     (optional; defaults to 443 if not set)
      - database (optional)

    Credentials are taken from environment variables:
      - DATACONTRACT_IMPALA_USERNAME
      - DATACONTRACT_IMPALA_PASSWORD
    """

    # Default port if not provided
    port = getattr(server, "port", None) or 443

    # Optional default database
    database = getattr(server, "database", None)

    connection = {
        "host": server.host,
        "port": str(port),
        "username": os.getenv("DATACONTRACT_IMPALA_USERNAME"),
        "password": os.getenv("DATACONTRACT_IMPALA_PASSWORD"),
        "use_ssl": True,
        "auth_mechanism": "LDAP",
        "use_http_transport": True,
        "http_path": "cliservice",
    }

    if database:
        connection["database"] = database

    soda_configuration = {
        # We keep the data_source name equal to server.type ("impala")
        # because check_soda_execute will call scan.set_data_source_name("impala").
        f"data_source {server.type}": {
            "type": "impala",
            "connection": connection,
        }
    }

    soda_configuration_str = yaml.dump(soda_configuration)
    return soda_configuration_str
