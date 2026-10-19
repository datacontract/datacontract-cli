"""`datacontract test` against XML files, read through the webbed DuckDB community extension.

The contracts are the ones `datacontract import xsd` creates from the test schemas, so these tests
also show that an imported XML Schema is ready to test the documents it describes.
"""

import glob
from pathlib import Path

import duckdb
import pytest
import xmlschema
import yaml
from open_data_contract_standard.model import DataQuality, Server
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

CONTRACT = "fixtures/xml/datacontract.yaml"


def contract(path: str, **schema_changes) -> str:
    data = yaml.safe_load(Path(CONTRACT).read_text())
    data["servers"][0]["path"] = path
    data["schema"][0].update(schema_changes)
    return yaml.safe_dump(data)


def results(run) -> dict:
    return {check.name: check.result.value for check in run.checks}


def test_cli():
    result = CliRunner().invoke(app, ["test", CONTRACT])

    assert result.exit_code == 0, result.output


def test_the_imported_contract_holds_for_valid_documents():
    imported = DataContract.import_from_source("xsd", "fixtures/import/xsd/orders.xsd")
    imported.servers = DataContract(data_contract_file=CONTRACT).get_data_contract().servers

    run = DataContract(data_contract=imported).test()

    assert run.result == "passed", [(c.name, c.reason) for c in run.checks if c.result != "passed"]
    names = results(run)
    # nested objects, repeated elements, attributes, and the text of an element with attributes are all checked
    for name in [
        "Check that field customer.name has no missing values",
        "Check that field line_items.line_item[].sku matches regex pattern ^([A-Z]{3}-[0-9]{4})$",
        "Check that field line_items.line_item[].price.value has a minimum of 0",
        "Check that field line_items.line_item[].price.currency has a max length of 3",
        "Check that field version has no missing values",
        "Check that field status only contains enum values ['pending', 'shipped', 'delivered']",
    ]:
        assert names[name] == "passed", name


def test_every_violation_is_found_and_nothing_else():
    run = DataContract(data_contract_str=contract("fixtures/xml/invalid/*.xml")).test()

    failed = {name for name, result in results(run).items() if result != "passed"}
    assert failed == {
        "Check that field order_id has a max length of 36",
        "Check that field order_timestamp has no missing values",
        "Check that field order_total has a minimum of 0",
        "Check that field status only contains enum values ['pending', 'shipped', 'delivered']",
        "Check that field customer.name has no missing values",
        "Check that field line_items.line_item[].sku matches regex pattern ^([A-Z]{3}-[0-9]{4})$",
        "Check that field line_items.line_item[].quantity is not equal to 1000",
        "Check that field line_items.line_item[].price.value has a minimum of 0",
        "Check that field line_items.line_item[].price.currency has a max length of 3",
        "Check that field category.name has no missing values",
        "Check that field version has no missing values",
    }
    assert run.result == "failed"


def test_a_violation_counts_the_records_that_break_it():
    run = DataContract(data_contract_str=contract("fixtures/xml/invalid/*.xml")).test()

    check = next(
        c
        for c in run.checks
        if c.name == "Check that field status only contains enum values ['pending', 'shipped', 'delivered']"
    )
    assert check.reason == "Actual invalid_count(status) was 1, expected = 0"


def test_an_absent_optional_object_does_not_make_its_required_fields_missing():
    # order-2.xml has no category, whose name is required
    run = DataContract(data_contract_str=contract("fixtures/xml/data/order-2.xml")).test()

    assert results(run)["Check that field category.name has no missing values"] == "passed"


def test_records_inside_a_wrapper_element_with_prefixed_names():
    contract_str = """
apiVersion: v3.2.0
kind: DataContract
id: batch
version: 1.0.0
status: active
servers:
  - server: local
    type: local
    path: fixtures/xml/batch/orders.xml
    format: xml
schema:
  - name: orders
    physicalName: order
    properties:
      - name: order_id
        logicalType: string
        required: true
        unique: true
      - name: order_total
        logicalType: number
        logicalTypeOptions:
          maximum: 20.5
      - name: version
        logicalType: integer
        logicalTypeOptions:
          minimum: 1
    quality:
      - type: sql
        query: SELECT COUNT(*) FROM orders
        mustBe: 3
      - type: sql
        query: SELECT SUM(order_total) FROM orders
        mustBe: 35.75
"""
    run = DataContract(data_contract_str=contract_str).test()

    assert run.result == "passed", [(c.name, c.reason) for c in run.checks if c.result != "passed"]
    # records found, and presence for the required order_id only: optional elements may be absent everywhere
    assert len(run.checks) == 8


def test_a_record_element_that_is_not_in_the_documents_fails():
    run = DataContract(data_contract_str=contract("fixtures/xml/data/*.xml", physicalName="shipment")).test()

    assert run.result == "failed"
    assert results(run)["Check that field 'order_id' is present"] == "failed"


def test_a_value_of_the_wrong_type_fails_the_run(tmp_path: Path):
    document = (
        Path("fixtures/xml/data/order-2.xml").read_text().replace("<quantity>3</quantity>", "<quantity>many</quantity>")
    )
    (tmp_path / "order.xml").write_text(document)

    run = DataContract(data_contract_str=contract(str(tmp_path / "order.xml"))).test()

    assert run.result == "failed"
    # presence is read as text, so only the checks that need the value report it
    assert results(run)["Check that field 'order_id' is present"] == "passed"
    assert any("'many'" in (c.reason or "") for c in run.checks)


@pytest.mark.parametrize("unique, result", [(True, "failed"), (False, "passed")])
def test_unique_across_files(tmp_path: Path, unique, result):
    for name in ("a.xml", "b.xml"):
        (tmp_path / name).write_text(Path("fixtures/xml/data/order-1.xml").read_text())
    data = yaml.safe_load(contract(str(tmp_path / "*.xml")))
    order_id = next(p for p in data["schema"][0]["properties"] if p["name"] == "order_id")
    order_id["unique"] = unique

    run = DataContract(data_contract_str=yaml.safe_dump(data)).test()

    assert results(run).get("Check that unique field order_id has no duplicate values", "passed") == result


def test_an_element_without_its_attributes_keeps_its_text(tmp_path: Path):
    # Where one price carries no currency, DuckDB infers every price as plain text
    for name in ("order-1.xml", "order-2.xml"):
        (tmp_path / name).write_text(Path(f"fixtures/xml/data/{name}").read_text())
    without_currency = Path("fixtures/xml/data/order-2.xml").read_text().replace(' currency="GBP"', "")
    (tmp_path / "order-3.xml").write_text(without_currency.replace("C-1002", "C-1003"))

    run = DataContract(data_contract_str=contract(str(tmp_path / "*.xml"))).test()

    failed = {name for name, result in results(run).items() if result != "passed"}
    assert failed == {"Check that field line_items.line_item[].price.currency has no missing values"}


@pytest.mark.parametrize(
    "schema_changes",
    [
        {"name": 'o" AS SELECT 1; CREATE MACRO injected() AS 42; CREATE VIEW "z'},
        {"physicalName": 'order" AS SELECT 1; CREATE MACRO injected() AS 42; --'},
    ],
)
def test_names_from_the_contract_are_not_run_as_sql(schema_changes):
    con = duckdb.connect()

    DataContract(data_contract_str=contract("fixtures/xml/data/*.xml", **schema_changes), duckdb_connection=con).test()

    assert con.sql("SELECT * FROM duckdb_functions() WHERE function_name = 'injected'").fetchall() == []


def test_an_element_that_occurs_once_in_every_document_is_still_an_array(tmp_path: Path):
    # order-2.xml has a single line_item, which DuckDB infers as one object rather than a list of one
    (tmp_path / "order.xml").write_text(Path("fixtures/xml/data/order-2.xml").read_text())

    run = DataContract(data_contract_str=contract(str(tmp_path / "order.xml"))).test()

    line_item_checks = {name: result for name, result in results(run).items() if "line_item" in name}
    assert len(line_item_checks) > 10
    assert set(line_item_checks.values()) == {"passed"}, line_item_checks


def test_an_imported_pattern_matches_the_whole_value(tmp_path: Path):
    # XSD patterns are anchored; the sku ABC-0001x would pass an unanchored search for [A-Z]{3}-[0-9]{4}
    document = Path("fixtures/xml/data/order-2.xml").read_text().replace("DEF-1234", "xDEF-1234x")
    (tmp_path / "order.xml").write_text(document)

    run = DataContract(data_contract_str=contract(str(tmp_path / "order.xml"))).test()

    assert (
        results(run)["Check that field line_items.line_item[].sku matches regex pattern ^([A-Z]{3}-[0-9]{4})$"]
        == "failed"
    )


# Each schema with documents that follow it and one document that breaks every constraint once
SCHEMAS = {
    "orders": ("fixtures/import/xsd/orders.xsd", "fixtures/xml/data/*.xml", "fixtures/xml/invalid/order-3.xml"),
    "purchase-order": (
        "fixtures/import/xsd/purchase-order.xsd",
        "fixtures/xml/purchase-order/valid/*.xml",
        "fixtures/xml/purchase-order/invalid/po-3.xml",
    ),
    "canonical": (
        "fixtures/xsd/canonical.xsd",
        "fixtures/xml/canonical/valid/*.xml",
        "fixtures/xml/canonical/invalid/order-3.xml",
    ),
}


def imported(xsd: str, path: str) -> DataContract:
    """The contract `datacontract import xsd` creates, with a server for the documents."""
    contract = DataContract.import_from_source("xsd", xsd)
    contract.servers = [Server(server="local", type="local", path=path, format="xml")]
    return DataContract(data_contract=contract)


@pytest.mark.parametrize("name", SCHEMAS)
def test_the_documents_follow_their_own_xsd(name):
    """A planted violation must break the schema too, and a valid document must not."""
    xsd, valid, invalid = SCHEMAS[name]
    schema = xmlschema.XMLSchema(xsd, allow="local", validation="lax")

    documents = sorted(glob.glob(valid))
    assert documents
    for document in documents:
        assert list(schema.iter_errors(document)) == [], document
    assert not schema.is_valid(invalid)


@pytest.mark.parametrize("name", SCHEMAS)
def test_valid_documents_pass_the_imported_contract(name):
    xsd, valid, _ = SCHEMAS[name]

    run = imported(xsd, valid).test()

    assert run.result == "passed", [(c.name, c.reason) for c in run.checks if c.result != "passed"]


PLANTED = {
    "purchase-order": {
        "Check that field shipTo.state has a max length of 2",
        "Check that field shipTo.latitude has a maximum of 90",
        "Check that field creditCard.number matches regex pattern ^(\\d{16}|\\d{4}-\\d{4}-\\d{4}-\\d{4})$",
        "Check that field items.item[].productName has no missing values",
        "Check that field items.item[].quantity is not equal to 100",
        "Check that field items.item[].USPrice.value has a maximum of 99999.99",
        "Check that field items.item[].partNum matches regex pattern ^(\\d{3}-[A-Z]{2})$",
        "Check that field metadata.channel only contains enum values ['web', 'phone', 'store']",
        "Check that field 'orderDate' is present",
        "Check that field orderDate has no missing values",
        "Check that field priority only contains enum values [1, 2, 3]",
    },
    "canonical": {
        "Check that field order_id has a min length of 8",
        "Check that field order_id matches regex pattern ^(ORD-[0-9]{4})$",
        "Check that field code has a max length of 10",
        "Check that field delivery_date has a minimum of 2020-01-01",
        "Check that field total is not equal to 1000000",
        # the range of xs:unsignedInt
        "Check that field items_count has a minimum of 0",
        "Check that field priority only contains enum values [1, 2, 3]",
        "Check that field status only contains enum values ['pending', 'shipped']",
        "Check that field customer.display_name has no missing values",
        "Check that field customer.id has no missing values",
        "Check that field line_item[].quantity has a maximum of 999",
        "Check that field line_item[].price.value has a minimum of 0",
        "Check that field line_item[].price.currency has a max length of 3",
        "Check that field 'version' is present",
        "Check that field version has no missing values",
    },
}


@pytest.mark.parametrize("name", PLANTED)
def test_an_invalid_document_fails_exactly_the_planted_checks(name):
    xsd, _, invalid = SCHEMAS[name]

    run = imported(xsd, invalid).test()

    assert {c.name for c in run.checks if c.result != "passed"} == PLANTED[name]


def xsd_contract(tmp_path: Path, body: str, documents: dict[str, str]) -> DataContract:
    """The contract imported from an XML Schema, testing the given documents."""
    source = tmp_path / "schema.xsd"
    source.write_text(f'<xs:schema xmlns:xs="http://www.w3.org/2001/XMLSchema">{body}</xs:schema>')
    for name, text in documents.items():
        (tmp_path / name).write_text(text)
    return imported(str(source), str(tmp_path / "*.xml"))


def test_a_file_larger_than_16_mb_is_read(tmp_path: Path):
    # read_xml refuses files above 16 MB by default, with a SAX parsing error
    records = "".join(f"<order><id>A-{i}</id><note>{'x' * 40}</note></order>" for i in range(300_000))
    (tmp_path / "orders.xml").write_text(f"<orders>{records}</orders>")
    assert (tmp_path / "orders.xml").stat().st_size > 16 * 2**20
    contract = f"""
apiVersion: v3.2.0
kind: DataContract
id: big
version: 1.0.0
status: active
servers:
  - server: local
    type: local
    path: {tmp_path / "orders.xml"}
    format: xml
schema:
  - name: order
    properties:
      - name: id
        logicalType: string
        required: true
    quality:
      - type: sql
        query: SELECT COUNT(*) FROM {{model}}
        mustBe: 300000
"""
    run = DataContract(data_contract_str=contract).test()

    assert run.result == "passed", [(c.name, c.reason) for c in run.checks if c.result != "passed"]


def test_documents_without_any_record_fail(tmp_path: Path):
    # all properties optional: without a check for records, a wrong record element would pass every check
    run = DataContract(
        data_contract_str=contract(
            "fixtures/xml/data/*.xml",
            physicalName="shipment",
            properties=[{"name": "tracking", "logicalType": "string", "logicalTypeOptions": {"pattern": "^[A-Z]+$"}}],
        )
    ).test()

    assert run.result == "failed"
    assert results(run)["Check that the documents have shipment elements"] == "failed"


def test_the_elements_of_a_repeating_group_are_arrays(tmp_path: Path):
    contract = xsd_contract(
        tmp_path,
        """<xs:element name="contact"><xs:complexType>
             <xs:choice maxOccurs="unbounded">
               <xs:element name="email" type="xs:string"/>
               <xs:element name="phone" type="xs:string"/>
             </xs:choice>
           </xs:complexType></xs:element>""",
        {
            "a.xml": "<contact><email>a@x.org</email><phone>1</phone><email>b@x.org</email></contact>",
            "b.xml": "<contact><email>c@x.org</email></contact>",
        },
    )
    odcs = contract.get_data_contract()
    odcs.schema_[0].quality = [
        DataQuality(type="sql", query="SELECT SUM(len(email)) + SUM(len(phone)) FROM {model}", mustBe=4)
    ]

    run = DataContract(data_contract=odcs).test()

    assert run.result == "passed", [(c.name, c.reason) for c in run.checks if c.result != "passed"]


def test_an_attribute_named_value_next_to_text_is_read(tmp_path: Path):
    run = xsd_contract(
        tmp_path,
        """<xs:element name="item"><xs:complexType><xs:sequence>
             <xs:element name="price"><xs:complexType><xs:simpleContent>
               <xs:extension base="xs:decimal">
                 <xs:attribute name="value" use="required"><xs:simpleType><xs:restriction base="xs:string">
                   <xs:enumeration value="list"/><xs:enumeration value="net"/>
                 </xs:restriction></xs:simpleType></xs:attribute>
               </xs:extension>
             </xs:simpleContent></xs:complexType></xs:element>
           </xs:sequence></xs:complexType></xs:element>""",
        {
            "a.xml": '<item><price value="list">9.50</price></item>',
            "b.xml": '<item><price value="gross">-1</price></item>',
        },
    ).test()

    failed = {c.name for c in run.checks if c.result != "passed"}
    assert failed == {"Check that field price.@value only contains enum values ['list', 'net']"}


def test_an_attribute_named_like_an_element_is_read_as_the_attribute(tmp_path: Path, caplog):
    # read_xml reads only the attribute when an element has the same name
    with caplog.at_level("WARNING"):
        run = xsd_contract(
            tmp_path,
            """<xs:element name="order"><xs:complexType>
                 <xs:sequence><xs:element name="id" type="xs:string"/></xs:sequence>
                 <xs:attribute name="id" type="xs:unsignedByte" use="required"/>
               </xs:complexType></xs:element>""",
            {"a.xml": '<order id="7"><id>A-1</id></order>', "b.xml": '<order id="300"><id>A-2</id></order>'},
        ).test()

    assert results(run)["Check that field @id has a maximum of 255"] == "failed"
    assert "read_xml reads only the attribute" in caplog.text


def test_a_fixed_value_is_checked(tmp_path: Path):
    run = xsd_contract(
        tmp_path,
        """<xs:element name="address"><xs:complexType>
             <xs:sequence><xs:element name="country" type="xs:string" fixed="US"/></xs:sequence>
           </xs:complexType></xs:element>""",
        {"a.xml": "<address><country>US</country></address>", "b.xml": "<address><country>DE</country></address>"},
    ).test()

    assert results(run)["Check that field country only contains enum values ['US']"] == "failed"


def test_a_pattern_on_repeated_elements_is_checked(tmp_path: Path):
    run = xsd_contract(
        tmp_path,
        """<xs:element name="contact"><xs:complexType><xs:sequence>
             <xs:element name="email" maxOccurs="unbounded"><xs:simpleType><xs:restriction base="xs:string">
               <xs:pattern value="[^@]+@[^@]+"/></xs:restriction></xs:simpleType></xs:element>
           </xs:sequence></xs:complexType></xs:element>""",
        {
            "a.xml": "<contact><email>a@x.org</email><email>b@x.org</email></contact>",
            "b.xml": "<contact><email>c@x.org</email><email>not-an-email</email></contact>",
        },
    ).test()

    check = next(c for c in run.checks if "regex pattern" in c.name)
    assert (check.name, check.result, check.reason) == (
        "Check that field email[] matches regex pattern ^([^@]+@[^@]+)$",
        "failed",
        "Actual invalid_count(email[]) was 1, expected = 0",
    )
