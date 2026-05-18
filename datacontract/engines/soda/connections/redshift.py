import os

import yaml

from datacontract.model.exceptions import require_env


def to_redshift_soda_configuration(server):
    prefix = "DATACONTRACT_REDSHIFT_"
    extra = {
        k.removeprefix(prefix).lower(): v
        for k, v in os.environ.items()
        if k.startswith(prefix) and k not in {"DATACONTRACT_REDSHIFT_USERNAME", "DATACONTRACT_REDSHIFT_PASSWORD"}
    }
    data_source = {
        **extra,
        "type": "redshift",
        "host": server.host,
        "port": str(server.port),
        "username": require_env("DATACONTRACT_REDSHIFT_USERNAME", server_type="redshift"),
        "database": server.database,
        "schema": server.schema_,
    }
    # Password is optional: when absent, soda-core-redshift enters IAM mode and
    # derives temporary credentials from access_key_id / secret_access_key / region.
    password = os.getenv("DATACONTRACT_REDSHIFT_PASSWORD")
    if password:
        data_source["password"] = password
    return yaml.dump({f"data_source {server.type}": data_source})
