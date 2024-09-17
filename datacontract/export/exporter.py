from abc import ABC, abstractmethod
from enum import Enum
import typing

from datacontract.model.data_contract_specification import DataContractSpecification


class Exporter(ABC):
    def __init__(self, export_format) -> None:
        self.export_format = export_format

    @abstractmethod
    def export(self, data_contract, model, server, sql_server_type, export_args) -> dict:
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
    spark = "spark"
    sqlalchemy = "sqlalchemy"
    data_caterer = "data-caterer"

    @classmethod
    def get_supported_formats(cls):
        return list(map(lambda c: c.value, cls))


def _check_models_for_export(
    data_contract: DataContractSpecification, model: str, export_format: str
) -> typing.Tuple[str, str]:
    if data_contract.models is None:
        raise RuntimeError(f"Export to {export_format} requires models in the data contract.")

    model_names = list(data_contract.models.keys())

    if model == "all":
        if len(data_contract.models.items()) != 1:
            raise RuntimeError(
                f"Export to {export_format} is model specific. Specify the model via --model $MODEL_NAME. Available models: {model_names}"
            )

        model_name, model_value = next(iter(data_contract.models.items()))
    else:
        model_name = model
        model_value = data_contract.models.get(model_name)
        if model_value is None:
            raise RuntimeError(f"Model {model_name} not found in the data contract. Available models: {model_names}")

    return model_name, model_value


def _determine_sql_server_type(data_contract: DataContractSpecification, sql_server_type: str, server: str = None):
    if sql_server_type == "auto":
        if data_contract.servers is None or len(data_contract.servers) == 0:
            raise RuntimeError("Export with server_type='auto' requires servers in the data contract.")

        if server is None:
            server_types = set([server.type for server in data_contract.servers.values()])
        else:
            server_types = {data_contract.servers[server].type}

        if "snowflake" in server_types:
            return "snowflake"
        elif "postgres" in server_types:
            return "postgres"
        elif "databricks" in server_types:
            return "databricks"
        else:
            # default to snowflake dialect
            return "snowflake"
    else:
        return sql_server_type
