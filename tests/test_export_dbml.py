from datetime import datetime
from importlib.metadata import version

import pytz
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(app, ["export", "./fixtures/dbml/datacontract.odcs.yaml", "--format", "dbml"])
    assert result.exit_code == 0


def test_cli_with_server():
    runner = CliRunner()
    result = runner.invoke(
        app, ["export", "./fixtures/dbml/datacontract.odcs.yaml", "--format", "dbml", "--server", "production"]
    )
    assert result.exit_code == 0


def test_dbml_export():
    data_contract = DataContract(data_contract_file="fixtures/dbml/datacontract.odcs.yaml")
    assert data_contract.lint().has_passed()

    result = data_contract.export("dbml")

    tz = pytz.timezone("UTC")
    now = datetime.now(tz)
    formatted_date = now.strftime("%b %d %Y")
    try:
        datacontract_cli_version = version("datacontract_cli")
    except Exception:
        datacontract_cli_version = ""

    # fmt: off
    expected = """/*
Generated at {0} by datacontract-cli version {1}
for datacontract Orders Latest (urn:datacontract:checkout:orders-latest) version 1.0.0
Using Logical Datacontract Types for the field types
*/
Project "Orders Latest" {{
    note: '''Successful customer orders in the webshop.
All orders since 2020-01-01.
Orders with their line items are in their current state (no history included).'''
}}

Table orders {{
    note: "One record per order. Includes cancelled and deleted orders."
    order_id string [pk, unique, not null, note: "An internal ID that identifies an order in the online shop."]
    order_timestamp timestamp [not null, note: "The business timestamp in UTC when the order was successfully registered in the source system and the payment was successful."]
    order_total object [not null, note: "Total amount the smallest monetary unit (e.g., cents)."]
    customer_id string [null, note: "Unique identifier for the customer."]
    customer_email_address string [not null, note: "The email address, as entered by the customer. The email address was not verified."]
    processed_timestamp timestamp [not null, note: "The timestamp when the record was processed by the data platform."]
}}

Table line_items {{
    note: "A single article that is part of an order."
    lines_item_id string [pk, unique, not null, note: "Primary key of the lines_item_id table"]
    order_id string [null, note: "An internal ID that identifies an order in the online shop."]
    sku string [null, note: "The purchased article number"]
}}
Ref: line_items.order_id > orders.order_id
""".format(formatted_date, datacontract_cli_version)
    # fmt: on

    assert result.strip() == expected.strip()


def test_dbml_export_with_server():
    data_contract = DataContract(data_contract_file="fixtures/dbml/datacontract.odcs.yaml", server="production")
    assert data_contract.lint().has_passed()

    result = data_contract.export("dbml")

    tz = pytz.timezone("UTC")
    now = datetime.now(tz)
    formatted_date = now.strftime("%b %d %Y")
    try:
        datacontract_cli_version = version("datacontract_cli")
    except Exception:
        datacontract_cli_version = ""

    # fmt: off
    expected = """/*
Generated at {0} by datacontract-cli version {1}
for datacontract Orders Latest (urn:datacontract:checkout:orders-latest) version 1.0.0
Using s3 Types for the field types
*/
Project "Orders Latest" {{
    note: '''Successful customer orders in the webshop.
All orders since 2020-01-01.
Orders with their line items are in their current state (no history included).'''
}}

Table orders {{
    note: "One record per order. Includes cancelled and deleted orders."
    order_id VARCHAR [pk, unique, not null, note: "An internal ID that identifies an order in the online shop."]
    order_timestamp TIMESTAMP WITH TIME ZONE [not null, note: "The business timestamp in UTC when the order was successfully registered in the source system and the payment was successful."]
    order_total STRUCT(amount STRUCT(sum DECIMAL(None,None), currency VARCHAR), due_date DATE, discount DOUBLE) [not null, note: "Total amount the smallest monetary unit (e.g., cents)."]
    customer_id VARCHAR [null, note: "Unique identifier for the customer."]
    customer_email_address VARCHAR [not null, note: "The email address, as entered by the customer. The email address was not verified."]
    processed_timestamp TIMESTAMP WITH TIME ZONE [not null, note: "The timestamp when the record was processed by the data platform."]
}}

Table line_items {{
    note: "A single article that is part of an order."
    lines_item_id VARCHAR [pk, unique, not null, note: "Primary key of the lines_item_id table"]
    order_id VARCHAR [null, note: "An internal ID that identifies an order in the online shop."]
    sku VARCHAR [null, note: "The purchased article number"]
}}
Ref: line_items.order_id > orders.order_id
""".format(formatted_date, datacontract_cli_version)
    # fmt: on

    assert result.strip() == expected.strip()
