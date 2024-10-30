import os.path

from pyarrow import parquet

from datacontract.imports.importer import Importer
from datacontract.model.data_contract_specification import (
    DataContractSpecification,
    Model,
    Field,
)


class ParquetImporter(Importer):
    def import_source(
        self, data_contract_specification: DataContractSpecification, source: str, import_args: dict
    ) -> DataContractSpecification:
        return import_parquet(data_contract_specification, source)


def import_parquet(data_contract_specification: DataContractSpecification, source: str) -> DataContractSpecification:
    # use filename as schema name, remove .parquet suffix, avoid breaking the yaml output by replacing dots
    schema_name = os.path.basename(source).removesuffix(".parquet").replace(".", "_")

    fields: dict[str, Field] = {}

    parquet_schema = parquet.read_schema(source)
    for field_name in parquet_schema.names:
        parquet_field = parquet_schema.field(field_name)

        field = Field(type=str(parquet_field.type))

        if not parquet_field.nullable:
            field.required = True

        fields[field_name] = field

    data_contract_specification.models[schema_name] = Model(fields=fields)

    return data_contract_specification
