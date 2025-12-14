from typing import List, Optional

from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, SchemaProperty
from pyiceberg import types
from pyiceberg.schema import Schema, assign_fresh_schema_ids

from datacontract.export.exporter import Exporter


class IcebergExporter(Exporter):
    """
    Exporter class for exporting data contracts to Iceberg schemas.
    """

    def export(
        self,
        data_contract: OpenDataContractStandard,
        schema_name,
        server,
        sql_server_type,
        export_args,
    ):
        """
        Export the given data contract to an Iceberg schema.

        Args:
            data_contract (OpenDataContractStandard): The data contract specification.
            schema_name: The name of the schema to export, or 'all' for all schemas.
            server: Not used in this implementation.
            sql_server_type: Not used in this implementation.
            export_args: Additional arguments for export.

        Returns:
            str: A string representation of the Iceberg json schema.
        """

        return to_iceberg(data_contract, schema_name)


def to_iceberg(contract: OpenDataContractStandard, model: str) -> str:
    """
    Converts an OpenDataContractStandard into an Iceberg json schema string. JSON string follows https://iceberg.apache.org/spec/#appendix-c-json-serialization.

    Args:
        contract (OpenDataContractStandard): The data contract specification containing models.
        model: The model to export, currently just supports one model.

    Returns:
        str: A string representation of the Iceberg json schema.
    """
    if not contract.schema_:
        raise Exception("No schema found in contract")

    if model is None or model == "all":
        if len(contract.schema_) != 1:
            # Iceberg doesn't have a way to combine multiple models into a single schema, an alternative would be to export json lines
            raise Exception(f"Can only output one model at a time, found {len(contract.schema_)} models")
        schema_obj = contract.schema_[0]
        schema = to_iceberg_schema(schema_obj)
    else:
        # Find the specific schema by name
        schema_obj = next((s for s in contract.schema_ if s.name == model), None)
        if schema_obj is None:
            raise Exception(f"model {model} not found in contract")
        schema = to_iceberg_schema(schema_obj)

    return schema.model_dump_json()


def to_iceberg_schema(schema_obj: SchemaObject) -> types.StructType:
    """
    Convert a schema object to an Iceberg schema.

    Args:
        schema_obj (SchemaObject): The schema object to convert.

    Returns:
        types.StructType: The corresponding Iceberg schema.
    """
    iceberg_fields = []
    primary_keys = []

    if schema_obj.properties:
        for prop in schema_obj.properties:
            iceberg_field = make_field(prop.name, prop)
            iceberg_fields.append(iceberg_field)

            if prop.primaryKey:
                primary_keys.append(iceberg_field.name)

    schema = Schema(*iceberg_fields)

    # apply non-0 field IDs so we can set the identifier fields for the schema
    schema = assign_fresh_schema_ids(schema)
    for field in schema.fields:
        if field.name in primary_keys:
            schema.identifier_field_ids.append(field.field_id)

    return schema


def _get_type(prop: SchemaProperty) -> Optional[str]:
    """Get the logical type from a schema property."""
    return prop.logicalType


def _get_logical_type_option(prop: SchemaProperty, key: str):
    """Get a logical type option value."""
    if prop.logicalTypeOptions is None:
        return None
    return prop.logicalTypeOptions.get(key)


def _get_custom_property_value(prop: SchemaProperty, key: str):
    """Get a custom property value."""
    if prop.customProperties is None:
        return None
    for cp in prop.customProperties:
        if cp.property == key and cp.value is not None:
            return cp.value
    return None


def make_field(field_name: str, prop: SchemaProperty) -> types.NestedField:
    field_type = get_field_type(prop)

    # Note: might want to re-populate field_id from config['icebergFieldId'] if it exists, however, it gets
    # complicated since field_ids impact the list and map element_ids, and the importer is not keeping track of those.
    # Even if IDs are re-constituted, it seems like the SDK code would still reset them before any operation against a catalog,
    # so it's likely not worth it.

    # Note 2: field_id defaults to 0 to signify that the exporter is not attempting to populate meaningful values.
    # also, the Iceberg sdk catalog code will re-set the fieldIDs prior to executing any table operations on the schema
    # ref: https://github.com/apache/iceberg-python/pull/1072
    return types.NestedField(field_id=0, name=field_name, field_type=field_type, required=prop.required is True)


def make_list(item: SchemaProperty) -> types.ListType:
    field_type = get_field_type(item)

    # element_id defaults to 0 to signify that the exporter is not attempting to populate meaningful values (see #make_field)
    return types.ListType(element_id=0, element_type=field_type, element_required=item.required is True)


def _type_str_to_iceberg_type(type_str: str) -> types.IcebergType:
    """Convert a type string to an Iceberg type."""
    if not type_str:
        return types.StringType()
    t = type_str.lower()
    if t == "string":
        return types.StringType()
    elif t in ["integer", "int"]:
        return types.IntegerType()
    elif t in ["long", "bigint"]:
        return types.LongType()
    elif t == "number":
        return types.DecimalType(precision=38, scale=0)
    elif t in ["float"]:
        return types.FloatType()
    elif t in ["double"]:
        return types.DoubleType()
    elif t == "boolean":
        return types.BooleanType()
    elif t == "date":
        return types.DateType()
    elif t == "timestamp":
        return types.TimestamptzType()
    elif t in ["bytes", "binary"]:
        return types.BinaryType()
    else:
        return types.StringType()


def _get_custom_prop(prop: SchemaProperty, key: str) -> Optional[str]:
    """Get a custom property value from a SchemaProperty."""
    if prop.customProperties is None:
        return None
    for cp in prop.customProperties:
        if cp.property == key:
            return cp.value
    return None


def make_map(prop: SchemaProperty) -> types.MapType:
    # For ODCS, read key/value types from customProperties
    # Default to string -> string if not specified
    key_type = types.StringType()
    value_type = types.StringType()

    key_type_str = _get_custom_prop(prop, "mapKeyType")
    value_type_str = _get_custom_prop(prop, "mapValueType")
    value_physical_type = _get_custom_prop(prop, "mapValuePhysicalType")
    value_required_str = _get_custom_prop(prop, "mapValueRequired")
    value_required = value_required_str == "true" if value_required_str else False

    if key_type_str:
        key_type = _type_str_to_iceberg_type(key_type_str)

    # Handle nested map in value type
    if value_physical_type == "map":
        nested_key_type = _get_custom_prop(prop, "mapNestedKeyType") or "string"
        nested_value_type = _get_custom_prop(prop, "mapNestedValueType") or "string"
        nested_value_required_str = _get_custom_prop(prop, "mapNestedValueRequired")
        nested_value_required = nested_value_required_str == "true" if nested_value_required_str else True
        value_type = types.MapType(
            key_id=0,
            key_type=_type_str_to_iceberg_type(nested_key_type),
            value_id=0,
            value_type=_type_str_to_iceberg_type(nested_value_type),
            value_required=nested_value_required
        )
    elif value_type_str:
        value_type = _type_str_to_iceberg_type(value_type_str)

    # key_id and value_id defaults to 0 to signify that the exporter is not attempting to populate meaningful values (see #make_field)
    return types.MapType(key_id=0, key_type=key_type, value_id=0, value_type=value_type, value_required=value_required)


def to_struct_type(properties: List[SchemaProperty]) -> types.StructType:
    """
    Convert a list of properties to an Iceberg StructType.

    Args:
        properties (List[SchemaProperty]): The properties to convert.

    Returns:
        types.StructType: The corresponding Iceberg StructType.
    """
    struct_fields = []
    for prop in properties:
        struct_field = make_field(prop.name, prop)
        struct_fields.append(struct_field)
    return types.StructType(*struct_fields)


def get_field_type(prop: SchemaProperty) -> types.IcebergType:
    """
    Convert a property to an Iceberg IcebergType.

    Args:
        prop (SchemaProperty): The property to convert.

    Returns:
        types.IcebergType: The corresponding Iceberg IcebergType.
    """
    logical_type = _get_type(prop)
    physical_type = prop.physicalType.lower() if prop.physicalType else None

    # Handle null type
    if logical_type is None and physical_type is None:
        return types.NullType()
    if physical_type == "null":
        return types.NullType()

    # Handle array type
    if logical_type == "array":
        if prop.items:
            return make_list(prop.items)
        return types.ListType(element_id=0, element_type=types.StringType(), element_required=False)

    # Handle map type
    if physical_type == "map":
        return make_map(prop)

    # Handle object/struct type
    if logical_type == "object" or physical_type in ["object", "record", "struct"]:
        if prop.properties:
            return to_struct_type(prop.properties)
        return types.StructType()

    # Check physical type first for specific SQL types
    if physical_type:
        if physical_type in ["string", "varchar", "text", "char", "nvarchar"]:
            return types.StringType()
        if physical_type in ["decimal", "numeric"]:
            precision = _get_custom_property_value(prop, "precision") or 38
            scale = _get_custom_property_value(prop, "scale") or 0
            return types.DecimalType(precision=precision, scale=scale)
        if physical_type in ["integer", "int", "int32"]:
            return types.IntegerType()
        if physical_type in ["bigint", "long", "int64"]:
            return types.LongType()
        if physical_type in ["float", "real", "float32"]:
            return types.FloatType()
        if physical_type in ["double", "float64"]:
            return types.DoubleType()
        if physical_type in ["boolean", "bool"]:
            return types.BooleanType()
        if physical_type in ["timestamp", "timestamp_tz"]:
            return types.TimestamptzType()
        if physical_type == "timestamp_ntz":
            return types.TimestampType()
        if physical_type == "date":
            return types.DateType()
        if physical_type in ["bytes", "binary", "bytea"]:
            return types.BinaryType()

    # Fall back to logical type
    match logical_type:
        case "string":
            return types.StringType()
        case "number":
            precision = _get_custom_property_value(prop, "precision") or 38
            scale = _get_custom_property_value(prop, "scale") or 0
            return types.DecimalType(precision=precision, scale=scale)
        case "integer":
            return types.LongType()
        case "boolean":
            return types.BooleanType()
        case "timestamp":
            return types.TimestamptzType()
        case "date":
            return types.DateType()
        case _:
            return types.BinaryType()
