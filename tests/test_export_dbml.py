from datetime import datetime
from importlib.metadata import version

import pytz
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(app, ["export", "./fixtures/dbml/datacontract.yaml", "--format", "dbml"])
    assert result.exit_code == 0


def test_cli_with_server():
    runner = CliRunner()
    result = runner.invoke(
        app, ["export", "./fixtures/dbml/datacontract.yaml", "--format", "dbml", "--server", "production"]
    )
    assert result.exit_code == 0


def test_dbml_export():
    data_contract = DataContract(data_contract_file="fixtures/dbml/datacontract.yaml")
    assert data_contract.lint(enabled_linters="none").has_passed()

    result = data_contract.export("dbml")

    tz = pytz.timezone("UTC")
    now = datetime.now(tz)
    formatted_date = now.strftime("%b %d %Y")
    try:
        datacontract_cli_version = version("datacontract_cli")
    except Exception:
        datacontract_cli_version = ""

    expected = """
/*

Generated at {0} by datacontract-cli version {1}
for datacontract Orders Latest (urn:datacontract:checkout:orders-latest) version 1.0.0 
Using Logical Datacontract Types for the field types
    
*/
    
Project "Orders Latest" {{
    Note: '''Successful customer orders in the webshop. 
All orders since 2020-01-01. 
Orders with their line items are in their current state (no history included).
'''
}}

    

Table "orders" {{ 
Note: "One record per order. Includes cancelled and deleted orders."
    "order_id" "text" [pk,unique,not null,Note: "An internal ID that identifies an order in the online shop."]
"order_timestamp" "timestamp" [not null,Note: "The business timestamp in UTC when the order was successfully registered in the source system and the payment was successful."]
"order_total" "record" [not null,Note: "Total amount the smallest monetary unit (e.g., cents)."]
"customer_id" "text" [null,Note: "Unique identifier for the customer."]
"customer_email_address" "text" [not null,Note: "The email address, as entered by the customer. The email address was not verified."]
"processed_timestamp" "timestamp" [not null,Note: "The timestamp when the record was processed by the data platform."]
}}


Table "line_items" {{ 
Note: "A single article that is part of an order."
    "lines_item_id" "text" [pk,unique,not null,Note: "Primary key of the lines_item_id table"]
"order_id" "text" [null,Note: "An internal ID that identifies an order in the online shop."]
"sku" "text" [null,Note: "The purchased article number"]
}}
Ref: line_items.order_id > orders.order_id
    """.format(formatted_date, datacontract_cli_version)

    assert result.strip() == expected.strip()


def test_dbml_export_with_server():
    data_contract = DataContract(data_contract_file="fixtures/dbml/datacontract.yaml", server="production")
    assert data_contract.lint(enabled_linters="none").has_passed()

    result = data_contract.export("dbml")

    tz = pytz.timezone("UTC")
    now = datetime.now(tz)
    formatted_date = now.strftime("%b %d %Y")
    try:
        datacontract_cli_version = version("datacontract_cli")
    except Exception:
        datacontract_cli_version = ""

    expected = """
/*

Generated at {0} by datacontract-cli version {1}
for datacontract Orders Latest (urn:datacontract:checkout:orders-latest) version 1.0.0 
Using s3 Types for the field types
    
*/
    
Project "Orders Latest" {{
    Note: '''Successful customer orders in the webshop. 
All orders since 2020-01-01. 
Orders with their line items are in their current state (no history included).
'''
}}

    

Table "orders" {{ 
Note: "One record per order. Includes cancelled and deleted orders."
    "order_id" "VARCHAR" [pk,unique,not null,Note: "An internal ID that identifies an order in the online shop."]
"order_timestamp" "TIMESTAMP WITH TIME ZONE" [not null,Note: "The business timestamp in UTC when the order was successfully registered in the source system and the payment was successful."]
"order_total" "STRUCT(amount STRUCT(sum DECIMAL(None,None), currency VARCHAR), due_date DATE, discount DOUBLE)" [not null,Note: "Total amount the smallest monetary unit (e.g., cents)."]
"customer_id" "VARCHAR" [null,Note: "Unique identifier for the customer."]
"customer_email_address" "VARCHAR" [not null,Note: "The email address, as entered by the customer. The email address was not verified."]
"processed_timestamp" "TIMESTAMP WITH TIME ZONE" [not null,Note: "The timestamp when the record was processed by the data platform."]
}}


Table "line_items" {{ 
Note: "A single article that is part of an order."
    "lines_item_id" "VARCHAR" [pk,unique,not null,Note: "Primary key of the lines_item_id table"]
"order_id" "VARCHAR" [null,Note: "An internal ID that identifies an order in the online shop."]
"sku" "VARCHAR" [null,Note: "The purchased article number"]
}}
Ref: line_items.order_id > orders.order_id
    """.format(formatted_date, datacontract_cli_version)

    print("Actual Result:\n", result.strip())
    print("Expected Result:\n", expected.strip())

    assert result.strip() == expected.strip()
