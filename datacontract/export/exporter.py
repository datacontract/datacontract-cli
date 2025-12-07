import typing
from abc import ABC, abstractmethod
from enum import Enum

from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject


class Exporter(ABC):
    def __init__(self, export_format) -> None:
        self.export_format = export_format

    @abstractmethod
    def export(
        self,
        data_contract: OpenDataContractStandard,
        schema_name: str,
        server: str,
        sql_server_type: str,
        export_args: dict,
    ) -> dict | str:
        """Export a data contract to the target format.

        Args:
            data_contract: The ODCS data contract to export.
            schema_name: The name of the schema to export, or 'all' for all schemas.
            server: The server name to use for export.
            sql_server_type: The SQL server type for dialect-specific exports.
            export_args: Additional export arguments.

        All exporters now accept OpenDataContractStandard (ODCS) format.
        """
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
    avro_idl = "avro-idl"
    sql = "sql"
    sql_query = "sql-query"
    mermaid = "mermaid"
    html = "html"
    go = "go"
    bigquery = "bigquery"
    dbml = "dbml"
    spark = "spark"
    sqlalchemy = "sqlalchemy"
    data_caterer = "data-caterer"
    dcs = "dcs"
    markdown = "markdown"
    iceberg = "iceberg"
    custom = "custom"
    excel = "excel"
    dqx = "dqx"

    @classmethod
    def get_supported_formats(cls):
        return list(map(lambda c: c.value, cls))


def _check_schema_name_for_export(
    data_contract: OpenDataContractStandard, schema_name: str, export_format: str
) -> typing.Tuple[str, SchemaObject]:
    """Check and retrieve a schema from the data contract for export.

    In ODCS, schemas are stored in schema_ as a list of SchemaObject.
    """
    if data_contract.schema_ is None or len(data_contract.schema_) == 0:
        raise RuntimeError(f"Export to {export_format} requires schema in the data contract.")

    schema_names = [schema.name for schema in data_contract.schema_]

    if schema_name == "all":
        if len(data_contract.schema_) != 1:
            raise RuntimeError(
                f"Export to {export_format} requires a specific schema. Specify the schema via --schema-name. Available schemas: {schema_names}"
            )

        schema_obj = data_contract.schema_[0]
        return schema_obj.name, schema_obj
    else:
        schema_obj = next((s for s in data_contract.schema_ if s.name == schema_name), None)
        if schema_obj is None:
            raise RuntimeError(f"Schema '{schema_name}' not found in the data contract. Available schemas: {schema_names}")

        return schema_name, schema_obj


def _determine_sql_server_type(
    data_contract: OpenDataContractStandard, sql_server_type: str, server: str = None
) -> str:
    """Determine the SQL server type from the data contract servers."""
    if sql_server_type == "auto":
        if data_contract.servers is None or len(data_contract.servers) == 0:
            raise RuntimeError("Export with server_type='auto' requires servers in the data contract.")

        if server is None:
            server_types = set([s.type for s in data_contract.servers])
        else:
            server_obj = next((s for s in data_contract.servers if s.server == server), None)
            server_types = {server_obj.type} if server_obj else set()

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
