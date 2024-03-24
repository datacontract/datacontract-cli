import os

import yaml


def to_snowflake_soda_configuration(server):
    soda_configuration = {
        f"data_source {server.type}": {
            "type": "snowflake",
            "username": os.getenv("DATACONTRACT_SNOWFLAKE_USERNAME"),
            "password": os.getenv("DATACONTRACT_SNOWFLAKE_PASSWORD"),
            "role": os.getenv("DATACONTRACT_SNOWFLAKE_ROLE"),
            "account": server.account,
            "database": server.database,
            "schema": server.schema_,
            "warehouse": os.getenv("DATACONTRACT_SNOWFLAKE_WAREHOUSE"),
            "connection_timeout": 5,  # minutes
        }
    }
    soda_configuration_str = yaml.dump(soda_configuration)
    return soda_configuration_str
