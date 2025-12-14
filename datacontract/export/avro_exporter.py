import json
from typing import List, Optional, Union

from open_data_contract_standard.model import SchemaObject, SchemaProperty

from datacontract.export.exporter import Exporter, _check_schema_name_for_export


class AvroExporter(Exporter):
    def export(self, data_contract, schema_name, server, sql_server_type, export_args) -> dict:
        model_name, model_value = _check_schema_name_for_export(data_contract, schema_name, self.export_format)
        return to_avro_schema_json(model_name, model_value)


def to_avro_schema(model_name: str, model: SchemaObject) -> dict:
    namespace = _get_config_value(model, "namespace")
    return to_avro_record(model_name, model.properties or [], model.description, namespace)


def to_avro_schema_json(model_name: str, model: SchemaObject) -> str:
    schema = to_avro_schema(model_name, model)
    return json.dumps(schema, indent=2, sort_keys=False)


def to_avro_record(name: str, properties: List[SchemaProperty], description: Optional[str], namespace: Optional[str]) -> dict:
    schema = {"type": "record", "name": name}
    if description is not None:
        schema["doc"] = description
    if namespace is not None:
        schema["namespace"] = namespace
    schema["fields"] = to_avro_fields(properties)
    return schema


def to_avro_fields(properties: List[SchemaProperty]) -> list:
    result = []
    for prop in properties:
        result.append(to_avro_field(prop))
    return result


def _get_config_value(obj: Union[SchemaObject, SchemaProperty], key: str) -> Optional[str]:
    """Get a custom property value."""
    if obj.customProperties is None:
        return None
    for cp in obj.customProperties:
        if cp.property == key:
            return cp.value
    return None


def _get_logical_type_option(prop: SchemaProperty, key: str):
    """Get a logical type option value."""
    if prop.logicalTypeOptions is None:
        return None
    return prop.logicalTypeOptions.get(key)


def _get_enum_values(prop: SchemaProperty):
    """Get enum values from logicalTypeOptions, customProperties, or quality rules."""
    import json
    # First check logicalTypeOptions (legacy/direct ODCS)
    enum_values = _get_logical_type_option(prop, "enum")
    if enum_values:
        return enum_values
    # Then check customProperties (converted from DCS)
    enum_str = _get_config_value(prop, "enum")
    if enum_str:
        try:
            return json.loads(enum_str)
        except (json.JSONDecodeError, TypeError):
            pass
    # Finally check quality rules for invalidValues with validValues
    if prop.quality:
        for q in prop.quality:
            if q.metric == "invalidValues" and q.arguments:
                valid_values = q.arguments.get("validValues")
                if valid_values:
                    return valid_values
    return None


def _parse_default_value(value: str):
    """Parse a default value string to its proper type (bool, int, float, or string)."""
    if value.lower() == "true":
        return True
    if value.lower() == "false":
        return False
    if value.lower() == "null":
        return None
    # Try parsing as int
    try:
        return int(value)
    except ValueError:
        pass
    # Try parsing as float
    try:
        return float(value)
    except ValueError:
        pass
    # Return as string
    return value


def to_avro_field(prop: SchemaProperty) -> dict:
    avro_field = {"name": prop.name}
    if prop.description is not None:
        avro_field["doc"] = prop.description
    is_required_avro = prop.required if prop.required is not None else True
    avro_type = to_avro_type(prop)
    avro_field["type"] = avro_type if is_required_avro else ["null", avro_type]

    # Handle enum types - both required and optional
    enum_values = _get_enum_values(prop)
    avro_config_type = _get_config_value(prop, "avroType")

    if avro_type == "enum" or (isinstance(avro_field["type"], list) and "enum" in avro_field["type"]):
        title = prop.businessName or prop.name
        enum_def = {
            "type": "enum",
            "name": title,
            "symbols": enum_values or [],
        }
        if is_required_avro:
            avro_field["type"] = enum_def
        else:
            # Replace "enum" with the full enum definition in the union
            avro_field["type"] = ["null", enum_def]

    avro_default = _get_config_value(prop, "avroDefault")
    if avro_default is not None:
        if avro_config_type != "enum":
            # Parse the default value to its proper type
            avro_field["default"] = _parse_default_value(avro_default)

    return avro_field


def to_avro_type(prop: SchemaProperty) -> Union[str, dict]:
    avro_logical_type = _get_config_value(prop, "avroLogicalType")
    avro_type = _get_config_value(prop, "avroType")

    if avro_logical_type and avro_type:
        return {"type": avro_type, "logicalType": avro_logical_type}
    if avro_logical_type:
        if avro_logical_type in [
            "timestamp-millis",
            "timestamp-micros",
            "local-timestamp-millis",
            "local-timestamp-micros",
            "time-micros",
        ]:
            return {"type": "long", "logicalType": avro_logical_type}
        if avro_logical_type in ["time-millis", "date"]:
            return {"type": "int", "logicalType": avro_logical_type}
    if avro_type:
        return avro_type

    # Check for enum fields based on presence of enum list and avroType config
    enum_values = _get_enum_values(prop)
    if enum_values and avro_type == "enum":
        return "enum"

    # Use physicalType for more specific type mappings, fall back to logicalType
    physical_type = prop.physicalType.lower() if prop.physicalType else None
    field_type = prop.logicalType

    # Handle specific physical types that need special treatment
    if physical_type in ["float"]:
        return "float"
    elif physical_type in ["double"]:
        return "double"
    elif physical_type in ["long", "bigint"]:
        return "long"
    elif physical_type in ["decimal"]:
        typeVal = {"type": "bytes", "logicalType": "decimal"}
        # Read precision/scale from customProperties
        scale = _get_config_value(prop, "scale")
        precision = _get_config_value(prop, "precision")
        if scale is not None:
            typeVal["scale"] = int(scale)
        if precision is not None:
            typeVal["precision"] = int(precision)
        return typeVal
    elif physical_type in ["map"]:
        values_type = _get_config_value(prop, "values")
        if values_type:
            # Parse JSON array if values is a string like '["string", "long"]'
            import json
            try:
                parsed_values = json.loads(values_type)
                return {"type": "map", "values": parsed_values}
            except (json.JSONDecodeError, TypeError):
                return {"type": "map", "values": values_type}
        else:
            return "bytes"
    elif physical_type in ["timestamp_ntz"]:
        return {"type": "long", "logicalType": "local-timestamp-millis"}

    if field_type is None:
        return "null"
    if field_type.lower() in ["string", "varchar", "text"]:
        return "string"
    elif field_type.lower() in ["number", "numeric"]:
        # https://avro.apache.org/docs/1.11.1/specification/#decimal
        return "bytes"
    elif field_type.lower() in ["decimal"]:
        typeVal = {"type": "bytes", "logicalType": "decimal"}
        # Read precision/scale from customProperties
        scale = _get_config_value(prop, "scale")
        precision = _get_config_value(prop, "precision")
        if scale is not None:
            typeVal["scale"] = int(scale)
        if precision is not None:
            typeVal["precision"] = int(precision)
        return typeVal
    elif field_type.lower() in ["float"]:
        return "float"
    elif field_type.lower() in ["double"]:
        return "double"
    elif field_type.lower() in ["integer", "int"]:
        return "int"
    elif field_type.lower() in ["long", "bigint"]:
        return "long"
    elif field_type.lower() in ["boolean"]:
        return "boolean"
    elif field_type.lower() in ["timestamp", "timestamp_tz"]:
        return {"type": "long", "logicalType": "timestamp-millis"}
    elif field_type.lower() in ["timestamp_ntz"]:
        return {"type": "long", "logicalType": "local-timestamp-millis"}
    elif field_type.lower() in ["date"]:
        return {"type": "int", "logicalType": "date"}
    elif field_type.lower() in ["time"]:
        return "long"
    elif field_type.lower() in ["map"]:
        values_type = _get_config_value(prop, "values")
        if values_type:
            return {"type": "map", "values": values_type}
        else:
            return "bytes"
    elif field_type.lower() in ["object", "record", "struct"]:
        namespace = _get_config_value(prop, "namespace")
        return to_avro_record(prop.name, prop.properties or [], prop.description, namespace)
    elif field_type.lower() in ["binary"]:
        return "bytes"
    elif field_type.lower() in ["array"]:
        if prop.items:
            return {"type": "array", "items": to_avro_type(prop.items)}
        return {"type": "array", "items": "string"}
    elif field_type.lower() in ["null"]:
        return "null"
    else:
        return "bytes"
