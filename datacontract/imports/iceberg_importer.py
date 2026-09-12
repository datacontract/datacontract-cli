from open_data_contract_standard.model import OpenDataContractStandard, SchemaProperty
from pydantic import ValidationError
from pyiceberg import types as iceberg_types
from pyiceberg.schema import Schema

from datacontract.config import Config
from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import (
    create_odcs,
    create_property,
    create_schema_object,
    create_server,
)
from datacontract.model.exceptions import DataContractException


class IcebergImporter(Importer):
    def import_source(self, source: str, import_args: dict, config: "Config | None" = None) -> OpenDataContractStandard:
        config = Config.resolve(config)
        catalog_url = import_args.get("iceberg_catalog_url") or config.get_iceberg_catalog_url()
        if source is None and catalog_url:
            return import_from_catalog(import_args, config, catalog_url)
        if source is None:
            raise DataContractException(
                type="schema",
                name="Import iceberg",
                reason="Pass --source with a schema JSON file, or --catalog-url and --table to read from a REST catalog.",
                engine="datacontract-cli",
            )
        schema = load_and_validate_iceberg_schema(source)
        return import_iceberg(
            schema,
            import_args.get("iceberg_table"),
        )


def import_from_catalog(import_args: dict, config: "Config", catalog_url: str) -> OpenDataContractStandard:
    """Import a table's schema from a REST catalog and describe the catalog as the contract's server."""
    from datacontract.engines.ibis.connections.iceberg import load_iceberg_catalog, load_iceberg_table

    table_name = import_args.get("iceberg_table")
    if not table_name:
        raise DataContractException(
            type="schema",
            name="Import iceberg",
            reason="--table is required when importing from a catalog.",
            engine="datacontract-cli",
        )
    server = create_server(
        name="production",
        server_type="iceberg",
        catalog=import_args.get("iceberg_catalog") or config.get_iceberg_catalog() or "default",
        warehouse=import_args.get("iceberg_warehouse") or config.get_iceberg_warehouse(),
    )
    server.catalogUrl = catalog_url
    server.namespace = import_args.get("iceberg_namespace") or config.get_iceberg_namespace()
    catalog = load_iceberg_catalog(server, config)
    table = load_iceberg_table(catalog, server, table_name, config)
    odcs = import_iceberg(table.schema(), table_name.split(".")[-1])
    # Preserve an explicitly qualified identifier, even when --namespace was
    # omitted or names a different default namespace.
    odcs.schema_[0].physicalName = table_name
    odcs.servers = [server]
    return odcs


def load_and_validate_iceberg_schema(source: str) -> Schema:
    with open(source, "r") as file:
        try:
            return Schema.model_validate_json(file.read())
        except ValidationError as e:
            raise DataContractException(
                type="schema",
                name="Parse iceberg schema",
                reason=f"Failed to validate iceberg schema from {source}: {e}",
                engine="datacontract-cli",
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
    map_key = map_value = None
    physical_type = str(nested_field.field_type)

    if logical_type == "array":
        items_prop = _type_to_property(
            "items", nested_field.field_type.element_type, nested_field.field_type.element_required
        )
    elif logical_type == "map":
        map_key, map_value = _map_key_value(nested_field.field_type)
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
        map_key=map_key,
        map_value=map_value,
        custom_properties=custom_props if custom_props else None,
    )


def _map_key_value(map_type: iceberg_types.MapType) -> tuple[SchemaProperty, SchemaProperty]:
    """The key and value properties of an Iceberg map; Iceberg keys are always required."""
    return (
        _type_to_property("key", map_type.key_type, True),
        _type_to_property("value", map_type.value_type, map_type.value_required),
    )


def _type_to_property(name: str, iceberg_type: iceberg_types.IcebergType, required: bool = True) -> SchemaProperty:
    """Convert an Iceberg type to an ODCS SchemaProperty."""
    logical_type = _data_type_from_iceberg(iceberg_type)

    nested_properties = None
    items_prop = None
    map_key = map_value = None

    if logical_type == "array":
        items_prop = _type_to_property("items", iceberg_type.element_type, iceberg_type.element_required)
    elif logical_type == "map":
        map_key, map_value = _map_key_value(iceberg_type)
    elif logical_type == "object" and hasattr(iceberg_type, "fields"):
        nested_properties = [_property_from_nested_field(nf) for nf in iceberg_type.fields]

    return create_property(
        name=name,
        logical_type=logical_type,
        physical_type=str(iceberg_type),
        required=required if required else None,
        properties=nested_properties,
        items=items_prop,
        map_key=map_key,
        map_value=map_value,
    )


def _data_type_from_iceberg(iceberg_type: iceberg_types.IcebergType) -> str | None:
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
        return "time"
    if isinstance(iceberg_type, iceberg_types.TimestampType):
        return "timestamp"
    if isinstance(iceberg_type, iceberg_types.TimestamptzType):
        return "timestamp"
    if isinstance(iceberg_type, iceberg_types.StringType):
        return "string"
    if isinstance(iceberg_type, iceberg_types.UUIDType):
        return "string"
    if isinstance(iceberg_type, (iceberg_types.BinaryType, iceberg_types.FixedType)):
        # ODCS has no binary logical type. Keep physicalType without pretending
        # that bytes are text or a list with an Iceberg element type.
        return None
    if isinstance(iceberg_type, iceberg_types.MapType):
        return "map"
    if isinstance(iceberg_type, iceberg_types.ListType):
        return "array"
    if isinstance(iceberg_type, iceberg_types.StructType):
        return "object"

    raise ValueError(f"Unknown Iceberg type: {iceberg_type}")
