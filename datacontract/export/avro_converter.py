import json

from datacontract.model.data_contract_specification import Field


def to_avro_schema(model_name, fields) -> str:
    schema = to_avro_record(model_name, fields)
    return json.dumps(schema)


def to_avro_record(name, fields):
    schema = {
        "type": "record",
        "name": name,
        "fields": to_avro_fields(fields)
    }
    return schema


def to_avro_fields(fields):
    result = []
    for field_name, field in fields.items():
        result.append(to_avro_field(field, field_name))
    return result


def to_avro_field(field, field_name):
    return {
        "name": field_name,
        "type": to_avro_type(field, field_name)
    }


def to_avro_type(field: Field, field_name: str):
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
        return "string"
    elif field.type in ["timestamp_ntz"]:
        return "string"
    elif field.type in ["date"]:
        return "int"
    elif field.type in ["time"]:
        return "long"
    elif field.type in ["object", "record", "struct"]:
        return to_avro_record(field_name, field.fields)
    elif field.type in ["binary"]:
        return "bytes"
    elif field.type in ["array"]:
        # TODO support array structs
        return "array"
    elif field.type in ["null"]:
        return "null"
    else:
        return "bytes"
