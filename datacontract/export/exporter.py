from abc import ABC, abstractmethod
from enum import Enum


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
