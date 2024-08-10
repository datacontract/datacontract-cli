import os
import sys

from rdflib.compare import to_isomorphic
from rdflib.graph import Graph
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.export.rdf_converter import to_rdf
from datacontract.model.data_contract_specification import DataContractSpecification

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
    data_contract = DataContractSpecification.from_string(file_content)
    expected_rdf = """
@prefix dc1: <https://datacontract.com/DataContractSpecification/0.9.2/> .
@prefix dcx: <https://datacontract.com/DataContractSpecification/0.9.2/Extension/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<https://example.com/orders-unit-test> a dc1:DataContract ;
    dc1:dataContractSpecification "0.9.2" ;
    dc1:id "orders-unit-test" ;
    dc1:info [ a dc1:Info ;
            dc1:contact [ a dc1:Contact ;
                dcx:email "team-orders@example.com" ;
                dc1:url "https://wiki.example.com/teams/checkout" ] ;
            dc1:description "None" ;
            dc1:owner "checkout" ;
            dc1:title "Orders Unit Test" ;
            dc1:version "1.0.0" ] ;
    dc1:model <https://example.com/orders> ;
    dc1:terms [ a dc1:Terms ;
            dc1:billing "free" ;
            dc1:limitations "Not intended to use in production" ;
            dc1:noticePeriod "P3M" ;
            dc1:usage "This data contract serves to demo datacontract CLI export." ] .

<https://example.com/orders> a dc1:Model ;
    dc1:description "The orders model" ;
    dc1:field [ a dc1:Field ;
            dc1:description "The order_total field" ;
            dc1:maximum 1000000 ;
            dc1:minimum 0 ;
            dc1:name "order_total" ;
            dc1:required true ;
            dc1:type "bigint" ],
        [ a dc1:Field ;
            dc1:enum "delivered",
                "pending",
                "shipped" ;
            dc1:name "order_status" ;
            dc1:required true ;
            dc1:type "text" ],
        [ a dc1:Field ;
            dcx:pattern "^B[0-9]+$" ;
            dcx:tags "order_id" ;
            dc1:classification "sensitive" ;
            dc1:maxLength 10 ;
            dc1:minLength 8 ;
            dc1:name "order_id" ;
            dc1:pii true ;
            dc1:required true ;
            dc1:type "varchar" ;
            dc1:unique true ] .

"""
    g = Graph().parse(format="n3", data=expected_rdf)

    result = to_rdf(data_contract, "https://example.com/")

    iso_g1 = to_isomorphic(Graph().parse(data=g.serialize()))
    iso_result = to_isomorphic(Graph().parse(data=result.serialize()))

    assert iso_g1 == iso_result


def test_to_rdf_complex():
    data_contract_file = "fixtures/export/rdf/datacontract-complex.yaml"
    file_content = read_file(data_contract_file=data_contract_file)
    data_contract = DataContractSpecification.from_string(file_content)
    expected_rdf = """
@base <http://test.com/> .
@prefix dc1: <https://datacontract.com/DataContractSpecification/0.9.2/> .
@prefix dcx: <https://datacontract.com/DataContractSpecification/0.9.2/Extension/> .
@prefix xsd: <http://www.w3.org/2001/XMLSchema#> .

<orders-latest> a dc1:DataContract ;
    dc1:dataContractSpecification "0.9.2" ;
    dc1:example [ a dc1:Example ;
            dc1:data \"\"\"order_id,order_timestamp,order_total
"1001","2023-09-09T08:30:00Z",2500
"1002","2023-09-08T15:45:00Z",1800
"1003","2023-09-07T12:15:00Z",3200
"1004","2023-09-06T19:20:00Z",1500
"1005","2023-09-05T10:10:00Z",4200
"1006","2023-09-04T14:55:00Z",2800
"1007","2023-09-03T21:05:00Z",1900
"1008","2023-09-02T17:40:00Z",3600
"1009","2023-09-01T09:25:00Z",3100
"1010","2023-08-31T22:50:00Z",2700\"\"\" ;
            dc1:model <orders> ;
            dc1:type "csv" ],
        [ a dc1:Example ;
            dc1:data \"\"\"lines_item_id,order_id,sku
"1","1001","5901234123457"
"2","1001","4001234567890"
"3","1002","5901234123457"
"4","1002","2001234567893"
"5","1003","4001234567890"
"6","1003","5001234567892"
"7","1004","5901234123457"
"8","1005","2001234567893"
"9","1005","5001234567892"
"10","1005","6001234567891\\"\"\"\" ;
            dc1:model <line_items> ;
            dc1:type "csv" ] ;
    dc1:id "orders-latest" ;
    dc1:info [ a dc1:Info ;
            dc1:contact [ a dc1:Contact ;
                dc1:name "John Doe (Data Product Owner)" ;
                dc1:url "https://teams.microsoft.com/l/channel/acme/checkout" ] ;
            dc1:description \"\"\"Successful customer orders in the webshop. All orders since 2020-01-01. Orders with their line items are in their current state (no history included).
\"\"\" ;
            dc1:owner "urn:acme:CheckoutTeam" ;
            dc1:title "Orders Latest" ;
            dc1:version "1.0.0" ] ;
    dc1:model <line_items>,
        <orders> ;
    dc1:server <production> ;
    dc1:terms [ a dc1:Terms ;
            dc1:billing "5000 USD per month" ;
            dc1:limitations \"\"\"Not suitable for real-time use cases. Data may not be used to identify individual customers. Max data processing per day: 10 TiB
\"\"\" ;
            dc1:noticePeriod "P3M" ;
            dc1:usage \"\"\"Data can be used for reports, analytics and machine learning use cases. Order may be linked and joined by other tables
\"\"\" ] .

<production> a dc1:Server ;
    dc1:delimiter "new_line" ;
    dc1:format "json" ;
    dc1:location "s3://multiple-bucket/fixtures/s3-json-multiple-models/data/{model}/*.json" ;
    dc1:type "s3" .

<line_items> a dc1:Model ;
    dc1:description "A single article that is part of an order." ;
    dc1:field [ a dc1:Field ;
            dc1:description "Primary key of the lines_item_id table" ;
            dc1:name "lines_item_id" ;
            dc1:required true ;
            dc1:type "text" ;
            dc1:unique true ],
        [ a dc1:Field ;
            dc1:name "order_id" ],
        [ a dc1:Field ;
            dc1:description "The purchased article number" ;
            dc1:name "sku" ] .

<orders> a dc1:Model ;
    dc1:description "One record per order. Includes cancelled and deleted orders." ;
    dc1:field [ a dc1:Field ;
            dc1:name "order_id" ;
            dc1:required true ;
            dc1:unique true ],
        [ a dc1:Field ;
            dc1:description "The business timestamp in UTC when the order was successfully registered in the source system and the payment was successful." ;
            dc1:name "order_timestamp" ;
            dc1:required true ;
            dc1:type "timestamp" ],
        [ a dc1:Field ;
            dc1:description "The email address, as entered by the customer. The email address was not verified." ;
            dc1:format "email" ;
            dc1:name "customer_email_address" ;
            dc1:required true ;
            dc1:type "text" ],
        [ a dc1:Field ;
            dc1:description "Unique identifier for the customer." ;
            dc1:maxLength 20 ;
            dc1:minLength 10 ;
            dc1:name "customer_id" ;
            dc1:type "text" ],
        [ a dc1:Field ;
            dc1:description "Total amount the smallest monetary unit (e.g., cents)." ;
            dc1:name "order_total" ;
            dc1:required true ;
            dc1:type "long" ] .

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
