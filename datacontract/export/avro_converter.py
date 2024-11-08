import json

from datacontract.export.exporter import Exporter, _check_models_for_export
from datacontract.model.data_contract_specification import Field


class AvroExporter(Exporter):
    def export(self, data_contract, model, server, sql_server_type, export_args) -> dict:
        model_name, model_value = _check_models_for_export(data_contract, model, self.export_format)
        return to_avro_schema_json(model_name, model_value)


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
    is_required_avro = field.required if field.required is not None else True
    avro_type = to_avro_type(field, field_name)
    avro_field["type"] = avro_type if is_required_avro else ["null", avro_type]

    if avro_field["type"] == "enum":
        avro_field["type"] = {
            "type": "enum",
            "name": field.title,
            "symbols": field.enum,
        }

    if field.config:
        if "avroDefault" in field.config:
            if field.config.get("avroType") != "enum":
                avro_field["default"] = field.config["avroDefault"]

    return avro_field


def to_avro_type(field: Field, field_name: str) -> str | dict:
    if field.config:
        if "avroLogicalType" in field.config and "avroType" in field.config:
            return {"type": field.config["avroType"], "logicalType": field.config["avroLogicalType"]}
        if "avroLogicalType" in field.config:
            if field.config["avroLogicalType"] in [
                "timestamp-millis",
                "timestamp-micros",
                "local-timestamp-millis",
                "local-timestamp-micros",
                "time-micros",
            ]:
                return {"type": "long", "logicalType": field.config["avroLogicalType"]}
            if field.config["avroLogicalType"] in ["time-millis", "date"]:
                return {"type": "int", "logicalType": field.config["avroLogicalType"]}
        if "avroType" in field.config:
            return field.config["avroType"]

    if field.type is None:
        return "null"
    if field.type in ["string", "varchar", "text"]:
        return "string"
    elif field.type in ["number", "numeric"]:
        # https://avro.apache.org/docs/1.11.1/specification/#decimal
        return "bytes"
    elif field.type in ["decimal"]:
        typeVal = {"type": "bytes", "logicalType": "decimal"}
        if field.scale is not None:
            typeVal["scale"] = field.scale
        if field.precision is not None:
            typeVal["precision"] = field.precision
        return typeVal
    elif field.type in ["float", "double"]:
        return "double"
    elif field.type in ["integer", "int"]:
        return "int"
    elif field.type in ["long", "bigint"]:
        return "long"
    elif field.type in ["boolean"]:
        return "boolean"
    elif field.type in ["timestamp", "timestamp_tz"]:
        return {"type": "long", "logicalType": "timestamp-millis"}
    elif field.type in ["timestamp_ntz"]:
        return {"type": "long", "logicalType": "local-timestamp-millis"}
    elif field.type in ["date"]:
        return {"type": "int", "logicalType": "date"}
    elif field.type in ["time"]:
        return "long"
    elif field.type in ["object", "record", "struct"]:
        return to_avro_record(field_name, field.fields, field.description, None)
    elif field.type in ["binary"]:
        return "bytes"
    elif field.type in ["array"]:
        return {"type": "array", "items": to_avro_type(field.items, field_name)}
    elif field.type in ["null"]:
        return "null"
    else:
        return "bytes"
