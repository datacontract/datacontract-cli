import os

import yaml
from open_data_contract_standard.model import Server


def initialize_client_and_create_soda_configuration(server: Server) -> str:
    import oracledb

    soda_config = to_oracle_soda_configuration(server)

    oracle_client_dir = os.getenv("DATACONTRACT_ORACLE_CLIENT_DIR")
    if oracle_client_dir is not None:
        # Soda Core currently does not support thick mode natively, see https://github.com/sodadata/soda-core/issues/2036
        #   but the oracledb client can be configured accordingly before Soda initializes as a work-around
        oracledb.init_oracle_client(lib_dir=oracle_client_dir)

    return soda_config


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

    service_name = server.serviceName or server.database
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
