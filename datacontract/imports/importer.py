from abc import ABC, abstractmethod
from enum import Enum

from datacontract.model.data_contract_specification import DataContractSpecification


class Importer(ABC):
    def __init__(self, import_format) -> None:
        self.import_format = import_format

    @abstractmethod
    def import_source(
        self,
        data_contract_specification: DataContractSpecification,
        source: str,
        import_args: dict,
    ) -> DataContractSpecification:
        pass


class ImportFormat(str, Enum):
    sql = "sql"
    avro = "avro"
    dbt = "dbt"
    dbml = "dbml"
    glue = "glue"
    jsonschema = "jsonschema"
    bigquery = "bigquery"
    odcs = "odcs"
    unity = "unity"
    spark = "spark"

    @classmethod
    def get_supported_formats(cls):
        return list(map(lambda c: c.value, cls))
