import os.path

import pyarrow
from open_data_contract_standard.model import OpenDataContractStandard
from pyarrow import parquet

from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import (
    create_odcs,
    create_property,
    create_schema_object,
)
from datacontract.model.exceptions import DataContractException


class ParquetImporter(Importer):
    def import_source(
        self, source: str, import_args: dict
    ) -> OpenDataContractStandard:
        return import_parquet(source)


def import_parquet(source: str) -> OpenDataContractStandard:
    """Import a Parquet file and create an ODCS data contract."""
    # use filename as schema name, remove .parquet suffix, avoid breaking the yaml output by replacing dots
    schema_name = os.path.basename(source).removesuffix(".parquet").replace(".", "_")

    properties = []

    arrow_schema = parquet.read_schema(source)
    for field_name in arrow_schema.names:
        parquet_field = arrow_schema.field(field_name)

        prop = map_pyarrow_field_to_property(parquet_field, field_name)

        if not parquet_field.nullable:
            prop.required = True

        properties.append(prop)

    odcs = create_odcs()
    schema_obj = create_schema_object(
        name=schema_name,
        physical_type="parquet",
        properties=properties,
    )
    odcs.schema_ = [schema_obj]

    return odcs


def map_pyarrow_field_to_property(pyarrow_field: pyarrow.Field, field_name: str):
    """Map a PyArrow field to an ODCS SchemaProperty."""
    if pyarrow.types.is_boolean(pyarrow_field.type):
        return create_property(name=field_name, logical_type="boolean", physical_type="BOOLEAN")
    if pyarrow.types.is_int32(pyarrow_field.type):
        return create_property(name=field_name, logical_type="integer", physical_type="INT32")
    if pyarrow.types.is_int64(pyarrow_field.type):
        return create_property(name=field_name, logical_type="integer", physical_type="INT64")
    if pyarrow.types.is_integer(pyarrow_field.type):
        return create_property(name=field_name, logical_type="integer", physical_type=str(pyarrow_field.type))
    if pyarrow.types.is_float32(pyarrow_field.type):
        return create_property(name=field_name, logical_type="number", physical_type="FLOAT")
    if pyarrow.types.is_float64(pyarrow_field.type):
        return create_property(name=field_name, logical_type="number", physical_type="DOUBLE")
    if pyarrow.types.is_decimal(pyarrow_field.type):
        return create_property(
            name=field_name,
            logical_type="number",
            physical_type="DECIMAL",
            precision=pyarrow_field.type.precision,
            scale=pyarrow_field.type.scale,
        )
    if pyarrow.types.is_timestamp(pyarrow_field.type):
        return create_property(name=field_name, logical_type="timestamp", physical_type="TIMESTAMP")
    if pyarrow.types.is_date(pyarrow_field.type):
        return create_property(name=field_name, logical_type="date", physical_type="DATE")
    if pyarrow.types.is_null(pyarrow_field.type):
        return create_property(name=field_name, logical_type="string", physical_type="NULL")
    if pyarrow.types.is_binary(pyarrow_field.type):
        return create_property(name=field_name, logical_type="array", physical_type="BINARY")
    if pyarrow.types.is_string(pyarrow_field.type):
        return create_property(name=field_name, logical_type="string", physical_type="STRING")
    if pyarrow.types.is_map(pyarrow_field.type) or pyarrow.types.is_dictionary(pyarrow_field.type):
        return create_property(name=field_name, logical_type="object", physical_type="MAP")
    if pyarrow.types.is_struct(pyarrow_field.type):
        return create_property(name=field_name, logical_type="object", physical_type="STRUCT")
    if pyarrow.types.is_list(pyarrow_field.type):
        return create_property(name=field_name, logical_type="array", physical_type="LIST")

    raise DataContractException(
        type="schema",
        name="Parse parquet schema",
        reason=f"{pyarrow_field.type} currently not supported.",
        engine="datacontract",
    )
