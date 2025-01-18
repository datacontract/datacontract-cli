from pyiceberg import types
from pyiceberg.schema import Schema, assign_fresh_schema_ids

from datacontract.export.exporter import Exporter
from datacontract.model.data_contract_specification import (
    DataContractSpecification,
    Field,
    Model,
)


class IcebergExporter(Exporter):
    """
    Exporter class for exporting data contracts to Iceberg schemas.
    """

    def export(
        self,
        data_contract: DataContractSpecification,
        model,
        server,
        sql_server_type,
        export_args,
    ):
        """
        Export the given data contract model to an Iceberg schema.

        Args:
            data_contract (DataContractSpecification): The data contract specification.
            model: The model to export, currently just supports one model.
            server: Not used in this implementation.
            sql_server_type: Not used in this implementation.
            export_args: Additional arguments for export.

        Returns:
            str: A string representation of the Iceberg json schema.
        """

        return to_iceberg(data_contract, model)


def to_iceberg(contract: DataContractSpecification, model: str) -> str:
    """
    Converts a DataContractSpecification into an Iceberg json schema string. JSON string follows https://iceberg.apache.org/spec/#appendix-c-json-serialization.

    Args:
        contract (DataContractSpecification): The data contract specification containing models.
        model: The model to export, currently just supports one model.

    Returns:
        str: A string representation of the Iceberg json schema.
    """
    if model is None or model == "all":
        if len(contract.models.items()) != 1:
            # Iceberg doesn't have a way to combine multiple models into a single schema, an alternative would be to export json lines
            raise Exception(f"Can only output one model at a time, found {len(contract.models.items())} models")
        for model_name, model in contract.models.items():
            schema = to_iceberg_schema(model)
    else:
        if model not in contract.models:
            raise Exception(f"model {model} not found in contract")
        schema = to_iceberg_schema(contract.models[model])

    return schema.model_dump_json()


def to_iceberg_schema(model: Model) -> types.StructType:
    """
    Convert a model to a Iceberg schema.

    Args:
        model (Model): The model to convert.

    Returns:
        types.StructType: The corresponding Iceberg schema.
    """
    iceberg_fields = []
    primary_keys = []
    for field_name, spec_field in model.fields.items():
        iceberg_field = make_field(field_name, spec_field)
        iceberg_fields.append(iceberg_field)

        if spec_field.primaryKey:
            primary_keys.append(iceberg_field.name)

    schema = Schema(*iceberg_fields)

    # apply non-0 field IDs so we can set the identifier fields for the schema
    schema = assign_fresh_schema_ids(schema)
    for field in schema.fields:
        if field.name in primary_keys:
            schema.identifier_field_ids.append(field.field_id)

    return schema


def make_field(field_name, field):
    field_type = get_field_type(field)

    # Note: might want to re-populate field_id from config['icebergFieldId'] if it exists, however, it gets
    # complicated since field_ids impact the list and map element_ids, and the importer is not keeping track of those.
    # Even if IDs are re-constituted, it seems like the SDK code would still reset them before any operation against a catalog,
    # so it's likely not worth it.

    # Note 2: field_id defaults to 0 to signify that the exporter is not attempting to populate meaningful values.
    # also, the Iceberg sdk catalog code will re-set the fieldIDs prior to executing any table operations on the schema
    # ref: https://github.com/apache/iceberg-python/pull/1072
    return types.NestedField(field_id=0, name=field_name, field_type=field_type, required=field.required is True)


def make_list(item):
    field_type = get_field_type(item)

    # element_id defaults to 0 to signify that the exporter is not attempting to populate meaningful values (see #make_field)
    return types.ListType(element_id=0, element_type=field_type, element_required=item.required is True)


def make_map(field):
    key_type = get_field_type(field.keys)
    value_type = get_field_type(field.values)

    # key_id and value_id defaults to 0 to signify that the exporter is not attempting to populate meaningful values (see #make_field)
    return types.MapType(
        key_id=0, key_type=key_type, value_id=0, value_type=value_type, value_required=field.values.required is True
    )


def to_struct_type(fields: dict[str, Field]) -> types.StructType:
    """
    Convert a dictionary of fields to a Iceberg StructType.

    Args:
        fields (dict[str, Field]): The fields to convert.

    Returns:
        types.StructType: The corresponding Iceberg StructType.
    """
    struct_fields = []
    for field_name, field in fields.items():
        struct_field = make_field(field_name, field)
        struct_fields.append(struct_field)
    return types.StructType(*struct_fields)


def get_field_type(field: Field) -> types.IcebergType:
    """
    Convert a field to a Iceberg IcebergType.

    Args:
        field (Field): The field to convert.

    Returns:
        types.IcebergType: The corresponding Iceberg IcebergType.
    """
    field_type = field.type
    if field_type is None or field_type in ["null"]:
        return types.NullType()
    if field_type == "array":
        return make_list(field.items)
    if field_type == "map":
        return make_map(field)
    if field_type in ["object", "record", "struct"]:
        return to_struct_type(field.fields)
    if field_type in ["string", "varchar", "text"]:
        return types.StringType()
    if field_type in ["number", "decimal", "numeric"]:
        precision = field.precision if field.precision is not None else 38
        scale = field.scale if field.scale is not None else 0
        return types.DecimalType(precision=precision, scale=scale)
    if field_type in ["integer", "int"]:
        return types.IntegerType()
    if field_type in ["bigint", "long"]:
        return types.LongType()
    if field_type == "float":
        return types.FloatType()
    if field_type == "double":
        return types.DoubleType()
    if field_type == "boolean":
        return types.BooleanType()
    if field_type in ["timestamp", "timestamp_tz"]:
        return types.TimestamptzType()
    if field_type == "timestamp_ntz":
        return types.TimestampType()
    if field_type == "date":
        return types.DateType()
    if field_type == "bytes":
        return types.BinaryType()
    return types.BinaryType()
