import os
from abc import ABC, abstractmethod
from enum import Enum
from urllib.parse import urlparse

import fsspec
from datacontract_specification.model import DataContractSpecification
from open_data_contract_standard.model import OpenDataContractStandard


class Importer(ABC):
    def __init__(self, import_format) -> None:
        self.import_format = import_format

    @abstractmethod
    def import_source(
        self,
        data_contract_specification: DataContractSpecification | OpenDataContractStandard,
        source: str,
        import_args: dict,
    ) -> DataContractSpecification | OpenDataContractStandard:
        pass


class ImportFormat(str, Enum):
    sql = "sql"
    avro = "avro"
    dbt = "dbt"
    dbml = "dbml"
    glue = "glue"
    jsonschema = "jsonschema"
    json = "json"
    bigquery = "bigquery"
    odcs = "odcs"
    unity = "unity"
    spark = "spark"
    iceberg = "iceberg"
    parquet = "parquet"
    csv = "csv"
    protobuf = "protobuf"
    excel = "excel"

    @classmethod
    def get_supported_formats(cls):
        return list(map(lambda c: c.value, cls))


class Spec(str, Enum):
    datacontract_specification = "datacontract_specification"
    odcs = "odcs"

    @classmethod
    def get_supported_types(cls):
        return list(map(lambda c: c.value, cls))


def setup_sftp_filesystem(url: str):
    parsed_url = urlparse(url)
    hostname = parsed_url.hostname if parsed_url.hostname is not None else "127.0.0.1"
    port = parsed_url.port if parsed_url.port is not None else 22
    sftp_user = os.getenv("DATACONTRACT_SFTP_USER")
    sftp_password = os.getenv("DATACONTRACT_SFTP_PASSWORD")
    if sftp_user is None or sftp_password is None:
        raise ValueError("Error: Environment variable DATACONTRACT_SFTP_USER is not set")
    if sftp_password is None:
        raise ValueError("Error: Environment variable DATACONTRACT_SFTP_PASSWORD is not set")
    return fsspec.filesystem("sftp", host=hostname, port=port, username=sftp_user, password=sftp_password)
