import logging
from pathlib import Path

import pytest
import xmlschema
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract
from datacontract.export.xsd_exporter import to_xsd

CONTRACT = """
apiVersion: v3.2.0
kind: DataContract
id: shop
name: Shop
version: 1.0.0
status: active
schema:
  - name: orders
    physicalName: order
    description: An order placed in the webshop.
    customProperties:
      - property: xmlNamespace
        value: urn:example:shop
    properties:
      - name: order_id
        logicalType: string
        description: Unique identifier of the order.
        required: true
        logicalTypeOptions:
          pattern: ^ORD-[0-9]{4}$
      - name: placed_at
        logicalType: timestamp
        required: true
      - name: delivery_date
        logicalType: date
      - name: delivery_window
        logicalType: time
      - name: total
        logicalType: number
        required: true
        logicalTypeOptions:
          minimum: 0
          exclusiveMinimum: -1
          exclusiveMaximum: 100000
        customProperties:
          - property: precision
            value: 10
          - property: scale
            value: 2
      - name: status
        logicalType: string
        required: true
        enum:
          - value: pending
          - value: shipped
      - name: gift
        logicalType: boolean
      - name: priority
        logicalType: integer
        physicalType: unsignedByte
      - name: customer
        logicalType: object
        required: true
        properties:
          - name: name
            logicalType: string
            required: true
            logicalTypeOptions:
              minLength: 1
              maxLength: 100
          - name: id
            logicalType: string
            required: true
            customProperties:
              - property: xmlNode
                value: attribute
      - name: lines
        logicalType: array
        required: true
        logicalTypeOptions:
          minItems: 1
          maxItems: 50
        items:
          logicalType: object
          properties:
            - name: sku
              logicalType: string
              required: true
            - name: price
              logicalType: object
              required: true
              properties:
                - name: value
                  logicalType: number
                  logicalTypeOptions:
                    minimum: 0
                  customProperties:
                    - property: xmlNode
                      value: text
                - name: currency
                  logicalType: string
                  required: true
                  customProperties:
                    - property: xmlNode
                      value: attribute
      - name: tags
        logicalType: array
        items:
          logicalType: string
      - name: attributes
        logicalType: map
        map:
          key:
            logicalType: string
          value:
            logicalType: integer
      - name: extension
        logicalType: object
  - name: returns
    properties:
      - name: order_id
        logicalType: string
        required: true
"""


@pytest.fixture
def exported() -> str:
    return to_xsd(DataContract(data_contract_str=CONTRACT).get_data_contract())


@pytest.fixture
def schema(exported) -> xmlschema.XMLSchema:
    return xmlschema.XMLSchema(exported)


def valid_order(**replace) -> str:
    parts = {
        "order_id": "<order_id>ORD-0001</order_id>",
        "placed_at": "<placed_at>2026-09-01T10:15:00</placed_at>",
        "total": "<total>149.90</total>",
        "status": "<status>shipped</status>",
        "customer": '<customer id="C-1"><name>Ada</name></customer>',
        "lines": '<lines><sku>ABC</sku><price currency="EUR">49.95</price></lines>',
        "tags": "",
        "attributes": "<attributes><entry><key>size</key><value>42</value></entry></attributes>",
    } | replace
    return f'<order xmlns="urn:example:shop">{"".join(parts.values())}</order>'


def test_cli(tmp_path: Path):
    contract = tmp_path / "datacontract.yaml"
    contract.write_text(CONTRACT)

    result = CliRunner().invoke(app, ["export", "xsd", str(contract), "--output", str(tmp_path / "schema.xsd")])

    assert result.exit_code == 0
    xmlschema.XMLSchema(str(tmp_path / "schema.xsd"))


def test_export_one_global_element_per_schema_in_the_target_namespace(schema):
    assert schema.target_namespace == "urn:example:shop"
    assert list(schema.elements) == ["order", "returns"]
    assert str(schema.elements["order"].annotation) == "An order placed in the webshop."


def test_export_selects_a_schema_by_name():
    exported = to_xsd(DataContract(data_contract_str=CONTRACT).get_data_contract(), "returns")

    assert list(xmlschema.XMLSchema(exported).elements) == ["returns"]


def test_export_types(schema):
    order = schema.elements["order"].type.content

    types = {e.local_name: e.type for e in order.iter_elements()}
    assert types["placed_at"].name.endswith("dateTime")
    assert types["delivery_date"].name.endswith("date")
    assert types["delivery_window"].name.endswith("time")
    assert types["gift"].name.endswith("boolean")
    assert types["priority"].name.endswith("unsignedByte")  # the physicalType, a builtin XSD integer type
    assert types["total"].base_type.name.endswith("decimal")
    assert types["extension"].name.endswith("anyType")


def test_export_occurrences(schema):
    occurs = {e.local_name: (e.min_occurs, e.max_occurs) for e in schema.elements["order"].type.content.iter_elements()}

    assert occurs["order_id"] == (1, 1)
    assert occurs["delivery_date"] == (0, 1)
    assert occurs["lines"] == (1, 50)
    assert occurs["tags"] == (0, None)


def test_export_facets(schema):
    elements = {e.local_name: e for e in schema.elements["order"].type.content.iter_elements()}

    total = elements["total"].type
    # minimum 0 is tighter than exclusiveMinimum -1, and XSD allows only one of them
    assert total.min_value == 0 and total.max_value == 100000
    assert (total.facets[f"{XS}totalDigits"].value, total.facets[f"{XS}fractionDigits"].value) == (10, 2)
    assert elements["status"].type.enumeration == ["pending", "shipped"]
    # XSD patterns always match the whole value, so the anchors go
    assert elements["order_id"].type.patterns.regexps == ["ORD-[0-9]{4}"]
    assert elements["order_id"].annotation is not None


def test_export_attributes_and_text(schema):
    elements = {e.local_name: e for e in schema.elements["order"].type.content.iter_elements()}

    customer = elements["customer"].type
    assert list(customer.attributes) == ["id"] and customer.attributes["id"].use == "required"
    price = next(e for e in elements["lines"].type.content.iter_elements() if e.local_name == "price").type
    assert price.has_simple_content() and list(price.attributes) == ["currency"]
    # the text keeps its constraint through a named type
    assert price.content.min_value == 0


@pytest.mark.parametrize(
    "replace, valid",
    [
        ({}, True),
        ({"order_id": "<order_id>ORD-1</order_id>"}, False),
        ({"status": "<status>lost</status>"}, False),
        ({"total": "<total>-5</total>"}, False),
        ({"total": "<total>1.999</total>"}, False),
        ({"customer": "<customer><name>Ada</name></customer>"}, False),
        ({"lines": ""}, False),
        ({"lines": '<lines><sku>ABC</sku><price currency="EUR">-1</price></lines>'}, False),
        ({"placed_at": "<placed_at>yesterday</placed_at>"}, False),
        ({"attributes": "<attributes><entry><key>size</key><value>big</value></entry></attributes>"}, False),
        ({"tags": "<tags>a</tags><tags>b</tags>"}, True),
    ],
)
def test_exported_schema_validates_documents(schema, replace, valid):
    assert schema.is_valid(valid_order(**replace)) == valid


def test_export_invalid_xml_names(caplog):
    contract = """
apiVersion: v3.2.0
kind: DataContract
id: names
version: 1.0.0
status: active
schema:
  - name: 1st table
    properties:
      - name: first name
        logicalType: string
"""
    with caplog.at_level(logging.WARNING):
        exported = to_xsd(DataContract(data_contract_str=contract).get_data_contract())

    schema = xmlschema.XMLSchema(exported)
    assert list(schema.elements) == ["_1st_table"]
    assert [e.local_name for e in schema.elements["_1st_table"].type.content.iter_elements()] == ["first_name"]
    assert "first name is not a valid XML name" in caplog.text


def test_export_without_a_namespace():
    contract = CONTRACT.replace(
        "    customProperties:\n      - property: xmlNamespace\n        value: urn:example:shop\n", ""
    )

    schema = xmlschema.XMLSchema(to_xsd(DataContract(data_contract_str=contract).get_data_contract()))

    assert schema.target_namespace == ""
    assert schema.is_valid(valid_order().replace(' xmlns="urn:example:shop"', ""))


XS = "{http://www.w3.org/2001/XMLSchema}"


# A contract as most people write it: no XML custom properties, SQL physical types
PLAIN_CONTRACT = """
apiVersion: v3.2.0
kind: DataContract
id: plain
version: 1.0.0
status: active
schema:
  - name: customers
    physicalType: table
    description: One row per customer.
    properties:
      - name: customer_id
        logicalType: string
        physicalType: VARCHAR(36)
        required: true
        primaryKey: true
      - name: email
        logicalType: string
        physicalType: TEXT
        logicalTypeOptions:
          format: email
          maxLength: 320
      - name: signed_up_at
        logicalType: timestamp
        physicalType: TIMESTAMP_TZ
        required: true
      - name: birthday
        logicalType: date
        physicalType: DATE
      - name: lifetime_value
        logicalType: number
        physicalType: NUMERIC(12,2)
        logicalTypeOptions:
          minimum: 0
      - name: orders
        logicalType: integer
        physicalType: BIGINT
      - name: active
        logicalType: boolean
        physicalType: BOOLEAN
        required: true
      - name: address
        logicalType: object
        properties:
          - name: street
            logicalType: string
          - name: city
            logicalType: string
            required: true
      - name: phone_numbers
        logicalType: array
        items:
          logicalType: string
          logicalTypeOptions:
            pattern: ^\\+[0-9 ]+$
      - name: segment
        logicalType: string
        enum:
          - value: retail
          - value: business
"""


def test_export_the_example_orders_contract():
    exported = to_xsd(DataContract(data_contract_file="../examples/orders/orders.odcs.yaml").get_data_contract())

    schema = xmlschema.XMLSchema(exported)
    assert schema.target_namespace == ""
    assert list(schema.elements) == ["orders", "line_items"]
    orders = {e.local_name: e for e in schema.elements["orders"].type.content.iter_elements()}
    assert list(orders) == ["order_id", "order_timestamp", "customer_id", "order_total", "status"]
    # SQL physical types are not XSD types, so the logical types decide
    assert [orders[name].type.local_name for name in orders] == ["string", "dateTime", "string", "integer", "string"]
    assert all(e.min_occurs == 1 for e in orders.values())
    assert str(orders["order_id"].annotation) == "Unique identifier of the order."
    assert not schema.elements["orders"].type.attributes


def test_export_a_plain_contract_has_only_elements(schema_plain):
    customers = schema_plain.elements["customers"]

    assert schema_plain.target_namespace == ""
    assert not customers.type.attributes
    elements = {e.local_name: e for e in customers.type.content.iter_elements()}
    assert list(elements) == [
        "customer_id", "email", "signed_up_at", "birthday", "lifetime_value", "orders", "active", "address",
        "phone_numbers", "segment",
    ]  # fmt: skip
    assert elements["customer_id"].type.local_name == "string"
    assert elements["signed_up_at"].type.local_name == "dateTime"
    assert elements["birthday"].type.local_name == "date"
    assert elements["orders"].type.local_name == "integer"
    assert elements["active"].type.local_name == "boolean"
    assert elements["lifetime_value"].type.base_type.local_name == "decimal"
    assert elements["email"].type.max_length == 320
    assert (elements["phone_numbers"].min_occurs, elements["phone_numbers"].max_occurs) == (0, None)
    assert elements["phone_numbers"].type.patterns.regexps == ["\\+[0-9 ]+"]
    assert [e.local_name for e in elements["address"].type.content.iter_elements()] == ["street", "city"]


@pytest.fixture
def schema_plain() -> xmlschema.XMLSchema:
    return xmlschema.XMLSchema(to_xsd(DataContract(data_contract_str=PLAIN_CONTRACT).get_data_contract()))


PLAIN_DOCUMENT = (
    "<customers>"
    "<customer_id>C-1</customer_id>"
    "<email>ada@example.com</email>"
    "<signed_up_at>2026-01-01T09:00:00Z</signed_up_at>"
    "<lifetime_value>1200.50</lifetime_value>"
    "<active>true</active>"
    "<address><city>London</city></address>"
    "<phone_numbers>+44 20 7946 0000</phone_numbers>"
    "<phone_numbers>+44 20 7946 0001</phone_numbers>"
    "<segment>retail</segment>"
    "</customers>"
)


@pytest.mark.parametrize(
    "old, new, valid",
    [
        ("", "", True),
        ("<customer_id>C-1</customer_id>", "", False),
        ("<active>true</active>", "<active>maybe</active>", False),
        ("<lifetime_value>1200.50</lifetime_value>", "<lifetime_value>-1</lifetime_value>", False),
        ("<address><city>London</city></address>", "<address><street>Baker St</street></address>", False),
        ("<segment>retail</segment>", "<segment>vip</segment>", False),
        ("<phone_numbers>+44 20 7946 0000</phone_numbers>", "<phone_numbers>0800</phone_numbers>", False),
        ("<signed_up_at>2026-01-01T09:00:00Z</signed_up_at>", "<signed_up_at>2026-01-01</signed_up_at>", False),
        # elements in another order than the contract's properties
        ("<customer_id>C-1</customer_id><email>ada@example.com</email>",
         "<email>ada@example.com</email><customer_id>C-1</customer_id>", False),
    ],
)  # fmt: skip
def test_a_plain_contract_validates_documents(schema_plain, old, new, valid):
    assert schema_plain.is_valid(PLAIN_DOCUMENT.replace(old, new) if old else PLAIN_DOCUMENT) == valid


def test_export_leaves_out_the_range_its_integer_type_already_has():
    contract = """
apiVersion: v3.2.0
kind: DataContract
id: bounds
version: 1.0.0
status: active
schema:
  - name: counter
    properties:
      - name: count
        logicalType: integer
        physicalType: unsignedInt
        required: true
        logicalTypeOptions:
          minimum: 0
          maximum: 4294967295
      - name: score
        logicalType: integer
        physicalType: unsignedByte
        required: true
        logicalTypeOptions:
          minimum: 1
          maximum: 255
"""
    schema = xmlschema.XMLSchema(to_xsd(DataContract(data_contract_str=contract).get_data_contract()))

    count, score = schema.elements["counter"].type.content.iter_elements()
    assert count.type.name.endswith("unsignedInt")  # the builtin itself, no restriction
    assert score.type.base_type.name.endswith("unsignedByte") and score.type.min_value == 1
    assert f"{XS}maxInclusive" not in score.type.facets


@pytest.mark.parametrize(
    "pattern, exported",
    [
        ("^ORD-[0-9]{4}$", "ORD-[0-9]{4}"),
        ("^(ORD-[0-9]{4})$", "ORD-[0-9]{4}"),  # as the import writes it
        ("^(a|b)$", "a|b"),
        ("^(a)|(b)$", "(a)|(b)"),  # the first group closes early, so the parentheses stay
        ("ORD", ".*(ORD).*"),
        ("^ORD", "(ORD).*"),
        ("ORD$", ".*(ORD)"),
        ("price\\$", ".*(price\\$).*"),  # an escaped dollar is not an anchor
    ],
)
def test_export_patterns_match_where_the_contract_matches(pattern, exported):
    """A contract pattern matches anywhere unless anchored; an XSD pattern always matches the whole value."""
    contract = f"""
apiVersion: v3.2.0
kind: DataContract
id: patterns
version: 1.0.0
status: active
schema:
  - name: code
    properties:
      - name: value
        logicalType: string
        required: true
        logicalTypeOptions:
          pattern: '{pattern}'
"""
    schema = xmlschema.XMLSchema(to_xsd(DataContract(data_contract_str=contract).get_data_contract()))

    (value,) = schema.elements["code"].type.content.iter_elements()
    assert value.type.patterns.regexps == [exported]


@pytest.mark.parametrize("text, valid", [("ORD", True), ("xORDx", True), ("ord", False)])
def test_an_unanchored_pattern_accepts_what_the_check_accepts(text, valid):
    contract = """
apiVersion: v3.2.0
kind: DataContract
id: patterns
version: 1.0.0
status: active
schema:
  - name: code
    properties:
      - name: value
        logicalType: string
        required: true
        logicalTypeOptions:
          pattern: ORD
"""
    schema = xmlschema.XMLSchema(to_xsd(DataContract(data_contract_str=contract).get_data_contract()))

    assert schema.is_valid(f"<code><value>{text}</value></code>") == valid


@pytest.mark.parametrize(
    "logical_type, odcs_format, physical_type, exported",
    [
        ("integer", "i16", "SMALLINT", "short"),
        ("integer", "u32", None, "unsignedInt"),
        ("number", "f32", "REAL", "float"),
        ("number", "f64", None, "double"),
        ("integer", "i64", "int", "int"),  # an XSD physicalType wins
    ],
)
def test_export_the_odcs_format_as_the_sized_xsd_type(logical_type, odcs_format, physical_type, exported):
    physical = f"\n        physicalType: {physical_type}" if physical_type else ""
    contract = f"""
apiVersion: v3.2.0
kind: DataContract
id: sizes
version: 1.0.0
status: active
schema:
  - name: measure
    properties:
      - name: value
        logicalType: {logical_type}{physical}
        required: true
        logicalTypeOptions:
          format: {odcs_format}
"""
    schema = xmlschema.XMLSchema(to_xsd(DataContract(data_contract_str=contract).get_data_contract()))

    (value,) = schema.elements["measure"].type.content.iter_elements()
    assert value.type.local_name == exported


def test_export_an_attribute_with_an_at_prefix_without_it():
    contract = """
apiVersion: v3.2.0
kind: DataContract
id: names
version: 1.0.0
status: active
schema:
  - name: order
    properties:
      - name: id
        logicalType: string
        required: true
      - name: "@id"
        logicalType: integer
        customProperties:
          - property: xmlNode
            value: attribute
"""
    schema = xmlschema.XMLSchema(to_xsd(DataContract(data_contract_str=contract).get_data_contract()))

    order = schema.elements["order"].type
    assert [e.local_name for e in order.content.iter_elements()] == ["id"]
    assert list(order.attributes) == ["id"]


def test_export_an_element_in_no_namespace_as_unqualified():
    contract = """
apiVersion: v3.2.0
kind: DataContract
id: forms
version: 1.0.0
status: active
schema:
  - name: order
    customProperties:
      - property: xmlNamespace
        value: urn:x
    properties:
      - name: id
        logicalType: string
        required: true
        customProperties:
          - property: xmlNamespace
            value: ""
      - name: note
        logicalType: string
        required: true
"""
    schema = xmlschema.XMLSchema(to_xsd(DataContract(data_contract_str=contract).get_data_contract()))

    assert schema.is_valid('<o:order xmlns:o="urn:x"><id>1</id><o:note>n</o:note></o:order>')
    assert not schema.is_valid('<o:order xmlns:o="urn:x"><o:id>1</o:id><o:note>n</o:note></o:order>')
