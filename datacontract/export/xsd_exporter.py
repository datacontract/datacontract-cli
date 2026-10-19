import logging
import re
from xml.etree import ElementTree

from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, SchemaProperty

from datacontract.export.exporter import Exporter
from datacontract.imports.xsd_importer import FORMATS, INTEGER_BOUNDS, LOGICAL_TYPES
from datacontract.model.enum_values import get_enum_values
from datacontract.model.map_type import get_map_key, get_map_value, is_map

logger = logging.getLogger(__name__)

XS_NAMESPACE = "http://www.w3.org/2001/XMLSchema"
XS = f"{{{XS_NAMESPACE}}}"

# The XSD type of a logical type, unless the physicalType already names a builtin of that logical type
XSD_TYPES = {
    "string": "string",
    "integer": "integer",
    "number": "decimal",
    "boolean": "boolean",
    "date": "date",
    "timestamp": "dateTime",
    "time": "time",
}

# Builtin XSD types imported as logicalType string
STRING_TYPES = {
    "string", "normalizedString", "token", "language", "Name", "NCName", "NMTOKEN", "NMTOKENS", "ID", "IDREF",
    "IDREFS", "ENTITY", "ENTITIES", "QName", "NOTATION", "anyURI", "base64Binary", "hexBinary", "duration",
    "dayTimeDuration", "yearMonthDuration", "gYear", "gYearMonth", "gMonth", "gMonthDay", "gDay",
}  # fmt: skip

# The XSD type of an ODCS integer or number format
SIZED_TYPES = {odcs_format: xsd for xsd, odcs_format in FORMATS.items()}

# logicalTypeOptions and the facets they become
FACETS = {
    "minLength": "minLength",
    "maxLength": "maxLength",
    "minimum": "minInclusive",
    "exclusiveMinimum": "minExclusive",
    "maximum": "maxInclusive",
    "exclusiveMaximum": "maxExclusive",
}


class XsdExporter(Exporter):
    def export(self, data_contract, schema_name, server, sql_server_type, export_args) -> str:
        return to_xsd(data_contract, schema_name)


def to_xsd(data_contract: OpenDataContractStandard, schema_name: str = "all") -> str:
    """An XML Schema with one global element per schema of the data contract."""
    if not data_contract.schema_:
        raise RuntimeError("Export to xsd requires a schema in the data contract.")
    schema_objects = [s for s in data_contract.schema_ if schema_name in ("all", s.name)]
    if not schema_objects:
        names = ", ".join(s.name for s in data_contract.schema_)
        raise RuntimeError(f"The data contract has no schema named {schema_name}, only {names}.")

    namespaces = list(dict.fromkeys(custom_property(s, "xmlNamespace") for s in schema_objects))
    if len(namespaces) > 1:
        logger.warning(f"An XML Schema has one target namespace, using {namespaces[0]} of {namespaces}")
    namespace = namespaces[0]

    ElementTree.register_namespace("xs", XS_NAMESPACE)
    root = ElementTree.Element(f"{XS}schema", {"elementFormDefault": "qualified"})
    if namespace:
        # The default namespace resolves references to the named types below
        root.set("targetNamespace", namespace)
        root.set("xmlns", namespace)
    writer = XsdWriter(namespace)
    root.extend([writer.schema_element(schema_object) for schema_object in schema_objects])
    root.extend(writer.types.values())

    ElementTree.indent(root)
    return '<?xml version="1.0" encoding="UTF-8"?>\n' + ElementTree.tostring(root, encoding="unicode") + "\n"


class XsdWriter:
    """Writes elements and collects the named simple types they need."""

    def __init__(self, namespace: str | None):
        self.types: dict[str, ElementTree.Element] = {}
        self.namespace = namespace or ""

    def schema_element(self, schema_object: SchemaObject) -> ElementTree.Element:
        name = xml_name(schema_object.physicalName or schema_object.name)
        element = ElementTree.Element(f"{XS}element", {"name": name})
        annotate(element, schema_object.description)
        element.append(self.complex_type(name, schema_object.properties or []))
        return element

    def property_node(self, prop: SchemaProperty) -> ElementTree.Element:
        """The xs:attribute or xs:element of a property; an array becomes an element that repeats."""
        if xml_node(prop) == "attribute":
            # the import names an attribute like another property with an @ prefix
            name = xml_name((prop.physicalName or prop.name).removeprefix("@"))
            node = ElementTree.Element(f"{XS}attribute", {"name": name})
            namespace = custom_property(prop, "xmlNamespace")
            if namespace and namespace == self.namespace:
                node.set("form", "qualified")
            elif namespace:
                logger.warning(f"Attribute {name} is in namespace {namespace}, which needs a schema of its own")
            if prop.required:
                node.set("use", "required")
            annotate(node, prop.description)
            set_simple_type(node, prop)
            return node

        name = xml_name(prop.physicalName or prop.name)
        node = ElementTree.Element(f"{XS}element", {"name": name})
        namespace = custom_property(prop, "xmlNamespace")
        if namespace == "" and self.namespace:
            # a local element in no namespace, such as one from a schema without elementFormDefault
            node.set("form", "unqualified")
        elif namespace and namespace != self.namespace:
            logger.warning(f"Element {name} is in namespace {namespace}, which needs a schema of its own")
        value = prop
        if prop.logicalType == "array":
            value = prop.items or SchemaProperty(name=name, logicalType="string")
            min_items = option(prop, "minItems")
            min_occurs = min_items if min_items is not None else 1 if prop.required else 0
            if min_occurs != 1:
                node.set("minOccurs", str(min_occurs))
            node.set("maxOccurs", str(option(prop, "maxItems") or "unbounded"))
        elif not prop.required:
            node.set("minOccurs", "0")
        annotate(node, prop.description)

        if value.logicalType == "object":
            if value.properties:
                node.append(self.complex_type(name, value.properties))
            else:
                node.set("type", "xs:anyType")
        elif is_map(value):
            node.append(self.map_type(value))
        else:
            set_simple_type(node, value)
        return node

    def complex_type(self, name: str, properties: list[SchemaProperty]) -> ElementTree.Element:
        """Child elements and attributes, or text and attributes when a property is the element's text."""
        node = ElementTree.Element(f"{XS}complexType")
        attributes = [self.property_node(p) for p in properties if xml_node(p) == "attribute"]
        text = next((p for p in properties if xml_node(p) == "text"), None)
        elements = [p for p in properties if xml_node(p) not in ("attribute", "text")]

        if text is not None and not elements:
            content = ElementTree.SubElement(node, f"{XS}simpleContent")
            ElementTree.SubElement(content, f"{XS}extension", {"base": self.text_type(name, text)}).extend(attributes)
            return node
        if text is not None:
            logger.warning(f"Element {name} has child elements, so it cannot have the text {text.name}")

        if elements:
            ElementTree.SubElement(node, f"{XS}sequence").extend(self.property_node(p) for p in elements)
        node.extend(attributes)
        return node

    def text_type(self, name: str, text: SchemaProperty) -> str:
        """The type of the text of an element with attributes; an extension needs a named type for constraints."""
        if not facets(text) and text.physicalType != "list":
            return xsd_type(text)
        type_name = f"{name}Value"
        suffix = 1
        while type_name in self.types:
            suffix += 1
            type_name = f"{name}Value{suffix}"
        holder = ElementTree.Element("holder")
        set_simple_type(holder, text)
        simple_type = holder.find(f"{XS}simpleType")
        simple_type.set("name", type_name)
        self.types[type_name] = simple_type
        return type_name

    def map_type(self, prop: SchemaProperty) -> ElementTree.Element:
        """A map as repeated entry elements with a key and a value."""
        key = get_map_key(prop) or SchemaProperty(logicalType="string")
        value = get_map_value(prop) or SchemaProperty(logicalType="string")
        entry = SchemaProperty(
            name="entry",
            logicalType="array",
            items=SchemaProperty(
                logicalType="object",
                properties=[
                    key.model_copy(update={"name": "key", "required": True}),
                    value.model_copy(update={"name": "value"}),
                ],
            ),
        )
        return self.complex_type("entry", [entry])


def set_simple_type(node: ElementTree.Element, prop: SchemaProperty):
    """The builtin type of the property, restricted to its constraints when it has any."""
    if prop.physicalType == "list":
        simple_type = ElementTree.SubElement(node, f"{XS}simpleType")
        ElementTree.SubElement(simple_type, f"{XS}list", {"itemType": "xs:string"})
        return
    members = (prop.physicalType or "").split("|")
    if len(members) > 1 and all(m in LOGICAL_TYPES or m in STRING_TYPES for m in members):
        simple_type = ElementTree.SubElement(node, f"{XS}simpleType")
        ElementTree.SubElement(simple_type, f"{XS}union", {"memberTypes": " ".join(f"xs:{m}" for m in members)})
        return
    restrictions = facets(prop)
    if not restrictions:
        node.set("type", xsd_type(prop))
        return
    restriction = ElementTree.SubElement(
        ElementTree.SubElement(node, f"{XS}simpleType"), f"{XS}restriction", {"base": xsd_type(prop)}
    )
    for facet, value in restrictions:
        ElementTree.SubElement(restriction, f"{XS}{facet}", {"value": lexical(value)})


def facets(prop: SchemaProperty) -> list[tuple[str, object]]:
    """The constraints of the property as the facets its XSD type allows."""
    logical_type = prop.logicalType or "string"
    result = [("enumeration", value) for value in get_enum_values(prop) or []]
    pattern = option(prop, "pattern")
    if pattern:
        result.append(("pattern", xsd_pattern(pattern)))
    bounds = {name: option(prop, name) for name in FACETS}
    if logical_type == "string":
        bounds = {name: value for name, value in bounds.items() if name in ("minLength", "maxLength")}
    else:
        bounds = {name: value for name, value in bounds.items() if name not in ("minLength", "maxLength")}
        # XSD allows one lower and one upper bound per type; the tighter one wins
        for inclusive, exclusive, tighter in (
            ("minimum", "exclusiveMinimum", max),
            ("maximum", "exclusiveMaximum", min),
        ):
            if bounds[inclusive] is not None and bounds[exclusive] is not None:
                loose = inclusive if tighter(bounds[inclusive], bounds[exclusive]) == bounds[exclusive] else exclusive
                bounds[loose] = None
        # The range of the builtin integer type itself needs no facet
        lowest, highest = INTEGER_BOUNDS.get(xsd_type(prop).removeprefix("xs:"), (None, None))
        if bounds["minimum"] is not None and bounds["minimum"] == lowest:
            bounds["minimum"] = None
        if bounds["maximum"] is not None and bounds["maximum"] == highest:
            bounds["maximum"] = None
    result += [(FACETS[name], value) for name, value in bounds.items() if value is not None]
    if logical_type in ("integer", "number") and xsd_type(prop) not in ("xs:float", "xs:double"):
        for custom, facet in (("precision", "totalDigits"), ("scale", "fractionDigits")):
            value = custom_property(prop, custom)
            if value is not None:
                result.append((facet, value))
    return result


def xsd_pattern(pattern: str) -> str:
    """The pattern as XSD reads it: XSD patterns match the whole value, contract patterns anywhere unless anchored."""
    start = pattern.startswith("^")
    end = pattern.endswith("$") and not pattern.endswith("\\$")
    body = pattern[1 if start else 0 : -1 if end else None]
    if start and end:
        # The import writes an XSD pattern as ^(pattern)$
        return unwrap(body)
    return f"{'' if start else '.*'}({body}){'' if end else '.*'}"


def unwrap(body: str) -> str:
    """The pattern without the parentheses around all of it, if it has them."""
    if not (body.startswith("(") and body.endswith(")")) or body.startswith("(?"):
        return body
    depth = 0
    in_class = False
    escaped = False
    for index, char in enumerate(body):
        if escaped:
            escaped = False
        elif char == "\\":
            escaped = True
        elif in_class:
            in_class = char != "]"
        elif char == "[":
            in_class = True
        elif char == "(":
            depth += 1
        elif char == ")":
            depth -= 1
            if depth == 0 and index < len(body) - 1:
                # the first group closes before the end, so the parentheses do not wrap it all
                return body
    return body[1:-1]


def xsd_type(prop: SchemaProperty) -> str:
    """The physicalType when it names a builtin XSD type of the same logical type, otherwise the logical mapping."""
    logical_type = prop.logicalType or "string"
    if prop.physicalType in LOGICAL_TYPES or prop.physicalType in STRING_TYPES:
        if LOGICAL_TYPES.get(prop.physicalType, "string") == logical_type:
            return f"xs:{prop.physicalType}"
    # the ODCS format of a sized integer or number, such as i32 or f64
    sized = SIZED_TYPES.get(option(prop, "format"))
    if sized and LOGICAL_TYPES[sized] == logical_type:
        return f"xs:{sized}"
    return f"xs:{XSD_TYPES.get(logical_type, 'string')}"


def annotate(node: ElementTree.Element, description: str | None):
    if description:
        annotation = ElementTree.SubElement(node, f"{XS}annotation")
        ElementTree.SubElement(annotation, f"{XS}documentation").text = description.strip()


def option(prop: SchemaProperty, name: str):
    return (prop.logicalTypeOptions or {}).get(name)


def custom_property(component, name: str):
    return next((c.value for c in component.customProperties or [] if c.property == name), None)


def xml_node(prop: SchemaProperty) -> str | None:
    return custom_property(prop, "xmlNode")


def xml_name(name: str) -> str:
    """The name as a valid XML name: other characters become underscores, and it starts with a letter or one."""
    valid = re.sub(r"[^\w.\-]", "_", name)
    if not re.match(r"[^\W\d]", valid):
        valid = f"_{valid}"
    if valid != name:
        logger.warning(f"{name} is not a valid XML name, exporting it as {valid}")
    return valid


def lexical(value) -> str:
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)
