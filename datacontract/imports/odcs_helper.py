"""Helper functions for creating ODCS (OpenDataContractStandard) objects."""

import re
from typing import Any, Dict, List

from open_data_contract_standard.model import (
    CustomProperty,
    DataQuality,
    EnumValue,
    OpenDataContractStandard,
    Role,
    SchemaObject,
    SchemaProperty,
    Server,
)

from datacontract.model.map_type import map_definition
from datacontract.model.server import to_odcs_server_type


def create_odcs(
    id: str = None,
    name: str = None,
    version: str = "1.0.0",
    status: str = "draft",
) -> OpenDataContractStandard:
    """Create a new OpenDataContractStandard instance with default values."""
    return OpenDataContractStandard(
        apiVersion="v3.2.0",
        kind="DataContract",
        id=id or "my-data-contract",
        name=name or "My Data Contract",
        version=version,
        status=status,
    )


def create_schema_object(
    name: str,
    physical_type: str = "table",
    description: str = None,
    business_name: str = None,
    properties: List[SchemaProperty] = None,
    tags: List[str] = None,
    quality: List[DataQuality] = None,
) -> SchemaObject:
    """Create a SchemaObject (equivalent to DCS Model)."""
    schema = SchemaObject(
        name=name,
        physicalName=name,
        logicalType="object",
        physicalType=physical_type,
    )
    if description:
        schema.description = description
    if business_name:
        schema.businessName = business_name
    if properties:
        schema.properties = properties
    if tags:
        schema.tags = tags
    if quality:
        schema.quality = quality
    return schema


def create_property(
    name: str,
    logical_type: str,
    physical_type: str = None,
    description: str = None,
    required: bool = None,
    primary_key: bool = None,
    primary_key_position: int = None,
    unique: bool = None,
    classification: str = None,
    tags: List[str] = None,
    examples: List[Any] = None,
    min_length: int = None,
    max_length: int = None,
    pattern: str = None,
    minimum: float = None,
    maximum: float = None,
    exclusive_minimum: float = None,
    exclusive_maximum: float = None,
    precision: int = None,
    scale: int = None,
    format: str = None,
    properties: List["SchemaProperty"] = None,
    items: "SchemaProperty" = None,
    custom_properties: Dict[str, Any] = None,
    id: str = None,
    quality: List[DataQuality] = None,
    enum: List[Any] = None,
    map_key: "SchemaProperty" = None,
    map_value: "SchemaProperty" = None,
    dimensions: int = None,
    element_type: str = None,
) -> SchemaProperty:
    """Create a SchemaProperty (equivalent to DCS Field).

    ``enum`` lists the allowed values, as plain values or ``EnumValue`` entries (ODCS v3.2.0).
    ``map_key`` and ``map_value`` describe a ``logicalType: map`` property; a missing side is a string.
    ``dimensions`` and ``element_type`` describe a ``logicalType: vector`` property.
    """
    prop = SchemaProperty(name=name, id=id)
    prop.logicalType = logical_type

    if physical_type:
        prop.physicalType = physical_type
    if description:
        prop.description = description
    if required is not None:
        prop.required = required
    if primary_key:
        prop.primaryKey = primary_key
        prop.primaryKeyPosition = primary_key_position or 1
    if unique:
        prop.unique = unique
    if classification:
        prop.classification = classification
    if tags:
        prop.tags = tags
    if examples:
        prop.examples = examples
    if properties:
        prop.properties = properties
    if items:
        prop.items = items

    # Logical type options
    logical_type_options = {}
    if min_length is not None:
        logical_type_options["minLength"] = min_length
    if max_length is not None:
        logical_type_options["maxLength"] = max_length
    if pattern:
        logical_type_options["pattern"] = pattern
    if minimum is not None:
        logical_type_options["minimum"] = minimum
    if maximum is not None:
        logical_type_options["maximum"] = maximum
    if exclusive_minimum is not None:
        logical_type_options["exclusiveMinimum"] = exclusive_minimum
    if exclusive_maximum is not None:
        logical_type_options["exclusiveMaximum"] = exclusive_maximum
    if format:
        logical_type_options["format"] = format
    if dimensions is not None:
        logical_type_options["dimensions"] = dimensions
    if element_type:
        logical_type_options["elementType"] = element_type
    if logical_type_options:
        prop.logicalTypeOptions = logical_type_options

    # precision/scale are forbidden in logicalTypeOptions for number types per ODCS v3.1.0,
    # so carry them in customProperties instead.
    custom_properties = dict(custom_properties or {})
    if precision is not None:
        custom_properties.setdefault("precision", precision)
    if scale is not None:
        custom_properties.setdefault("scale", scale)
    if custom_properties:
        prop.customProperties = [CustomProperty(property=k, value=v) for k, v in custom_properties.items()]

    # Data quality
    if quality:
        prop.quality = quality

    if enum:
        prop.enum = [entry if isinstance(entry, EnumValue) else EnumValue(value=entry) for entry in enum]

    if logical_type == "map" or map_key is not None or map_value is not None:
        prop.map = map_definition(map_key, map_value)

    return prop


def create_server(
    name: str,
    server_type: str,
    environment: str = None,
    host: str = None,
    port: int = None,
    database: str = None,
    schema: str = None,
    account: str = None,
    project: str = None,
    dataset: str = None,
    path: str = None,
    location: str = None,
    catalog: str = None,
    topic: str = None,
    format: str = None,
    roles: List[Role] = None,
    warehouse: str = None,
    region_name: str = None,
    staging_dir: str = None,
    service_name: str = None,
) -> Server:
    """Create a Server object.

    Server types outside the ODCS enum (e.g. ``dataframe``) are written in a
    standard-compliant way as ``type: custom`` with the real type carried in a
    ``customType`` custom property.
    """
    odcs_type, custom_properties = to_odcs_server_type(server_type)
    server = Server(server=name, type=odcs_type)
    if custom_properties:
        server.customProperties = custom_properties
    if environment:
        server.environment = environment
    if host:
        server.host = host
    if port:
        server.port = port
    if database:
        server.database = database
    if schema:
        server.schema_ = schema
    if account:
        server.account = account
    if project:
        server.project = project
    if dataset:
        server.dataset = dataset
    if path:
        server.path = path
    if location:
        server.location = location
    if catalog:
        server.catalog = catalog
    if topic:
        server.topic = topic
    if format:
        server.format = format
    if roles:
        server.roles = roles
    if warehouse:
        server.warehouse = warehouse
    if region_name:
        server.regionName = region_name
    if staging_dir:
        server.stagingDir = staging_dir
    if service_name:
        server.serviceName = service_name
    return server


# Type mapping from various SQL dialects to ODCS logical types
SQL_TO_LOGICAL_TYPE = {
    # String types
    "varchar": "string",
    "char": "string",
    "nvarchar": "string",
    "nchar": "string",
    "text": "string",
    "ntext": "string",
    "string": "string",
    "clob": "string",
    "nclob": "string",
    # Integer types
    "int": "integer",
    "integer": "integer",
    "smallint": "integer",
    "tinyint": "integer",
    "mediumint": "integer",
    "int2": "integer",
    "int4": "integer",
    "bigint": "integer",
    "int8": "integer",
    "long": "integer",
    # Float types
    "float": "number",
    "real": "number",
    "float4": "number",
    "float8": "number",
    "double": "number",
    "double precision": "number",
    # Decimal types
    "decimal": "number",
    "numeric": "number",
    "number": "number",
    # Boolean types
    "boolean": "boolean",
    "bool": "boolean",
    "bit": "boolean",
    # Date/time types
    "date": "date",
    "timestamp": "date",
    "datetime": "date",
    "datetime2": "date",
    "timestamptz": "date",
    "timestamp_tz": "date",
    "timestamp_ntz": "date",
    "time": "string",
    # Binary types
    "binary": "array",
    "varbinary": "array",
    "blob": "array",
    "bytes": "array",
    "bytea": "array",
    # Complex types
    "array": "array",
    "object": "object",
    "struct": "object",
    "record": "object",
    "map": "map",
    "vector": "vector",
    "halfvec": "vector",
    "json": "object",
    "jsonb": "object",
    "variant": "object",
}


def split_type_arguments(arguments: str) -> List[str]:
    """Split the arguments of a parameterized type on the commas of the top level only."""
    parts, depth, start = [], 0, 0
    for index, char in enumerate(arguments):
        if char in "<(":
            depth += 1
        elif char in ">)":
            depth -= 1
        elif char == "," and depth == 0:
            parts.append(arguments[start:index])
            start = index + 1
    parts.append(arguments[start:])
    return [part.strip() for part in parts if part.strip()]


def property_from_type_string(name: str, type_string: str) -> SchemaProperty:
    """A property for a native type string such as ``map<string,array<int>>`` or ``STRUCT<a: INT>``.

    ``map``, ``array``/``list`` and ``struct``/``row`` are expanded recursively (the
    ``map<k,v>``, ``map(k,v)``, ``array<t>`` and ``struct<name:type,...>`` spellings of
    Spark, Databricks, Hive, Glue, Trino and Snowflake); anything else is a scalar.
    """
    text = type_string.strip()
    lowered = text.lower()
    match = re.match(r"^(map|array|list|struct|row)\s*([<(])(.*)([>)])$", lowered, re.S)
    if match:
        kind, inner = match.group(1), text[match.start(3) : match.end(3)]
        arguments = split_type_arguments(inner)
        if kind == "map" and len(arguments) == 2:
            return create_property(
                name=name,
                logical_type="map",
                physical_type=text,
                map_key=property_from_type_string("key", arguments[0]),
                map_value=property_from_type_string("value", arguments[1]),
            )
        if kind in ("array", "list") and len(arguments) == 1:
            return create_property(
                name=name,
                logical_type="array",
                physical_type=text,
                items=property_from_type_string("items", arguments[0]),
            )
        if kind in ("struct", "row"):
            properties = []
            for argument in arguments:
                field_name, _, field_type = argument.partition(":")
                if not field_type:
                    field_name, _, field_type = argument.partition(" ")
                properties.append(property_from_type_string(field_name.strip().strip('`"'), field_type.strip()))
            return create_property(name=name, logical_type="object", physical_type=text, properties=properties)
    return create_property(name=name, logical_type=map_sql_type_to_logical(text), physical_type=text)


def map_sql_type_to_logical(sql_type: str) -> str:
    """Map a SQL type string to an ODCS logical type."""
    if sql_type is None:
        return "string"

    sql_type_lower = sql_type.lower().strip()

    # Handle parameterized types (e.g., VARCHAR(255), DECIMAL(10,2))
    base_type = sql_type_lower.split("(")[0].strip()

    return SQL_TO_LOGICAL_TYPE.get(base_type, "string")


# Type mapping from Avro to ODCS logical types
AVRO_TO_LOGICAL_TYPE = {
    "null": None,
    "string": "string",
    "bytes": "array",
    "int": "integer",
    "long": "integer",
    "float": "number",
    "double": "number",
    "boolean": "boolean",
    "record": "object",
    "array": "array",
    "map": "map",
    "enum": "string",
    "fixed": "array",
}


def map_avro_type_to_logical(avro_type: str) -> str:
    """Map an Avro type string to an ODCS logical type."""
    return AVRO_TO_LOGICAL_TYPE.get(avro_type, "string")


# Avro logical type mapping
AVRO_LOGICAL_TYPE_MAPPING = {
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


def map_avro_logical_type(avro_logical_type: str) -> str:
    """Map an Avro logical type to an ODCS logical type."""
    return AVRO_LOGICAL_TYPE_MAPPING.get(avro_logical_type, "string")
