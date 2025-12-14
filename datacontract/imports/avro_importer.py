from typing import List

import avro.schema
from open_data_contract_standard.model import OpenDataContractStandard, SchemaProperty

from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import (
    create_odcs,
    create_property,
    create_schema_object,
)
from datacontract.model.exceptions import DataContractException

# Avro logical type to ODCS logical type mapping
LOGICAL_TYPE_MAPPING = {
    "decimal": "number",
    "date": "date",
    "time-millis": "string",
    "time-micros": "string",
    "timestamp-millis": "date",
    "timestamp-micros": "date",
    "local-timestamp-millis": "date",
    "local-timestamp-micros": "date",
    "duration": "string",
    "uuid": "string",
}


class AvroImporter(Importer):
    """Class to import Avro Schema file"""

    def import_source(
        self, source: str, import_args: dict
    ) -> OpenDataContractStandard:
        return import_avro(source)


def import_avro(source: str) -> OpenDataContractStandard:
    """Import an Avro schema from a file."""
    try:
        with open(source, "r") as file:
            avro_schema = avro.schema.parse(file.read())
    except Exception as e:
        raise DataContractException(
            type="schema",
            name="Parse avro schema",
            reason=f"Failed to parse avro schema from {source}",
            engine="datacontract",
            original_exception=e,
        )

    odcs = create_odcs()
    odcs.schema_ = []

    properties = import_record_fields(avro_schema.fields)

    schema_obj = create_schema_object(
        name=avro_schema.name,
        physical_type="record",
        description=avro_schema.get_prop("doc"),
        properties=properties,
    )

    # Add namespace as custom property if present
    if avro_schema.get_prop("namespace") is not None:
        from open_data_contract_standard.model import CustomProperty
        schema_obj.customProperties = [
            CustomProperty(property="namespace", value=avro_schema.get_prop("namespace"))
        ]

    odcs.schema_.append(schema_obj)

    return odcs


def import_record_fields(record_fields: List[avro.schema.Field]) -> List[SchemaProperty]:
    """Import Avro record fields and convert them to ODCS properties."""
    properties = []

    for field in record_fields:
        prop = import_avro_field(field)
        if prop:
            properties.append(prop)

    return properties


def import_avro_field(field: avro.schema.Field) -> SchemaProperty:
    """Import a single Avro field as an ODCS SchemaProperty."""
    custom_props = {}

    # Handle Avro custom properties
    if field.get_prop("logicalType") is not None:
        custom_props["avroLogicalType"] = field.get_prop("logicalType")
    if field.default is not None:
        custom_props["avroDefault"] = str(field.default)

    # Determine type and nested structures
    if field.type.type == "record":
        nested_properties = import_record_fields(field.type.fields)
        prop = create_property(
            name=field.name,
            logical_type="object",
            physical_type="record",
            description=field.type.doc or field.doc,
            required=True,
            properties=nested_properties,
            custom_properties=custom_props if custom_props else None,
        )
    elif field.type.type == "union":
        # Union types indicate optional fields (null + type)
        enum_schema = get_enum_from_union_field(field)
        if enum_schema:
            prop = create_property(
                name=field.name,
                logical_type="string",
                physical_type="enum",
                description=field.doc,
                required=False,
                custom_properties={**custom_props, "avroType": "enum"} if custom_props else {"avroType": "enum"},
            )
        else:
            logical_type, physical_type = import_type_of_optional_field(field)
            if logical_type == "object":
                record_schema = get_record_from_union_field(field)
                nested_properties = import_record_fields(record_schema.fields) if record_schema else []
                prop = create_property(
                    name=field.name,
                    logical_type="object",
                    physical_type="record",
                    description=field.doc,
                    required=False,
                    properties=nested_properties,
                    custom_properties=custom_props if custom_props else None,
                )
            elif logical_type == "array":
                array_schema = get_array_from_union_field(field)
                items_prop = import_avro_array_items(array_schema) if array_schema else None
                prop = create_property(
                    name=field.name,
                    logical_type="array",
                    physical_type="array",
                    description=field.doc,
                    required=False,
                    items=items_prop,
                    custom_properties=custom_props if custom_props else None,
                )
            else:
                prop = create_property(
                    name=field.name,
                    logical_type=logical_type,
                    physical_type=physical_type,
                    description=field.doc,
                    required=False,
                    custom_properties=custom_props if custom_props else None,
                )
    elif field.type.type == "array":
        items_prop = import_avro_array_items(field.type)
        prop = create_property(
            name=field.name,
            logical_type="array",
            physical_type="array",
            description=field.doc,
            required=True,
            items=items_prop,
            custom_properties=custom_props if custom_props else None,
        )
    elif field.type.type == "map":
        prop = create_property(
            name=field.name,
            logical_type="object",
            physical_type="map",
            description=field.doc,
            required=True,
            custom_properties={**custom_props, "avroType": "map"} if custom_props else {"avroType": "map"},
        )
    elif field.type.type == "enum":
        prop = create_property(
            name=field.name,
            logical_type="string",
            physical_type="enum",
            description=field.doc,
            required=True,
            custom_properties={**custom_props, "avroType": "enum", "avroSymbols": field.type.symbols} if custom_props else {"avroType": "enum", "avroSymbols": field.type.symbols},
        )
    else:
        # Primitive types
        avro_logical_type = field.type.get_prop("logicalType")
        if avro_logical_type in LOGICAL_TYPE_MAPPING:
            logical_type = LOGICAL_TYPE_MAPPING[avro_logical_type]
            precision = getattr(field.type, 'precision', None)
            scale = getattr(field.type, 'scale', None)
            prop = create_property(
                name=field.name,
                logical_type=logical_type,
                physical_type=field.type.type,
                description=field.doc,
                required=True,
                precision=precision,
                scale=scale,
                custom_properties=custom_props if custom_props else None,
            )
        else:
            logical_type = map_type_from_avro(field.type.type)
            prop = create_property(
                name=field.name,
                logical_type=logical_type,
                physical_type=field.type.type,
                description=field.doc,
                required=True,
                custom_properties=custom_props if custom_props else None,
            )

    return prop


def import_avro_array_items(array_schema: avro.schema.ArraySchema) -> SchemaProperty:
    """Import Avro array items as an ODCS SchemaProperty."""
    if array_schema.items.type == "record":
        nested_properties = import_record_fields(array_schema.items.fields)
        return create_property(
            name="items",
            logical_type="object",
            physical_type="record",
            properties=nested_properties,
        )
    elif array_schema.items.type == "array":
        items_prop = import_avro_array_items(array_schema.items)
        return create_property(
            name="items",
            logical_type="array",
            physical_type="array",
            items=items_prop,
        )
    else:
        logical_type = map_type_from_avro(array_schema.items.type)
        return create_property(
            name="items",
            logical_type=logical_type,
            physical_type=array_schema.items.type,
        )


def import_avro_map_values(map_schema: avro.schema.MapSchema) -> SchemaProperty:
    """Import Avro map values as an ODCS SchemaProperty."""
    if map_schema.values.type == "record":
        nested_properties = import_record_fields(map_schema.values.fields)
        return create_property(
            name="values",
            logical_type="object",
            physical_type="record",
            properties=nested_properties,
        )
    elif map_schema.values.type == "array":
        items_prop = import_avro_array_items(map_schema.values)
        return create_property(
            name="values",
            logical_type="array",
            physical_type="array",
            items=items_prop,
        )
    else:
        logical_type = map_type_from_avro(map_schema.values.type)
        return create_property(
            name="values",
            logical_type=logical_type,
            physical_type=map_schema.values.type,
        )


def import_type_of_optional_field(field: avro.schema.Field) -> tuple[str, str]:
    """Determine the type of optional field in an Avro union."""
    for field_type in field.type.schemas:
        if field_type.type != "null":
            avro_logical_type = field_type.get_prop("logicalType")
            if avro_logical_type and avro_logical_type in LOGICAL_TYPE_MAPPING:
                return LOGICAL_TYPE_MAPPING[avro_logical_type], field_type.type
            else:
                return map_type_from_avro(field_type.type), field_type.type

    raise DataContractException(
        type="schema",
        result="failed",
        name="Map avro type to data contract type",
        reason="Could not import optional field: union type does not contain a non-null type",
        engine="datacontract",
    )


def get_record_from_union_field(field: avro.schema.Field) -> avro.schema.RecordSchema | None:
    """Get the record schema from a union field."""
    for field_type in field.type.schemas:
        if field_type.type == "record":
            return field_type
    return None


def get_array_from_union_field(field: avro.schema.Field) -> avro.schema.ArraySchema | None:
    """Get the array schema from a union field."""
    for field_type in field.type.schemas:
        if field_type.type == "array":
            return field_type
    return None


def get_enum_from_union_field(field: avro.schema.Field) -> avro.schema.EnumSchema | None:
    """Get the enum schema from a union field."""
    for field_type in field.type.schemas:
        if field_type.type == "enum":
            return field_type
    return None


def map_type_from_avro(avro_type_str: str) -> str:
    """Map Avro type strings to ODCS logical type strings."""
    type_mapping = {
        "null": "string",  # null type maps to string as placeholder
        "string": "string",
        "bytes": "array",
        "double": "number",
        "float": "number",
        "int": "integer",
        "long": "integer",
        "boolean": "boolean",
        "record": "object",
        "array": "array",
        "map": "object",
        "enum": "string",
        "fixed": "array",
    }

    if avro_type_str in type_mapping:
        return type_mapping[avro_type_str]

    raise DataContractException(
        type="schema",
        result="failed",
        name="Map avro type to data contract type",
        reason=f"Unsupported type {avro_type_str} in avro schema.",
        engine="datacontract",
    )
