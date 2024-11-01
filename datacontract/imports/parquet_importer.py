import os.path

import pyarrow
from pyarrow import parquet

from datacontract.imports.importer import Importer
from datacontract.model.data_contract_specification import (
    DataContractSpecification,
    Field,
    Model,
)
from datacontract.model.exceptions import DataContractException


class ParquetImporter(Importer):
    def import_source(
        self, data_contract_specification: DataContractSpecification, source: str, import_args: dict
    ) -> DataContractSpecification:
        return import_parquet(data_contract_specification, source)


def import_parquet(data_contract_specification: DataContractSpecification, source: str) -> DataContractSpecification:
    # use filename as schema name, remove .parquet suffix, avoid breaking the yaml output by replacing dots
    schema_name = os.path.basename(source).removesuffix(".parquet").replace(".", "_")

    fields: dict[str, Field] = {}

    arrow_schema = parquet.read_schema(source)
    for field_name in arrow_schema.names:
        parquet_field = arrow_schema.field(field_name)

        field = map_pyarrow_field_to_specification_field(parquet_field, "parquet")

        if not parquet_field.nullable:
            field.required = True

        fields[field_name] = field

    data_contract_specification.models[schema_name] = Model(fields=fields)

    return data_contract_specification


def map_pyarrow_field_to_specification_field(pyarrow_field: pyarrow.Field, file_format: str) -> Field:
    if pyarrow.types.is_boolean(pyarrow_field.type):
        return Field(type="boolean")
    if pyarrow.types.is_int32(pyarrow_field.type):
        return Field(type="int")
    if pyarrow.types.is_int64(pyarrow_field.type):
        return Field(type="long")
    if pyarrow.types.is_integer(pyarrow_field.type):
        return Field(type="number")
    if pyarrow.types.is_float32(pyarrow_field.type):
        return Field(type="float")
    if pyarrow.types.is_float64(pyarrow_field.type):
        return Field(type="double")
    if pyarrow.types.is_decimal(pyarrow_field.type):
        return Field(type="decimal", precision=pyarrow_field.type.precision, scale=pyarrow_field.type.scale)
    if pyarrow.types.is_timestamp(pyarrow_field.type):
        return Field(type="timestamp")
    if pyarrow.types.is_date(pyarrow_field.type):
        return Field(type="date")
    if pyarrow.types.is_null(pyarrow_field.type):
        return Field(type="null")
    if pyarrow.types.is_binary(pyarrow_field.type):
        return Field(type="bytes")
    if pyarrow.types.is_string(pyarrow_field.type):
        return Field(type="string")
    if pyarrow.types.is_map(pyarrow_field.type) or pyarrow.types.is_dictionary(pyarrow_field.type):
        return Field(type="map")
    if pyarrow.types.is_struct(pyarrow_field.type):
        return Field(type="struct")
    if pyarrow.types.is_list(pyarrow_field.type):
        return Field(type="array")

    raise DataContractException(
        type="schema",
        name=f"Parse {file_format} schema",
        reason=f"{pyarrow_field.type} currently not supported.",
        engine="datacontract",
    )
