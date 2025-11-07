import os

import yaml

from datacontract.model.data_contract_specification import Server


def to_oracle_soda_configuration(server: Server) -> str:
    """Serialize server config to soda configuration.


    ### Example:
        type: oracle
        host: database-1.us-east-1.rds.amazonaws.com
        port: '1521'
        username: simple
        password: simple_pass
        connectstring: database-1.us-east-1.rds.amazonaws.com:1521/ORCL (database is equal to service name at oracle)
        schema: SYSTEM
    """

    service_name = server.service_name or server.database
    # with service account key, using an external json file
    soda_configuration = {
        f"data_source {server.type}": {
            "type": "oracle",
            "host": server.host,
            "port": str(server.port),
            "username": os.getenv("DATACONTRACT_ORACLE_USERNAME", ""),
            "password": os.getenv("DATACONTRACT_ORACLE_PASSWORD", ""),
            "connectstring": f"{server.host}:{server.port}/{service_name}",
            "schema": server.schema_,
        }
    }

    soda_configuration_str = yaml.dump(soda_configuration)
    return soda_configuration_str
