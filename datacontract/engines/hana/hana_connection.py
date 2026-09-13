from contextlib import contextmanager
from typing import Any

from open_data_contract_standard.model import Server

from datacontract.config import Config
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import ResultEnum


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


def get_connection(server: Server, config: Config | None = None) -> Any:
    dbapi = import_hdbcli()
    config = Config.resolve(config)
    username = config.get_hana_username(required=True)
    password = config.get_hana_password(required=True)
    encrypt = config.get_hana_encrypt()
    ssl_validate = config.get_hana_ssl_validate_certificate()
    ssl_hostname = config.get_hana_ssl_hostname_in_certificate() or "*"

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
def hana_connection(server: Server, config: Config | None = None):
    connection = get_connection(server, config)
    try:
        yield connection
    finally:
        connection.close()
