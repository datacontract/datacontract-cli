import os

import yaml

from datacontract.model.exceptions import require_env

_PASSTHROUGH_EXCLUDED = {"DATACONTRACT_REDSHIFT_USERNAME", "DATACONTRACT_REDSHIFT_PASSWORD"}


def to_redshift_soda_configuration(server):
    prefix = "DATACONTRACT_REDSHIFT_"
    extra = {
        k.replace(prefix, "").lower(): v
        for k, v in os.environ.items()
        if k.startswith(prefix) and k not in _PASSTHROUGH_EXCLUDED
    }
    soda_configuration = {
        f"data_source {server.type}": {
            "type": "redshift",
            "host": server.host,
            "port": str(server.port),
            "username": require_env("DATACONTRACT_REDSHIFT_USERNAME", server_type="redshift"),
            "password": require_env("DATACONTRACT_REDSHIFT_PASSWORD", server_type="redshift"),
            "database": server.database,
            "schema": server.schema_,
            **extra,
        }
    }
    return yaml.dump(soda_configuration)
