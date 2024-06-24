from abc import ABC, abstractmethod
from enum import Enum

from datacontract.model.data_contract_specification import DataContractSpecification


class Importer(ABC):
    def __init__(self, import_format) -> None:
        self.import_format = import_format

    @abstractmethod
    def import_source(
        self, data_contract_specification: DataContractSpecification, source: str, import_args: dict
    ) -> dict:
        pass


class ImportFormat(str, Enum):
    sql = "sql"
    avro = "avro"
    glue = "glue"
    jsonschema = "jsonschema"
    bigquery = "bigquery"
    odcs = "odcs"
    unity = "unity"

    @classmethod
    def get_suported_formats(cls):
        return list(map(lambda c: c.value, cls))
