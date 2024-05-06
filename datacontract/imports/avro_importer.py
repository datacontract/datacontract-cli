import avro.schema

from datacontract.model.data_contract_specification import DataContractSpecification, Model, Field
from datacontract.model.exceptions import DataContractException


def import_avro(data_contract_specification: DataContractSpecification, source: str) -> DataContractSpecification:
    if data_contract_specification.models is None:
        data_contract_specification.models = {}

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

    # type record is being used for both the table and the object types in data contract
    # -> CONSTRAINT: one table per .avsc input, all nested records are interpreted as objects
    fields = import_record_fields(avro_schema.fields)

    data_contract_specification.models[avro_schema.name] = Model(
        fields=fields,
    )

    if avro_schema.get_prop("doc") is not None:
        data_contract_specification.models[avro_schema.name].description = avro_schema.get_prop("doc")

    if avro_schema.get_prop("namespace") is not None:
        data_contract_specification.models[avro_schema.name].namespace = avro_schema.get_prop("namespace")

    return data_contract_specification


def import_record_fields(record_fields):
    imported_fields = {}
    for field in record_fields:
        imported_fields[field.name] = Field()
        imported_fields[field.name].required = True
        imported_fields[field.name].description = field.doc
        for prop in field.other_props:
            imported_fields[field.name].__setattr__(prop, field.other_props[prop])

        if field.type.type == "record":
            imported_fields[field.name].type = "object"
            imported_fields[field.name].description = field.type.doc
            imported_fields[field.name].fields = import_record_fields(field.type.fields)
        elif field.type.type == "union":
            imported_fields[field.name].required = False
            type = import_type_of_optional_field(field)
            imported_fields[field.name].type = type
            if type == "record":
                imported_fields[field.name].fields = import_record_fields(get_record_from_union_field(field).fields)
        elif field.type.type == "array":
            imported_fields[field.name].type = "array"
            imported_fields[field.name].items = import_avro_array_items(field.type)
        else:  # primitive type
            imported_fields[field.name].type = map_type_from_avro(field.type.type)

    return imported_fields


def import_avro_array_items(array_schema):
    items = Field()
    for prop in array_schema.other_props:
        items.__setattr__(prop, array_schema.other_props[prop])

    if array_schema.items.type == "record":
        items.type = "object"
        items.fields = import_record_fields(array_schema.items.fields)
    elif array_schema.items.type == "array":
        items.type = "array"
        items.items = import_avro_array_items(array_schema.items)
    else:  # primitive type
        items.type = map_type_from_avro(array_schema.items.type)

    return items


def import_type_of_optional_field(field):
    for field_type in field.type.schemas:
        if field_type.type != "null":
            return map_type_from_avro(field_type.type)
    raise DataContractException(
        type="schema",
        result="failed",
        name="Map avro type to data contract type",
        reason="Could not import optional field: union type does not contain a non-null type",
        engine="datacontract",
    )


def get_record_from_union_field(field):
    for field_type in field.type.schemas:
        if field_type.type == "record":
            return field_type
    return None


def map_type_from_avro(avro_type_str: str):
    # TODO: ambiguous mapping in the export
    if avro_type_str == "null":
        return "null"
    elif avro_type_str == "string":
        return "string"
    elif avro_type_str == "bytes":
        return "binary"
    elif avro_type_str == "double":
        return "double"
    elif avro_type_str == "int":
        return "int"
    elif avro_type_str == "long":
        return "long"
    elif avro_type_str == "boolean":
        return "boolean"
    elif avro_type_str == "record":
        return "record"
    elif avro_type_str == "array":
        return "array"
    else:
        raise DataContractException(
            type="schema",
            result="failed",
            name="Map avro type to data contract type",
            reason=f"Unsupported type {avro_type_str} in avro schema.",
            engine="datacontract",
        )
