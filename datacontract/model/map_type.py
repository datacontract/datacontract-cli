"""Key and value of a ``logicalType: map`` property (ODCS v3.2.0, RFC 0030).

A map property carries a ``map`` block with ``key`` and ``value``, both full
property definitions, so nested maps and maps of objects need no special
handling. Before v3.2.0 the CLI stored the same information in custom
properties (``mapKeyType``/``mapValueType`` from Iceberg, Spark and DCS imports,
``mapKeys``/``mapValues`` for DuckDB and ClickHouse exports) with the value's
fields smuggled into ``properties``. Those are still read, so existing
contracts keep working, and are written no more.
"""

from typing import Optional

from open_data_contract_standard.model import MapDefinition, SchemaProperty


def is_map(prop: SchemaProperty) -> bool:
    """True for ``logicalType: map`` and for the pre-3.2.0 ``physicalType: map`` spelling."""
    if prop.logicalType and prop.logicalType.lower() == "map":
        return True
    if prop.physicalType:
        base = prop.physicalType.strip().lower()
        for separator in ("(", "<"):
            base = base.split(separator, 1)[0]
        return base == "map"
    return False


def get_map_key(prop: SchemaProperty) -> Optional[SchemaProperty]:
    """The key definition of a map property, or ``None`` when it declares none."""
    if prop.map and prop.map.key:
        return prop.map.key
    legacy = _custom_property(prop, "mapKeyType") or _custom_property(prop, "mapKeys")
    if legacy:
        return _legacy_property("key", legacy)
    return None


def get_map_value(prop: SchemaProperty) -> Optional[SchemaProperty]:
    """The value definition of a map property, or ``None`` when it declares none."""
    if prop.map and prop.map.value:
        return prop.map.value
    if prop.properties:
        # pre-3.2.0: the value's fields sat on the map property itself
        return SchemaProperty(name="value", logicalType="object", properties=prop.properties)
    legacy = _custom_property(prop, "mapValueType") or _custom_property(prop, "mapValues")
    if legacy:
        return _legacy_property("value", legacy)
    return None


def map_definition(key: Optional[SchemaProperty], value: Optional[SchemaProperty]) -> MapDefinition:
    """A ``map`` block; a missing side defaults to a string, the most common case."""
    return MapDefinition(
        key=key if key is not None else SchemaProperty(logicalType="string"),
        value=value if value is not None else SchemaProperty(logicalType="string"),
    )


def _custom_property(prop: SchemaProperty, name: str) -> Optional[str]:
    for custom_property in prop.customProperties or []:
        if custom_property.property == name and custom_property.value:
            return str(custom_property.value)
    return None


_LOGICAL_TYPES = {"string", "date", "timestamp", "time", "number", "integer", "object", "array", "boolean", "map"}


def _legacy_property(name: str, type_name: str) -> SchemaProperty:
    """A property from a bare type name: a logical type keyword, or a native type otherwise."""
    if type_name.lower() in _LOGICAL_TYPES:
        return SchemaProperty(name=name, logicalType=type_name.lower())
    return SchemaProperty(name=name, physicalType=type_name)
