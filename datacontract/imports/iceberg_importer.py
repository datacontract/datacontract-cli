
from open_data_contract_standard.model import OpenDataContractStandard, SchemaProperty
from pydantic import ValidationError
from pyiceberg import types as iceberg_types
from pyiceberg.schema import Schema

from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import (
    create_odcs,
    create_property,
    create_schema_object,
)
from datacontract.model.exceptions import DataContractException


class IcebergImporter(Importer):
    def import_source(
        self, source: str, import_args: dict
    ) -> OpenDataContractStandard:
        schema = load_and_validate_iceberg_schema(source)
        return import_iceberg(
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


def import_iceberg(schema: Schema, table_name: str) -> OpenDataContractStandard:
    """Import an Iceberg schema and create an ODCS data contract."""
    odcs = create_odcs()

    # Iceberg identifier_fields aren't technically primary keys since Iceberg doesn't support primary keys,
    # but they are close enough that we can treat them as primary keys on the conversion.
    identifier_fields_ids = schema.identifier_field_ids

    properties = []
    pk_position = 1

    for field in schema.fields:
        prop = _property_from_nested_field(field)

        if field.field_id in identifier_fields_ids:
            prop.primaryKey = True
            prop.primaryKeyPosition = pk_position
            pk_position += 1

        properties.append(prop)

    schema_obj = create_schema_object(
        name=table_name or "iceberg_table",
        physical_type="table",
        properties=properties,
    )

    odcs.schema_ = [schema_obj]
    return odcs


def _property_from_nested_field(nested_field: iceberg_types.NestedField) -> SchemaProperty:
    """Converts an Iceberg NestedField into an ODCS SchemaProperty."""
    logical_type = _data_type_from_iceberg(nested_field.field_type)

    custom_props = {}
    if nested_field.field_id > 0:
        custom_props["icebergFieldId"] = nested_field.field_id
    if nested_field.initial_default is not None:
        custom_props["icebergInitialDefault"] = str(nested_field.initial_default)
    if nested_field.write_default is not None:
        custom_props["icebergWriteDefault"] = str(nested_field.write_default)

    nested_properties = None
    items_prop = None
    physical_type = str(nested_field.field_type)

    if logical_type == "array":
        items_prop = _type_to_property("items", nested_field.field_type.element_type, nested_field.field_type.element_required)
    elif isinstance(nested_field.field_type, iceberg_types.MapType):
        # For map types, store key/value types in customProperties and use "map" as physicalType
        physical_type = "map"
        custom_props["mapKeyType"] = _data_type_from_iceberg(nested_field.field_type.key_type)
        custom_props["mapValueType"] = _data_type_from_iceberg(nested_field.field_type.value_type)
        custom_props["mapValueRequired"] = str(nested_field.field_type.value_required).lower()
        # Handle nested maps in value type
        if isinstance(nested_field.field_type.value_type, iceberg_types.MapType):
            custom_props["mapValuePhysicalType"] = "map"
            custom_props["mapNestedKeyType"] = _data_type_from_iceberg(nested_field.field_type.value_type.key_type)
            custom_props["mapNestedValueType"] = _data_type_from_iceberg(nested_field.field_type.value_type.value_type)
            custom_props["mapNestedValueRequired"] = str(nested_field.field_type.value_type.value_required).lower()
    elif logical_type == "object" and hasattr(nested_field.field_type, "fields"):
        nested_properties = [_property_from_nested_field(nf) for nf in nested_field.field_type.fields]

    return create_property(
        name=nested_field.name,
        logical_type=logical_type,
        physical_type=physical_type,
        description=nested_field.doc,
        required=nested_field.required if nested_field.required else None,
        properties=nested_properties,
        items=items_prop,
        custom_properties=custom_props if custom_props else None,
    )


def _type_to_property(name: str, iceberg_type: iceberg_types.IcebergType, required: bool = True) -> SchemaProperty:
    """Convert an Iceberg type to an ODCS SchemaProperty."""
    logical_type = _data_type_from_iceberg(iceberg_type)

    nested_properties = None
    items_prop = None

    if logical_type == "array":
        items_prop = _type_to_property("items", iceberg_type.element_type, iceberg_type.element_required)
    elif logical_type == "object" and hasattr(iceberg_type, "fields"):
        nested_properties = [_property_from_nested_field(nf) for nf in iceberg_type.fields]

    return create_property(
        name=name,
        logical_type=logical_type,
        physical_type=str(iceberg_type),
        required=required if required else None,
        properties=nested_properties,
        items=items_prop,
    )


def _data_type_from_iceberg(iceberg_type: iceberg_types.IcebergType) -> str:
    """Convert an Iceberg field type to an ODCS logical type."""
    if isinstance(iceberg_type, iceberg_types.BooleanType):
        return "boolean"
    if isinstance(iceberg_type, iceberg_types.IntegerType):
        return "integer"
    if isinstance(iceberg_type, iceberg_types.LongType):
        return "integer"
    if isinstance(iceberg_type, iceberg_types.FloatType):
        return "number"
    if isinstance(iceberg_type, iceberg_types.DoubleType):
        return "number"
    if isinstance(iceberg_type, iceberg_types.DecimalType):
        return "number"
    if isinstance(iceberg_type, iceberg_types.DateType):
        return "date"
    if isinstance(iceberg_type, iceberg_types.TimeType):
        return "string"
    if isinstance(iceberg_type, iceberg_types.TimestampType):
        return "date"
    if isinstance(iceberg_type, iceberg_types.TimestamptzType):
        return "date"
    if isinstance(iceberg_type, iceberg_types.StringType):
        return "string"
    if isinstance(iceberg_type, iceberg_types.UUIDType):
        return "string"
    if isinstance(iceberg_type, iceberg_types.BinaryType):
        return "array"
    if isinstance(iceberg_type, iceberg_types.FixedType):
        return "array"
    if isinstance(iceberg_type, iceberg_types.MapType):
        return "object"
    if isinstance(iceberg_type, iceberg_types.ListType):
        return "array"
    if isinstance(iceberg_type, iceberg_types.StructType):
        return "object"

    raise ValueError(f"Unknown Iceberg type: {iceberg_type}")
