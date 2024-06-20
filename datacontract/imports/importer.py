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


#  if format == "sql":
#             data_contract_specification = import_sql(data_contract_specification, format, source)
#         elif format == "avro":
#             data_contract_specification = import_avro(data_contract_specification, source)
#         elif format == "glue":
#             data_contract_specification = import_glue(data_contract_specification, source, glue_tables)
#         elif format == "jsonschema":
#             data_contract_specification = import_jsonschema(data_contract_specification, source)
#         elif format == "bigquery":
#             if source is not None:
#                 data_contract_specification = import_bigquery_from_json(data_contract_specification, source)
#             else:
#                 data_contract_specification = import_bigquery_from_api(
#                     data_contract_specification, bigquery_tables, bigquery_project, bigquery_dataset
#                 )
#         elif format == "odcs":
#             data_contract_specification = import_odcs(data_contract_specification, source)
#         elif format == "unity":


class ImportFormat(str, Enum):
    sql = "sql"
    avro = "avro"
    glue = "glue"
    jsonschema = "jsonschema"
    bigquery = "bigquery"
    odcs = "odcs"
    unity = "unity"

    @classmethod
    def get_formats(cls):
        return cls.__dict__
