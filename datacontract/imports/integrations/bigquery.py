from os import environ
from typing import Dict, List

from google.cloud.bigquery import Client, SchemaField

from datacontract.data_contract import DataContract
from datacontract.model.data_contract_specification import DataContractSpecification, Model, Field
from datacontract.imports import BaseDataContractImporter, ImporterArgument
from datacontract.model.exceptions import DataContractException


class BigQueryDataContractImporter(BaseDataContractImporter):
    """
    Importer for BigQuery tables.
    """

    # TODO: Extends importer to support multiple tables
    source = "bigquery"
    _arguments = [
        ImporterArgument(
            name="full_table_id",
            description="The full table id of the BigQuery table (project_id.dataset_id.table_id).",
            required=True,
            field_type=str,
        ),
        ImporterArgument(
            name="credentials",
            description="The path to the service account credentials file (If not set, the GOOGLE_APPLICATION_CREDENTIALS environment variable will be used).",
            required=False,
            field_type=str,
        ),
        ImporterArgument(
            name="billing_project_id",
            description="The project to use for billing purposes (If not set, the project_id from service account will be used).",
            required=False,
            field_type=str,
        ),
    ]

    def convert_fields(self, fields: List[SchemaField]) -> Dict[str, Field]:
        """
        Convert BigQuery fields to data contract fields model.
        """
        converted_fields = {}
        for bigquery_field in fields:
            converted_fields[bigquery_field.name] = Field(
                type=bigquery_field.field_type,
                required=bigquery_field.is_nullable,
                description=bigquery_field.description if bigquery_field.description else "",
            )
        return converted_fields

    def import_from_source(self, **kwargs) -> DataContractSpecification:
        self.set_atributes(**kwargs)
        data_contract_specification = DataContract().init()
        if hasattr(self, "credentials"):
            if self.credentials is not None:
                environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.credentials
        if not hasattr(self, "billing_project_id"):
            bq_client = Client()
        else:
            bq_client = Client(project=self.billing_project_id)
        bq_table = bq_client.get_table(self.full_table_id)
        if not bq_table:
            raise DataContractException(
                type="import",
                result="failed",
                name="BigQuery",
                reason=f"Table '{self.full_table_id}' not found.",
                engine="datacontract",
            )

        if data_contract_specification.models is None:
            data_contract_specification.models = {}

        table_name = self.full_table_id.split(".")[-1]
        fields = self.convert_fields(bq_table.schema)
        data_contract_specification.models[table_name] = Model(
            fields=fields, type=bq_table.table_type, description=bq_table.description or ""
        )
        data_contract_specification.id = self.full_table_id
        data_contract_specification.info.title = f"BigQuery Table {table_name}"

        return data_contract_specification
