import logging
from pathlib import Path

import pytest
import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract
from datacontract.model.exceptions import DataContractException


def import_xsd(tmp_path: Path, body: str, name: str = "schema.xsd"):
    source = tmp_path / name
    source.write_text(f'<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">{body}</xs:schema>')
    return DataContract.import_from_source("xsd", str(source))


def properties(prop) -> dict:
    """The properties of a schema or object by name."""
    return {p.name: p for p in prop.properties}


def custom(prop, name):
    return next((c.value for c in prop.customProperties or [] if c.property == name), None)


@pytest.mark.parametrize("fixture", ["orders", "purchase-order"])
def test_cli(tmp_path: Path, fixture):
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["import", "xsd", "--source", f"fixtures/import/xsd/{fixture}.xsd", "--output", tmp_path / "datacontract.yaml"],
    )
    assert result.exit_code == 0

    with open(tmp_path / "datacontract.yaml") as file:
        actual = yaml.safe_load(file)
    with open(f"fixtures/import/xsd/{fixture}.odcs.yaml") as file:
        expected = yaml.safe_load(file)
    assert actual == expected


def test_purchase_order_skips_remote_imports(caplog):
    with caplog.at_level(logging.WARNING):
        DataContract.import_from_source("xsd", "fixtures/import/xsd/purchase-order.xsd")

    assert "https://example.com/remote.xsd" in caplog.text


def test_purchase_order():
    """The W3C primer constructs, checked one by one rather than only as a whole file."""
    result = DataContract.import_from_source("xsd", "fixtures/import/xsd/purchase-order.xsd")
    (order,) = result.schema_
    props = properties(order)

    assert order.description == "A purchase order with its items."
    assert custom(order, "xmlNamespace") == "urn:example:po"
    # an extension adds its content and attributes after the base type's, imported from another namespace
    assert list(properties(props["shipTo"])) == [
        "name", "street", "city", "state", "zip", "latitude", "longitude", "country"
    ]  # fmt: skip
    # a restriction keeps only the content it restates, but every attribute
    assert list(properties(props["returnTo"])) == ["name", "city", "latitude", "longitude"]
    assert props["shipTo"].required and not props["billTo"].required  # billTo is nillable
    assert props["comment"].required is None  # minOccurs="0" on a ref
    # a choice inside a group makes both alternatives optional
    assert props["creditCard"].required is None and props["invoice"].required is None
    # an optional sequence makes its elements optional
    assert props["approvedBy"].required is None and props["approvedAt"].logicalType == "timestamp"
    # two patterns on one restriction are alternatives
    card = properties(props["creditCard"])
    assert card["number"].logicalTypeOptions["pattern"] == r"(\d{16})|(\d{4}-\d{4}-\d{4}-\d{4})"
    assert card["expires"].physicalType == "gYearMonth" and card["expires"].logicalType == "string"
    # the facets of an inline base type are merged into those of the type restricting it
    channel = properties(props["metadata"])["channel"]
    assert [e.value for e in channel.enum] == ["web", "phone", "store"]
    assert channel.logicalTypeOptions == {"maxLength": 10}
    assert channel.physicalType == "token"
    # an attribute keeps its integer enumeration as numbers
    assert [e.value for e in props["priority"].enum] == [1, 2, 3]
    assert props["orderDate"].required and custom(props["orderDate"], "xmlNode") == "attribute"
    # a union is a string, with its member types in physicalType
    assert props["reference"].logicalType == "string"
    assert props["reference"].physicalType == "date|string|integer"


def test_purchase_order_items():
    result = DataContract.import_from_source("xsd", "fixtures/import/xsd/purchase-order.xsd")
    items = properties(properties(result.schema_[0])["items"])["item"]

    assert items.logicalType == "array" and items.required is None  # minOccurs="0"
    item = properties(items.items)
    assert item["quantity"].physicalType == "positiveInteger"
    assert item["quantity"].logicalTypeOptions == {"exclusiveMaximum": 100}
    # a simpleContent restriction keeps the attributes of the type it restricts
    price = properties(item["USPrice"])
    assert list(price) == ["value", "currency"]
    assert custom(price["value"], "xmlNode") == "text"
    assert price["value"].logicalTypeOptions == {"maximum": 99999.99}
    assert price["currency"].required
    # a prohibited attribute is not imported
    assert "legacyCode" not in item
    # Items contains itself through bundle, which stops at the repetition
    assert item["bundle"].logicalType == "object" and item["bundle"].properties is None
    assert item["partNum"].logicalTypeOptions == {"pattern": r"\d{3}-[A-Z]{2}"}


def test_import_one_schema_per_root_element(tmp_path: Path):
    result = import_xsd(
        tmp_path,
        """
        <xs:element name="id" type="xs:long"/>
        <xs:element name="customer">
          <xs:complexType><xs:sequence><xs:element ref="id"/></xs:sequence></xs:complexType>
        </xs:element>
        <xs:element name="product">
          <xs:complexType><xs:attribute name="price" type="xs:double"/></xs:complexType>
        </xs:element>
        """,
        name="shop.xsd",
    )

    assert result.name == "shop"
    assert [(s.name, [(p.name, p.logicalType) for p in s.properties]) for s in result.schema_] == [
        ("customer", [("id", "integer")]),
        ("product", [("price", "number")]),
    ]


def test_import_elements_that_reference_each_other_are_all_roots(tmp_path: Path):
    result = import_xsd(
        tmp_path,
        """
        <xs:element name="a"><xs:complexType><xs:sequence><xs:element ref="b" minOccurs="0"/></xs:sequence></xs:complexType></xs:element>
        <xs:element name="b"><xs:complexType><xs:sequence><xs:element ref="a" minOccurs="0"/></xs:sequence></xs:complexType></xs:element>
        """,
    )

    assert [s.name for s in result.schema_] == ["a", "b"]


def test_import_a_recursive_element_stops_at_its_repetition(tmp_path: Path):
    result = import_xsd(
        tmp_path,
        """
        <xs:element name="tree"><xs:complexType><xs:sequence><xs:element ref="node"/></xs:sequence></xs:complexType></xs:element>
        <xs:element name="node">
          <xs:complexType><xs:sequence>
            <xs:element name="label" type="xs:string"/>
            <xs:element ref="node" minOccurs="0" maxOccurs="unbounded"/>
          </xs:sequence></xs:complexType>
        </xs:element>
        """,
    )

    node = properties(result.schema_[0])["node"]
    children = properties(node)["node"]
    assert children.logicalType == "array"
    assert children.items.logicalType == "object" and children.items.properties is None


def test_import_a_simple_root_element(tmp_path: Path):
    result = import_xsd(tmp_path, '<xs:element name="greeting" type="xs:string"/>')

    assert [(p.name, p.logicalType) for p in result.schema_[0].properties] == [("greeting", "string")]


@pytest.mark.parametrize(
    "xsd_type, logical_type",
    [
        ("string", "string"),
        ("normalizedString", "string"),
        ("anyURI", "string"),
        ("base64Binary", "string"),
        ("duration", "string"),
        ("boolean", "boolean"),
        ("int", "integer"),
        ("long", "integer"),
        ("unsignedByte", "integer"),
        ("nonNegativeInteger", "integer"),
        ("decimal", "number"),
        ("float", "number"),
        ("double", "number"),
        ("date", "date"),
        ("dateTime", "timestamp"),
        ("time", "time"),
        ("gYear", "string"),
    ],
)
def test_import_builtin_types(tmp_path: Path, xsd_type, logical_type):
    result = import_xsd(tmp_path, f'<xs:element name="value" type="xs:{xsd_type}"/>')

    (prop,) = result.schema_[0].properties
    assert (prop.logicalType, prop.physicalType) == (logical_type, xsd_type)


@pytest.mark.parametrize(
    "base, facets, options",
    [
        ("string", '<xs:length value="5"/>', {"minLength": 5, "maxLength": 5}),
        ("string", '<xs:minLength value="1"/><xs:maxLength value="9"/>', {"minLength": 1, "maxLength": 9}),
        ("decimal", '<xs:minExclusive value="0.5"/><xs:maxExclusive value="10"/>',
         {"exclusiveMinimum": 0.5, "exclusiveMaximum": 10}),
        ("integer", '<xs:minInclusive value="-3"/><xs:maxInclusive value="3"/>', {"minimum": -3, "maximum": 3}),
        ("date", '<xs:minInclusive value="2020-01-01"/>', {"minimum": "2020-01-01"}),
        ("string", '<xs:pattern value="[a-z]+"/>', {"pattern": "[a-z]+"}),
    ],
)  # fmt: skip
def test_import_facets(tmp_path: Path, base, facets, options):
    result = import_xsd(
        tmp_path,
        f'<xs:element name="value"><xs:simpleType><xs:restriction base="xs:{base}">{facets}</xs:restriction></xs:simpleType></xs:element>',
    )

    assert result.schema_[0].properties[0].logicalTypeOptions == options


def test_import_decimal_digits_as_precision_and_scale(tmp_path: Path):
    result = import_xsd(
        tmp_path,
        """<xs:element name="amount"><xs:simpleType><xs:restriction base="xs:decimal">
             <xs:totalDigits value="12"/><xs:fractionDigits value="3"/>
           </xs:restriction></xs:simpleType></xs:element>""",
    )

    prop = result.schema_[0].properties[0]
    assert (custom(prop, "precision"), custom(prop, "scale")) == (12, 3)


def test_import_occurrences_as_array_bounds(tmp_path: Path):
    result = import_xsd(
        tmp_path,
        """<xs:element name="team"><xs:complexType><xs:sequence>
             <xs:element name="member" type="xs:string" minOccurs="2" maxOccurs="5"/>
             <xs:element name="coach" type="xs:string" minOccurs="0" maxOccurs="unbounded"/>
           </xs:sequence></xs:complexType></xs:element>""",
    )

    member, coach = result.schema_[0].properties
    assert (member.required, member.logicalTypeOptions) == (True, {"minItems": 2, "maxItems": 5})
    assert (coach.required, coach.logicalTypeOptions) == (None, None)


def test_import_list_as_string(tmp_path: Path):
    result = import_xsd(
        tmp_path,
        '<xs:element name="tags"><xs:simpleType><xs:list itemType="xs:token"/></xs:simpleType></xs:element>',
    )

    prop = result.schema_[0].properties[0]
    assert (prop.logicalType, prop.physicalType) == ("string", "list")


def test_import_documentation_of_elements_and_attributes(tmp_path: Path):
    result = import_xsd(
        tmp_path,
        """<xs:element name="order">
             <xs:annotation><xs:documentation>An order.</xs:documentation></xs:annotation>
             <xs:complexType>
               <xs:sequence>
                 <xs:element name="id" type="xs:string">
                   <xs:annotation><xs:documentation>The
                     identifier.</xs:documentation></xs:annotation>
                 </xs:element>
               </xs:sequence>
               <xs:attribute name="source" type="xs:string">
                 <xs:annotation><xs:documentation>Where it came from.</xs:documentation></xs:annotation>
               </xs:attribute>
             </xs:complexType>
           </xs:element>""",
    )

    order = result.schema_[0]
    assert order.description == "An order."
    # line breaks stay, the indentation of the schema goes
    assert [p.description for p in order.properties] == ["The\nidentifier.", "Where it came from."]


def test_import_without_a_target_namespace_has_no_xml_namespace(tmp_path: Path):
    result = import_xsd(tmp_path, '<xs:element name="value" type="xs:string"/>')

    assert result.schema_[0].customProperties is None


def test_import_an_unresolved_type_as_any_object(tmp_path: Path, caplog):
    # Schemas often reference types of remote imports, which are not loaded
    with caplog.at_level(logging.WARNING):
        result = import_xsd(tmp_path, '<xs:element name="order" type="Missing"/>')

    assert "Missing" in caplog.text
    assert result.schema_[0].name == "order"


def test_import_a_document_that_is_not_an_xml_schema(tmp_path: Path):
    source = tmp_path / "data.xml"
    source.write_text("<order><id>1</id></order>")

    with pytest.raises(DataContractException, match="declares no global element"):
        DataContract.import_from_source("xsd", str(source))


def test_import_malformed_xml(tmp_path: Path):
    source = tmp_path / "broken.xsd"
    source.write_text('<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema"><xs:element name="a">')

    with pytest.raises(DataContractException, match="Failed to parse XML Schema"):
        DataContract.import_from_source("xsd", str(source))


def test_import_a_missing_file():
    with pytest.raises(DataContractException, match="Failed to parse XML Schema"):
        DataContract.import_from_source("xsd", "fixtures/import/xsd/missing.xsd")
