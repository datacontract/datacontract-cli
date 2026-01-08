from typing import Any, Dict

from pydantic import ValidationError
from pyiceberg import types as iceberg_types
from pyiceberg.schema import Schema

from datacontract.imports.importer import Importer
from datacontract.model.data_contract_specification import DataContractSpecification, Field, Model
from datacontract.model.exceptions import DataContractException


class IcebergImporter(Importer):
    def import_source(
        self, data_contract_specification: DataContractSpecification, source: str, import_args: dict
    ) -> DataContractSpecification:
        schema = load_and_validate_iceberg_schema(source)
        return import_iceberg(
            data_contract_specification,
            schema,
            import_args.get("iceberg_table"),
        )


def load_and_validate_iceberg_schema(source: str) -> Schema:
    with open(source, "r") as file:
        try:
            return Schema.model_validate_json(file.read())
        except ValidationError as e:
            raise DataContractException(
                type="schema",
                name="Parse iceberg schema",
                reason=f"Failed to validate iceberg schema from {source}: {e}",
                engine="datacontract",
            )


def import_iceberg(
    data_contract_specification: DataContractSpecification, schema: Schema, table_name: str
) -> DataContractSpecification:
    if data_contract_specification.models is None:
        data_contract_specification.models = {}

    model = Model(type="table", title=table_name)

    # Iceberg identifier_fields aren't technically primary keys since Iceberg doesn't support primary keys,
    # but they are close enough that we can probably treat them as primary keys on the conversion.
    # ref: https://iceberg.apache.org/spec/#identifier-field-ids
    # this code WILL NOT support finding nested primary key fields.
    identifier_fields_ids = schema.identifier_field_ids

    for field in schema.fields:
        model_field = _field_from_nested_field(field)

        if field.field_id in identifier_fields_ids:
            model_field.primaryKey = True

        model.fields[field.name] = model_field

    data_contract_specification.models[table_name] = model
    return data_contract_specification


def _field_from_nested_field(nested_field: iceberg_types.NestedField) -> Field:
    """
    Converts an Iceberg NestedField into a Field object for the data contract.

    Args:
        nested_field: The Iceberg NestedField to convert.

    Returns:
        Field: The generated Field object.
    """
    field = Field(
        title=nested_field.name,
        required=nested_field.required,
        config=build_field_config(nested_field),
    )

    if nested_field.doc is not None:
        field.description = nested_field.doc

    return _type_from_iceberg_type(field, nested_field.field_type)


def _type_from_iceberg_type(field: Field, iceberg_type: iceberg_types.IcebergType) -> Field:
    """
    Maps Iceberg data types to the Data Contract type system and updates the field.

    Args:
        field: The Field object to update.
        iceberg_type: The Iceberg data type to map.

    Returns:
        Field: The updated Field object.
    """
    field.type = _data_type_from_iceberg(iceberg_type)

    if field.type == "array":
        field.items = _type_from_iceberg_type(Field(required=iceberg_type.element_required), iceberg_type.element_type)

    elif field.type == "map":
        field.keys = _type_from_iceberg_type(Field(required=True), iceberg_type.key_type)
        field.values = _type_from_iceberg_type(Field(required=iceberg_type.value_required), iceberg_type.value_type)

    elif field.type == "object":
        field.fields = {nf.name: _field_from_nested_field(nf) for nf in iceberg_type.fields}

    return field


def build_field_config(iceberg_field: iceberg_types.NestedField) -> Dict[str, Any]:
    config = {}

    if iceberg_field.field_id > 0:
        config["icebergFieldId"] = iceberg_field.field_id

    if iceberg_field.initial_default is not None:
        config["icebergInitialDefault"] = iceberg_field.initial_default

    if iceberg_field.write_default is not None:
        config["icebergWriteDefault"] = iceberg_field.write_default

    return config


def _data_type_from_iceberg(type: iceberg_types.IcebergType) -> str:
    """
    Convert an Iceberg field type to a datacontract field type

    Args:
        type: The Iceberg field type

    Returns:
        str: The datacontract field type
    """
    if isinstance(type, iceberg_types.BooleanType):
        return "boolean"
    if isinstance(type, iceberg_types.IntegerType):
        return "integer"
    if isinstance(type, iceberg_types.LongType):
        return "long"
    if isinstance(type, iceberg_types.FloatType):
        return "float"
    if isinstance(type, iceberg_types.DoubleType):
        return "double"
    if isinstance(type, iceberg_types.DecimalType):
        return "decimal"
    if isinstance(type, iceberg_types.DateType):
        return "date"
    if isinstance(type, iceberg_types.TimeType):
        # there isn't a great mapping for the iceberg type "time", just map to string for now
        return "string"
    if isinstance(type, iceberg_types.TimestampType):
        return "timestamp_ntz"
    if isinstance(type, iceberg_types.TimestamptzType):
        return "timestamp_tz"
    if isinstance(type, iceberg_types.StringType):
        return "string"
    if isinstance(type, iceberg_types.UUIDType):
        return "string"
    if isinstance(type, iceberg_types.BinaryType):
        return "bytes"
    if isinstance(type, iceberg_types.FixedType):
        return "bytes"
    if isinstance(type, iceberg_types.MapType):
        return "map"
    if isinstance(type, iceberg_types.ListType):
        return "array"
    if isinstance(type, iceberg_types.StructType):
        return "object"

    raise ValueError(f"Unknown Iceberg type: {type}")
