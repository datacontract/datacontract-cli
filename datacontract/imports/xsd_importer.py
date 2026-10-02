import inspect
import logging
import warnings
from decimal import Decimal
from pathlib import Path

from open_data_contract_standard.model import CustomProperty, OpenDataContractStandard, SchemaProperty

from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import create_odcs, create_property, create_schema_object
from datacontract.model.exceptions import DataContractException

logger = logging.getLogger(__name__)

XS = "{http://www.w3.org/2001/XMLSchema}"

INTEGER_TYPES = {
    "integer", "int", "long", "short", "byte",
    "nonNegativeInteger", "positiveInteger", "nonPositiveInteger", "negativeInteger",
    "unsignedLong", "unsignedInt", "unsignedShort", "unsignedByte",
}  # fmt: skip
LOGICAL_TYPES = {
    "boolean": "boolean",
    "decimal": "number",
    "float": "number",
    "double": "number",
    "date": "date",
    "dateTime": "timestamp",
    "dateTimeStamp": "timestamp",
    "time": "time",
} | dict.fromkeys(INTEGER_TYPES, "integer")


class XsdImporter(Importer):
    def import_source(self, source: str, import_args: dict) -> OpenDataContractStandard:
        return import_xsd(source)


def import_xsd(source: str) -> OpenDataContractStandard:
    """Import an XML Schema (XSD) and create an ODCS data contract with one schema per root element."""
    schema = load_xml_schema(source)
    from xmlschema import XsdElement

    referenced = {element.name for element in schema.iter_components(XsdElement) if element.ref is not None}
    # Global elements only used through ref are part of another element; fall back to all for cyclic refs
    roots = [el for el in schema.elements.values() if el.name not in referenced] or list(schema.elements.values())

    odcs = create_odcs(name=roots[0].local_name if len(roots) == 1 else Path(source).stem)
    odcs.schema_ = []
    for root in roots:
        prop = element_property(root, optional=False, stack=())
        schema_object = create_schema_object(
            name=prop.name,
            physical_type="object",
            description=prop.description,
            properties=prop.properties if prop.logicalType == "object" else [prop],
        )
        if root.target_namespace:
            schema_object.customProperties = [CustomProperty(property="xmlNamespace", value=root.target_namespace)]
        odcs.schema_.append(schema_object)
    return odcs


def load_xml_schema(source: str):
    try:
        import xmlschema
    except ImportError as e:
        raise ImportError(
            "xmlschema is required for XML Schema import. Install with: pip install datacontract-cli[xml]"
        ) from e

    try:
        with warnings.catch_warnings(record=True) as caught:
            warnings.simplefilter("always")
            # lax: real-world schemas break rules the import does not depend on, or reference remote schemas
            schema = xmlschema.XMLSchema(source, validation="lax", allow="local")
    except (OSError, xmlschema.XMLSchemaException) as e:
        raise DataContractException(
            type="schema",
            name="Parse XML Schema",
            reason=f"Failed to parse XML Schema from {source}: {e}",
            engine="datacontract-cli",
            original_exception=e,
        )
    for warning in caught:
        logger.warning(str(warning.message))
    for error in schema.all_errors:
        logger.warning(f"Invalid XML Schema: {error.message}")
    if not schema.elements:
        raise DataContractException(
            type="schema",
            name="Parse XML Schema",
            reason=f"The XML Schema {source} declares no global element",
            engine="datacontract-cli",
        )
    return schema


def element_property(element, optional: bool, stack: tuple) -> SchemaProperty:
    name = element.local_name
    description = documentation(element) or (documentation(element.ref) if element.ref is not None else None)
    required = not optional and element.min_occurs > 0 and not element.nillable
    value = type_property(name, element.type, stack)

    if element.max_occurs is None or element.max_occurs > 1:
        value.name = "items"
        array = create_property(
            name=name,
            logical_type="array",
            physical_type="array",
            description=description,
            required=required or None,
            items=value,
        )
        occurs = {"minItems": element.min_occurs if element.min_occurs > 1 else None, "maxItems": element.max_occurs}
        array.logicalTypeOptions = {key: value for key, value in occurs.items() if value is not None} or None
        return array
    value.description = description
    value.required = required or None
    return value


def type_property(name: str, xsd_type, stack: tuple) -> SchemaProperty:
    if xsd_type.is_simple():
        return simple_property(name, xsd_type)
    attributes = attribute_properties(xsd_type)
    if xsd_type.has_simple_content():
        if not attributes:
            return simple_property(name, xsd_type.content)
        # The text of an element with attributes is its value property
        properties = [simple_property("value", xsd_type.content, xml_node="text")] + attributes
    elif any(xsd_type is seen for seen in stack):
        # A recursive type stops at its first repetition
        properties = None
    else:
        properties = content_properties(xsd_type.content, xsd_type.content.model == "choice", stack + (xsd_type,))
        properties += attributes
    return create_property(name=name, logical_type="object", physical_type="object", properties=properties)


def content_properties(group, optional: bool, stack: tuple) -> list[SchemaProperty]:
    """The elements of a model group, with nested groups flattened; a choice makes its elements optional."""
    from xmlschema.validators import XsdElement, XsdGroup

    properties = []
    for particle in group:
        if isinstance(particle, XsdGroup):
            nested_optional = optional or particle.model == "choice" or particle.min_occurs == 0
            properties += content_properties(particle, nested_optional, stack)
        elif isinstance(particle, XsdElement):
            properties.append(element_property(particle, optional, stack))
    return properties


def attribute_properties(xsd_type) -> list[SchemaProperty]:
    properties = []
    for attribute in xsd_type.attributes.values():
        if attribute.use == "prohibited" or attribute.name is None:
            continue
        prop = simple_property(attribute.local_name, attribute.type, xml_node="attribute")
        prop.description = documentation(attribute)
        prop.required = attribute.use == "required" or None
        properties.append(prop)
    return properties


def simple_property(name: str, xsd_type, xml_node: str = None) -> SchemaProperty:
    """A property of simple type; ``xml_node`` marks an attribute or the text of an element with attributes."""
    custom_properties = {"xmlNode": xml_node} if xml_node else None
    if xsd_type.is_list():
        # One text value of space-separated items, whose facets count items rather than characters
        return create_property(
            name=name, logical_type="string", physical_type="list", custom_properties=custom_properties
        )
    if xsd_type.is_union():
        members = "|".join(dict.fromkeys(builtin_type(member) for member in xsd_type.member_types))
        # ODCS has no union type
        return create_property(
            name=name, logical_type="string", physical_type=members, custom_properties=custom_properties
        )

    base = builtin_type(xsd_type)
    facets = derived_facets(xsd_type)
    length = facets.get("length")
    patterns = facets.get("pattern")
    return create_property(
        name=name,
        logical_type=LOGICAL_TYPES.get(base, "string"),
        physical_type=base,
        enum=[plain(value) for value in facets["enumeration"]] if "enumeration" in facets else None,
        # XSD regular expressions have no non-capturing groups
        pattern=None if not patterns else patterns[0] if len(patterns) == 1 else "|".join(f"({p})" for p in patterns),
        min_length=facets.get("minLength", length),
        max_length=facets.get("maxLength", length),
        minimum=plain(facets.get("minInclusive")),
        maximum=plain(facets.get("maxInclusive")),
        exclusive_minimum=plain(facets.get("minExclusive")),
        exclusive_maximum=plain(facets.get("maxExclusive")),
        precision=facets.get("totalDigits"),
        scale=facets.get("fractionDigits"),
        custom_properties=custom_properties,
    )


def builtin_type(xsd_type) -> str:
    """The local name of the builtin type a simple type is derived from."""
    while xsd_type.name is None or not xsd_type.name.startswith(XS):
        xsd_type = simple_base(xsd_type)
    return xsd_type.local_name


def derived_facets(xsd_type) -> dict:
    """The facets of a simple type and the user-defined types it derives from; the most derived wins."""
    facets = {}
    while xsd_type.name is None or not xsd_type.name.startswith(XS):
        for qname, facet in xsd_type.facets.items():
            key = qname.removeprefix(XS)
            if key in facets or facet is None:
                continue
            if key == "enumeration":
                facets[key] = facet.enumeration
            elif key == "pattern":
                facets[key] = facet.regexps
            else:
                facets[key] = facet.value
        xsd_type = simple_base(xsd_type)
    return facets


def simple_base(xsd_type):
    """The simple type a simple type derives from, through the content of a complex type with simple content."""
    base = xsd_type.base_type
    return base.content if base.is_complex() else base


def plain(value):
    """A facet value as a number when it is one, otherwise as its XSD lexical form."""
    if value is None or isinstance(value, (bool, int)):
        return value
    if isinstance(value, (Decimal, float)):
        return int(value) if value == int(value) else float(value)
    return str(value)


def documentation(component) -> str | None:
    if component is None or component.annotation is None:
        return None
    # Without the indentation of the schema, which is not part of the text
    texts = [inspect.cleandoc(doc.text) for doc in component.annotation.documentation if doc.text]
    return "\n".join(texts) or None
