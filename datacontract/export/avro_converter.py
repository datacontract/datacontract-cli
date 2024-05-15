import json

from datacontract.model.data_contract_specification import Field


def to_avro_schema(model_name, model) -> dict:
    return to_avro_record(model_name, model.fields, model.description, model.namespace)


def to_avro_schema_json(model_name, model) -> str:
    schema = to_avro_schema(model_name, model)
    return json.dumps(schema, indent=2, sort_keys=False)


def to_avro_record(name, fields, description, namespace) -> dict:
    schema = {"type": "record", "name": name}
    if description is not None:
        schema["doc"] = description
    if namespace is not None:
        schema["namespace"] = namespace
    schema["fields"] = to_avro_fields(fields)
    return schema


def to_avro_fields(fields):
    result = []
    for field_name, field in fields.items():
        result.append(to_avro_field(field, field_name))
    return result


def to_avro_field(field, field_name):
    avro_field = {"name": field_name}
    if field.description is not None:
        avro_field["doc"] = field.description
    avro_field["type"] = to_avro_type(field, field_name)
    # add logical type definitions for any of the date type fields
    if field.type in ["timestamp", "timestamp_tz", "timestamp_ntz", "date"]:
        avro_field["logicalType"] = to_avro_logical_type(field.type)

    return avro_field


def to_avro_type(field: Field, field_name: str) -> str | dict:
    if field.type is None:
        return "null"
    if field.type in ["string", "varchar", "text"]:
        return "string"
    elif field.type in ["number", "decimal", "numeric"]:
        # https://avro.apache.org/docs/1.11.1/specification/#decimal
        return "bytes"
    elif field.type in ["float", "double"]:
        return "double"
    elif field.type in ["integer", "int"]:
        return "int"
    elif field.type in ["long", "bigint"]:
        return "long"
    elif field.type in ["boolean"]:
        return "boolean"
    elif field.type in ["timestamp", "timestamp_tz"]:
        return "long"
    elif field.type in ["timestamp_ntz"]:
        return "long"
    elif field.type in ["date"]:
        return "int"
    elif field.type in ["time"]:
        return "long"
    elif field.type in ["object", "record", "struct"]:
        return to_avro_record(field_name, field.fields, field.description, None)
    elif field.type in ["binary"]:
        return "bytes"
    elif field.type in ["array"]:
        # TODO support array structs
        return "array"
    elif field.type in ["null"]:
        return "null"
    else:
        return "bytes"

def to_avro_logical_type(type: str) -> str:
    if type in ["timestamp", "timestamp_tz"]:
        return "timestamp-millis"
    elif type in ["timestamp_ntz"]:
        return "local-timestamp-millis"
    elif type in ["date"]:
        return "date"
    else:
        return ""