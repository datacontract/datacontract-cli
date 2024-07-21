import os

import yaml


def to_snowflake_soda_configuration(server):
    prefix = "DATACONTRACT_SNOWFLAKE_"
    snowflake_soda_params = {k.replace(prefix, "").lower(): v for k, v in os.environ.items() if k.startswith(prefix)}

    # backward compatibility
    if "connection_timeout" not in snowflake_soda_params:
        snowflake_soda_params["connection_timeout"] = "5"  # minutes

    soda_configuration = {
        f"data_source {server.type}": {
            "type": "snowflake",
            "account": server.account,
            "database": server.database,
            "schema": server.schema_,
            **snowflake_soda_params,
        }
    }
    soda_configuration_str = yaml.dump(soda_configuration)
    return soda_configuration_str
