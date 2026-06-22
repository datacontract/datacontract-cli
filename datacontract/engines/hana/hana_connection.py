import os
from contextlib import contextmanager
from typing import Any

from open_data_contract_standard.model import Server

from datacontract.model.exceptions import DataContractException, require_env
from datacontract.model.run import ResultEnum


def _env_bool(name: str, default: str = "true") -> bool:
    return os.getenv(name, default).lower() in ("true", "1", "yes")


def import_hdbcli():
    try:
        from hdbcli import dbapi

        return dbapi
    except ImportError as e:
        raise DataContractException(
            type="hana-connection",
            result=ResultEnum.failed,
            name="hdbcli is missing",
            reason="Install the extra datacontract-cli[hana] to use SAP HANA Cloud.",
            engine="hana",
            original_exception=e,
        )


def get_connection(server: Server) -> Any:
    dbapi = import_hdbcli()
    username = require_env("DATACONTRACT_HANA_USERNAME", server_type="hana")
    password = require_env("DATACONTRACT_HANA_PASSWORD", server_type="hana")
    encrypt = _env_bool("DATACONTRACT_HANA_ENCRYPT")
    ssl_validate = _env_bool("DATACONTRACT_HANA_SSL_VALIDATE_CERTIFICATE")
    ssl_hostname = os.getenv("DATACONTRACT_HANA_SSL_HOSTNAME_IN_CERTIFICATE", "*")

    try:
        return dbapi.connect(
            address=server.host,
            port=server.port or 443,
            user=username,
            password=password,
            encrypt=encrypt,
            sslValidateCertificate=ssl_validate,
            sslHostnameInCertificate=ssl_hostname,
        )
    except Exception as e:
        raise DataContractException(
            type="hana-connection",
            result=ResultEnum.failed,
            name="SAP HANA Cloud connection error",
            reason=str(e),
            engine="hana",
            original_exception=e,
        )


@contextmanager
def hana_connection(server: Server):
    connection = get_connection(server)
    try:
        yield connection
    finally:
        connection.close()
