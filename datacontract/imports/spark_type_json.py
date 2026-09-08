"""Read Spark's type JSON without pyspark.

Unity Catalog reports a column's full type as the JSON `StructField.toJson()`
produces, and it is the only place the nested shape of a struct or array column
is available. Parsing it used to go through `pyspark.sql.types.StructField.fromJson`,
which made pyspark — and the JVM-sized install behind it — a requirement for
importing a Databricks table that has a struct column. The format is plain JSON,
so this reads it directly.

Types are described two ways, matching what pyspark exposes: `logical_type` is
the ODCS logical type, and `simple_string` is the `DataType.simpleString()`
spelling that goes into `physicalType` (`bigint`, `array<struct<a:int>>`).
"""

from __future__ import annotations

from typing import Any, List, Optional, Tuple

from open_data_contract_standard.model import SchemaProperty

from datacontract.imports.odcs_helper import create_property

# Spark's JSON type names mapped to (simpleString spelling, ODCS logical type).
# Most names are their own simpleString; the integer family is where the two
# spellings part ways (`long` is `bigint`, `integer` is `int`).
_PRIMITIVES = {
    "string": ("string", "string"),
    "varchar": ("varchar", "string"),
    "char": ("char", "string"),
    "byte": ("tinyint", "integer"),
    "short": ("smallint", "integer"),
    "integer": ("int", "integer"),
    "long": ("bigint", "integer"),
    "float": ("float", "number"),
    "double": ("double", "number"),
    "decimal": ("decimal", "number"),
    "boolean": ("boolean", "boolean"),
    "binary": ("binary", "array"),
    "date": ("date", "date"),
    "timestamp": ("timestamp", "date"),
    "timestamp_ntz": ("timestamp_ntz", "date"),
    "void": ("void", "string"),
    "variant": ("variant", "object"),
}


def _primitive(name: str) -> Tuple[str, str]:
    # `decimal(10,2)` and `varchar(20)` carry their parameters in both spellings
    base = name.split("(", 1)[0]
    entry = _PRIMITIVES.get(base)
    if entry is None:
        raise ValueError(f"Unsupported Spark type: {name}")
    simple, logical = entry
    return (name if "(" in name else simple), logical


def simple_string(type_json: Any) -> str:
    """The `DataType.simpleString()` spelling of a type, e.g. `array<struct<a:int>>`."""
    if isinstance(type_json, str):
        return _primitive(type_json)[0]

    kind = type_json.get("type")
    if kind == "array":
        return f"array<{simple_string(type_json['elementType'])}>"
    if kind == "map":
        return f"map<{simple_string(type_json['keyType'])},{simple_string(type_json['valueType'])}>"
    if kind == "struct":
        fields = ",".join(f"{f['name']}:{simple_string(f['type'])}" for f in type_json["fields"])
        return f"struct<{fields}>"
    raise ValueError(f"Unsupported Spark type: {type_json}")


def logical_type(type_json: Any) -> str:
    """The ODCS logical type for a Spark type."""
    if isinstance(type_json, str):
        return _primitive(type_json)[1]

    kind = type_json.get("type")
    if kind == "array":
        return "array"
    if kind == "struct":
        return "object"
    if kind == "map":
        return "map"
    raise ValueError(f"Unsupported Spark type: {type_json}")


def property_from_field_json(field: Any) -> SchemaProperty:
    """Convert one Spark `StructField` JSON object into an ODCS property."""
    metadata = field.get("metadata") or {}
    return property_from_type_json(
        name=field["name"],
        type_json=field["type"],
        required=not field.get("nullable", True),
        description=metadata.get("comment"),
    )


def property_from_type_json(
    name: str,
    type_json: Any,
    required: bool = True,
    description: Optional[str] = None,
) -> SchemaProperty:
    """Convert a Spark type from its JSON form into an ODCS property named `name`."""
    logical = logical_type(type_json)

    nested_properties: Optional[List[SchemaProperty]] = None
    items: Optional[SchemaProperty] = None
    map_key: Optional[SchemaProperty] = None
    map_value: Optional[SchemaProperty] = None
    if isinstance(type_json, dict):
        if logical == "array":
            items = property_from_type_json("items", type_json["elementType"], not type_json.get("containsNull", True))
        elif logical == "map":
            map_key = property_from_type_json("key", type_json["keyType"], True)
            map_value = property_from_type_json(
                "value", type_json["valueType"], not type_json.get("valueContainsNull", True)
            )
        elif type_json.get("type") == "struct":
            nested_properties = [property_from_field_json(f) for f in type_json["fields"]]

    return create_property(
        name=name,
        logical_type=logical,
        physical_type=simple_string(type_json),
        description=description,
        required=required if required else None,
        properties=nested_properties,
        items=items,
        map_key=map_key,
        map_value=map_value,
    )
