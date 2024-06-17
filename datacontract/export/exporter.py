from abc import ABC, abstractmethod
from enum import Enum
import typing

from datacontract.model.data_contract_specification import DataContractSpecification


class Exporter(ABC):
    @abstractmethod
    def export(self, export_args) -> dict:
        pass


class ExportFormat(str, Enum):
    jsonschema = "jsonschema"
    pydantic_model = "pydantic-model"
    sodacl = "sodacl"
    dbt = "dbt"
    dbt_sources = "dbt-sources"
    dbt_staging_sql = "dbt-staging-sql"
    odcs = "odcs"
    rdf = "rdf"
    avro = "avro"
    protobuf = "protobuf"
    great_expectations = "great-expectations"
    terraform = "terraform"
    avro_idl = "avro-idl"
    sql = "sql"
    sql_query = "sql-query"
    html = "html"
    go = "go"
    bigquery = "bigquery"
    dbml = "dbml"


class FactoryExporter:
    def __init__(self):
        self.dict_exporters = {}

    def add_exporter(self, name, exporter):
        self.dict_exporters.update({name: exporter})

    def get_exporter(self, name) -> Exporter:
        try:
            return self.dict_exporters[name]()
        except:
            raise Exception(f"Export format {name} not supported.")
