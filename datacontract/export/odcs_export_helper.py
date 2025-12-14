"""Helper functions for ODCS export operations."""

from typing import Any, Dict, List, Optional, Tuple

from open_data_contract_standard.model import (
    OpenDataContractStandard,
    SchemaObject,
    SchemaProperty,
    Server,
)


def get_schema_by_name(
    data_contract: OpenDataContractStandard, name: str
) -> Optional[SchemaObject]:
    """Get a schema object by name from the data contract."""
    if data_contract.schema_ is None:
        return None
    return next((s for s in data_contract.schema_ if s.name == name), None)


def get_all_schema_names(data_contract: OpenDataContractStandard) -> List[str]:
    """Get all schema names from the data contract."""
    if data_contract.schema_ is None:
        return []
    return [s.name for s in data_contract.schema_]


def get_server_by_name(
    data_contract: OpenDataContractStandard, name: str
) -> Optional[Server]:
    """Get a server by name from the data contract."""
    if data_contract.servers is None:
        return None
    return next((s for s in data_contract.servers if s.server == name), None)


def get_first_server(data_contract: OpenDataContractStandard) -> Optional[Server]:
    """Get the first server from the data contract."""
    if data_contract.servers is None or len(data_contract.servers) == 0:
        return None
    return data_contract.servers[0]


def get_owner(data_contract: OpenDataContractStandard) -> Optional[str]:
    """Get the owner from the data contract (team name)."""
    if data_contract.team is None:
        return None
    return data_contract.team.name


def get_description(data_contract: OpenDataContractStandard) -> Optional[str]:
    """Get the description from the data contract."""
    return data_contract.description


def property_to_dict(properties: List[SchemaProperty]) -> Dict[str, SchemaProperty]:
    """Convert a list of properties to a dict keyed by property name."""
    if properties is None:
        return {}
    return {p.name: p for p in properties}


def get_property_type(prop: SchemaProperty) -> Optional[str]:
    """Get the type of a property (logicalType or physicalType)."""
    return prop.logicalType or prop.physicalType


def get_property_config(prop: SchemaProperty, key: str) -> Optional[Any]:
    """Get a custom property value from a SchemaProperty."""
    if prop.customProperties is None:
        return None
    for cp in prop.customProperties:
        if cp.property == key:
            return cp.value
    return None


def get_logical_type_option(prop: SchemaProperty, key: str) -> Optional[Any]:
    """Get a logical type option from a SchemaProperty."""
    if prop.logicalTypeOptions is None:
        return None
    return prop.logicalTypeOptions.get(key)


def iter_properties(schema: SchemaObject) -> List[Tuple[str, SchemaProperty]]:
    """Iterate over properties in a schema object, yielding (name, property) tuples."""
    if schema.properties is None:
        return []
    return [(p.name, p) for p in schema.properties]


def iter_schemas(data_contract: OpenDataContractStandard) -> List[Tuple[str, SchemaObject]]:
    """Iterate over schemas in a data contract, yielding (name, schema) tuples."""
    if data_contract.schema_ is None:
        return []
    return [(s.name, s) for s in data_contract.schema_]


class PropertyAdapter:
    """Adapter to make SchemaProperty compatible with DCS Field interface.

    This adapter provides a Field-like interface for SchemaProperty to maintain
    backward compatibility with existing type converters.
    """

    def __init__(self, prop: SchemaProperty):
        self._prop = prop

    @property
    def name(self) -> Optional[str]:
        return self._prop.name

    @property
    def type(self) -> Optional[str]:
        """Return the logical type (equivalent to DCS field.type)."""
        return self._prop.logicalType

    @property
    def required(self) -> Optional[bool]:
        return self._prop.required

    @property
    def description(self) -> Optional[str]:
        return self._prop.description

    @property
    def primaryKey(self) -> Optional[bool]:
        return self._prop.primaryKey

    @property
    def primary(self) -> Optional[bool]:
        # Alias for primaryKey
        return self._prop.primaryKey

    @property
    def unique(self) -> Optional[bool]:
        return self._prop.unique

    @property
    def format(self) -> Optional[str]:
        # Check for format in logicalTypeOptions
        return get_logical_type_option(self._prop, "format")

    @property
    def precision(self) -> Optional[int]:
        return get_logical_type_option(self._prop, "precision")

    @property
    def scale(self) -> Optional[int]:
        return get_logical_type_option(self._prop, "scale")

    @property
    def minLength(self) -> Optional[int]:
        return get_logical_type_option(self._prop, "minLength")

    @property
    def maxLength(self) -> Optional[int]:
        return get_logical_type_option(self._prop, "maxLength")

    @property
    def minimum(self) -> Optional[float]:
        return get_logical_type_option(self._prop, "minimum")

    @property
    def maximum(self) -> Optional[float]:
        return get_logical_type_option(self._prop, "maximum")

    @property
    def exclusiveMinimum(self) -> Optional[float]:
        return get_logical_type_option(self._prop, "exclusiveMinimum")

    @property
    def exclusiveMaximum(self) -> Optional[float]:
        return get_logical_type_option(self._prop, "exclusiveMaximum")

    @property
    def pattern(self) -> Optional[str]:
        return get_logical_type_option(self._prop, "pattern")

    @property
    def enum(self) -> Optional[List[str]]:
        return get_logical_type_option(self._prop, "enum")

    @property
    def title(self) -> Optional[str]:
        return self._prop.businessName

    @property
    def tags(self) -> Optional[List[str]]:
        return self._prop.tags

    @property
    def pii(self) -> Optional[bool]:
        return get_property_config(self._prop, "pii")

    @property
    def classification(self) -> Optional[str]:
        return self._prop.classification

    @property
    def references(self) -> Optional[str]:
        # Check relationships for foreign key references
        if self._prop.relationships is None:
            return None
        for rel in self._prop.relationships:
            if hasattr(rel, 'ref'):
                return rel.ref
        return None

    @property
    def config(self) -> Optional[Dict[str, Any]]:
        """Convert customProperties to config dict."""
        if self._prop.customProperties is None:
            return None
        return {cp.property: cp.value for cp in self._prop.customProperties}

    @property
    def items(self) -> Optional["PropertyAdapter"]:
        """Return items property for array types."""
        if self._prop.items is None:
            return None
        return PropertyAdapter(self._prop.items)

    @property
    def fields(self) -> Dict[str, "PropertyAdapter"]:
        """Return nested fields as a dict of PropertyAdapters."""
        if self._prop.properties is None:
            return {}
        return {p.name: PropertyAdapter(p) for p in self._prop.properties}

    @property
    def keys(self) -> Optional["PropertyAdapter"]:
        """Return keys property for map types (from customProperties)."""
        keys_prop = get_property_config(self._prop, "mapKeys")
        if keys_prop is None:
            return None
        # Create a minimal property for the key type
        from open_data_contract_standard.model import SchemaProperty
        key_prop = SchemaProperty(name="key")
        key_prop.logicalType = keys_prop if isinstance(keys_prop, str) else "string"
        return PropertyAdapter(key_prop)

    @property
    def values(self) -> Optional["PropertyAdapter"]:
        """Return values property for map types (from customProperties)."""
        values_prop = get_property_config(self._prop, "mapValues")
        if values_prop is None:
            return None
        from open_data_contract_standard.model import SchemaProperty
        val_prop = SchemaProperty(name="value")
        val_prop.logicalType = values_prop if isinstance(values_prop, str) else "string"
        return PropertyAdapter(val_prop)

    @property
    def namespace(self) -> Optional[str]:
        """Get namespace from customProperties."""
        return get_property_config(self._prop, "namespace")


class SchemaAdapter:
    """Adapter to make SchemaObject compatible with DCS Model interface."""

    def __init__(self, schema: SchemaObject):
        self._schema = schema

    @property
    def name(self) -> Optional[str]:
        return self._schema.name

    @property
    def type(self) -> Optional[str]:
        return self._schema.physicalType

    @property
    def description(self) -> Optional[str]:
        return self._schema.description

    @property
    def title(self) -> Optional[str]:
        return self._schema.businessName

    @property
    def namespace(self) -> Optional[str]:
        # Check customProperties for namespace
        if self._schema.customProperties is None:
            return None
        for cp in self._schema.customProperties:
            if cp.property == "namespace":
                return cp.value
        return None

    @property
    def primaryKey(self) -> Optional[List[str]]:
        """Get primary key columns."""
        if self._schema.properties is None:
            return None
        pk_cols = [
            p.name for p in self._schema.properties
            if p.primaryKey
        ]
        return pk_cols if pk_cols else None

    @property
    def fields(self) -> Dict[str, PropertyAdapter]:
        """Return fields as a dict of PropertyAdapters."""
        if self._schema.properties is None:
            return {}
        return {p.name: PropertyAdapter(p) for p in self._schema.properties}


def adapt_property(prop: SchemaProperty) -> PropertyAdapter:
    """Create a PropertyAdapter from a SchemaProperty."""
    return PropertyAdapter(prop)


def adapt_schema(schema: SchemaObject) -> SchemaAdapter:
    """Create a SchemaAdapter from a SchemaObject."""
    return SchemaAdapter(schema)
