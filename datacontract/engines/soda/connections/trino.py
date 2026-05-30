import os

import yaml

from datacontract.model.exceptions import require_env


def to_trino_soda_configuration(server):
    # trino always needs a user for session headers; password missing falls back to NoAuthentication.
    username = require_env("DATACONTRACT_TRINO_USERNAME", server_type="trino")
    password = os.getenv("DATACONTRACT_TRINO_PASSWORD")

    data_source = {
        "type": "trino",
        "host": server.host,
        "port": str(server.port),
        "username": username,
        "password": password,
        "catalog": server.catalog,
        "schema": server.schema_,
    }

    if password is None or password == "":
        data_source["auth_type"] = "NoAuthentication"  # default is BasicAuthentication

    soda_configuration = {f"data_source {server.type}": data_source}

    soda_configuration_str = yaml.dump(soda_configuration)
    return soda_configuration_str
