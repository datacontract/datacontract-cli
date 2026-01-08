import os
import sys

from rdflib.compare import to_isomorphic
from rdflib.graph import Graph
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.export.rdf_exporter import to_rdf
from datacontract.lint.resolve import resolve_data_contract

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app, ["export", "./fixtures/export/rdf/datacontract.yaml", "--format", "rdf", "--rdf-base", "urn:acme:"]
    )
    assert result.exit_code == 0


def test_no_rdf_base():
    runner = CliRunner()
    result = runner.invoke(app, ["export", "./fixtures/export/rdf/datacontract.yaml", "--format", "rdf"])
    assert result.exit_code == 0


def test_to_rdf():
    data_contract_file = "fixtures/export/rdf/datacontract.yaml"
    file_content = read_file(data_contract_file=data_contract_file)
    data_contract = resolve_data_contract(data_contract_str=file_content)
    expected_rdf = """
@base <https://example.com/> .
@prefix odcs: <https://github.com/bitol-io/open-data-contract-standard/> .
@prefix odcsx: <https://github.com/bitol-io/open-data-contract-standard/extension/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<orders-unit-test> a odcs:DataContract ;
    odcs:apiVersion "v3.1.0" ;
    odcs:id "orders-unit-test" ;
    odcs:info [ a odcs:Info ;
            odcs:name "Orders Unit Test" ;
            odcs:team "checkout" ;
            odcs:version "1.0.0" ] ;
    odcs:kind "DataContract" ;
    odcs:schema_ <orders> .

<orders> a odcs:Schema ;
    odcs:description "The orders model" ;
    odcs:property [ a odcs:Property ;
            odcs:description "The order_total field" ;
            odcs:logicalType "integer" ;
            odcs:name "order_total" ;
            odcs:physicalType "bigint" ;
            odcs:required true ],
        [ a odcs:Property ;
            odcs:logicalType "string" ;
            odcs:name "order_status" ;
            odcs:physicalType "text" ;
            odcs:required true ],
        [ a odcs:Property ;
            odcsx:tags "order_id" ;
            odcs:classification "sensitive" ;
            odcs:logicalType "string" ;
            odcs:name "order_id" ;
            odcs:physicalType "varchar" ;
            odcs:required true ;
            odcs:unique true ] .

"""
    g = Graph().parse(format="n3", data=expected_rdf)

    result = to_rdf(data_contract, "https://example.com/")

    iso_g1 = to_isomorphic(Graph().parse(data=g.serialize()))
    iso_result = to_isomorphic(Graph().parse(data=result.serialize()))

    assert iso_g1 == iso_result


def test_to_rdf_complex():
    data_contract_file = "fixtures/export/rdf/datacontract-complex.yaml"
    file_content = read_file(data_contract_file=data_contract_file)
    data_contract = resolve_data_contract(data_contract_str=file_content)
    expected_rdf = """
@base <http://test.com/> .
@prefix odcs: <https://github.com/bitol-io/open-data-contract-standard/> .
@prefix odcsx: <https://github.com/bitol-io/open-data-contract-standard/extension/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<orders-latest> a odcs:DataContract ;
    odcs:apiVersion "v3.1.0" ;
    odcs:id "orders-latest" ;
    odcs:info [ a odcs:Info ;
            odcs:description \"\"\"Successful customer orders in the webshop. All orders since 2020-01-01. Orders with their line items are in their current state (no history included).
\"\"\" ;
            odcs:name "Orders Latest" ;
            odcs:team "urn:acme:CheckoutTeam" ;
            odcs:version "1.0.0" ] ;
    odcs:kind "DataContract" ;
    odcs:schema_ <line_items>,
        <orders> ;
    odcs:server <production> .

<line_items> a odcs:Schema ;
    odcs:description "A single article that is part of an order." ;
    odcs:property [ a odcs:Property ;
            odcs:classification "restricted" ;
            odcs:description "An internal ID that identifies an order in the online shop." ;
            odcsx:businessName "Order ID" ;
            odcs:logicalType "string" ;
            odcs:name "order_id" ;
            odcs:physicalType "text" ],
        [ a odcs:Property ;
            odcs:description "The purchased article number" ;
            odcsx:businessName "Stock Keeping Unit" ;
            odcs:logicalType "string" ;
            odcs:name "sku" ;
            odcs:physicalType "text" ],
        [ a odcs:Property ;
            odcs:description "Primary key of the lines_item_id table" ;
            odcs:logicalType "string" ;
            odcs:name "lines_item_id" ;
            odcs:physicalType "text" ;
            odcs:required true ;
            odcs:unique true ] .

<orders> a odcs:Schema ;
    odcs:description "One record per order. Includes cancelled and deleted orders." ;
    odcs:property [ a odcs:Property ;
            odcs:classification "restricted" ;
            odcs:description "An internal ID that identifies an order in the online shop." ;
            odcsx:businessName "Order ID" ;
            odcs:logicalType "string" ;
            odcs:name "order_id" ;
            odcs:physicalType "text" ;
            odcs:required true ;
            odcs:unique true ],
        [ a odcs:Property ;
            odcs:description "The business timestamp in UTC when the order was successfully registered in the source system and the payment was successful." ;
            odcs:logicalType "timestamp" ;
            odcs:name "order_timestamp" ;
            odcs:physicalType "timestamp" ;
            odcs:required true ],
        [ a odcs:Property ;
            odcs:description "Unique identifier for the customer." ;
            odcs:logicalType "string" ;
            odcs:name "customer_id" ;
            odcs:physicalType "text" ],
        [ a odcs:Property ;
            odcs:description "The email address, as entered by the customer. The email address was not verified." ;
            odcs:logicalType "string" ;
            odcs:name "customer_email_address" ;
            odcs:physicalType "text" ;
            odcs:required true ],
        [ a odcs:Property ;
            odcs:description "Total amount the smallest monetary unit (e.g., cents)." ;
            odcs:logicalType "integer" ;
            odcs:name "order_total" ;
            odcs:physicalType "long" ;
            odcs:required true ] .

<production> a odcs:Server ;
    odcs:delimiter "new_line" ;
    odcsx:server "production" ;
    odcs:format "json" ;
    odcs:location "s3://multiple-bucket/fixtures/s3-json-multiple-models/data/{model}/*.json" ;
    odcs:type "s3" .

"""

    g = Graph().parse(format="n3", data=expected_rdf)

    result = to_rdf(data_contract, base="http://test.com/")

    iso_g1 = to_isomorphic(Graph().parse(data=g.serialize()))
    iso_result = to_isomorphic(Graph().parse(data=result.serialize()))

    assert iso_g1 == iso_result


def read_file(data_contract_file):
    if not os.path.exists(data_contract_file):
        print(f"The file '{data_contract_file}' does not exist.")
        sys.exit(1)
    with open(data_contract_file, "r") as file:
        file_content = file.read()
    return file_content
