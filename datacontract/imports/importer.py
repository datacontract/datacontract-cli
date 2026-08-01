import typing
from abc import ABC, abstractmethod
from enum import Enum

from open_data_contract_standard.model import OpenDataContractStandard

if typing.TYPE_CHECKING:
    from datacontract.config import Config


class Importer(ABC):
    def __init__(self, import_format) -> None:
        self.import_format = import_format

    @abstractmethod
    def import_source(
        self,
        source: str,
        import_args: dict,
        config: "Config | None" = None,
    ) -> OpenDataContractStandard:
        """Import a data contract from a source.

        All importers now return OpenDataContractStandard (ODCS) format.
        ``config`` carries credentials and connection options; implementations
        that do not need credentials can ignore it. Importers registered with
        the two-argument signature keep working: the caller only passes
        ``config`` when the implementation declares the parameter.
        """
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
    databricks = "databricks"
    spark = "spark"
    iceberg = "iceberg"
    parquet = "parquet"
    csv = "csv"
    protobuf = "protobuf"
    excel = "excel"
    powerbi = "powerbi"
    snowflake = "snowflake"
    redshift = "redshift"
    postgres = "postgres"
    athena = "athena"
    s3 = "s3"
    mysql = "mysql"
    sqlserver = "sqlserver"
    gcs = "gcs"
    adls = "adls"
    oracle = "oracle"
    trino = "trino"

    @classmethod
    def get_supported_formats(cls):
        return list(map(lambda c: c.value, cls))
