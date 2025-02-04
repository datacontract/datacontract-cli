from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(app, ["export", "./fixtures/postgres-export/datacontract.yaml", "--format", "sql"])
    assert result.exit_code == 0


def test_to_sql_ddl_postgres():
    actual = DataContract(data_contract_file="fixtures/postgres-export/datacontract.yaml").export("sql")
    expected = """
-- Data Contract: postgres
-- SQL Dialect: postgres
CREATE TABLE my_table (
  field_one text not null,
  field_two integer,
  field_three timestamptz
);
""".strip()
    assert actual == expected


def test_to_sql_ddl_snowflake():
    actual = DataContract(data_contract_file="fixtures/snowflake/datacontract.yaml").export("sql")
    expected = """
-- Data Contract: urn:datacontract:checkout:snowflake_orders_pii_v2
-- SQL Dialect: snowflake
CREATE TABLE orders (
  ORDER_ID TEXT not null,
  ORDER_TIMESTAMP TIMESTAMP_TZ not null,
  ORDER_TOTAL NUMBER not null,
  CUSTOMER_ID TEXT,
  CUSTOMER_EMAIL_ADDRESS TEXT not null,
  PROCESSING_TIMESTAMP TIMESTAMP_LTZ not null
);
CREATE TABLE line_items (
  LINE_ITEM_ID TEXT not null,
  ORDER_ID TEXT,
  SKU TEXT
);
""".strip()
    assert actual == expected


def test_to_sql_ddl_databricks_unity_catalog():
    actual = DataContract(data_contract_file="fixtures/databricks-sql/datacontract.yaml").export("sql")
    expected = """
-- Data Contract: urn:datacontract:checkout:orders-latest
-- SQL Dialect: databricks
CREATE OR REPLACE TABLE datacontract_test_2.orders_latest.orders (
  order_id STRING not null COMMENT "An internal ID that identifies an order in the online shop.",
  order_timestamp TIMESTAMP not null COMMENT "The business timestamp in UTC when the order was successfully registered in the source system and the payment was successful.",
  order_total BIGINT not null COMMENT "Total amount the smallest monetary unit (e.g., cents).",
  customer_id STRING COMMENT "Unique identifier for the customer.",
  customer_email_address STRING not null COMMENT "The email address, as entered by the customer. The email address was not verified.",
  discounts ARRAY<STRUCT<discount_code STRING, discount_amount BIGINT>> COMMENT "This is an array of records"
) COMMENT "One record per order. Includes cancelled and deleted orders.";
CREATE OR REPLACE TABLE datacontract_test_2.orders_latest.line_items (
  lines_item_id STRING not null COMMENT "Primary key of the lines_item_id table",
  order_id STRING COMMENT "An internal ID that identifies an order in the online shop.",
  sku STRING COMMENT "The purchased article number"
) COMMENT "A single article that is part of an order.";
""".strip()
    assert actual == expected


def test_to_sql_ddl_databricks_unity_catalog_staging():
    actual = DataContract(data_contract_file="fixtures/databricks-sql/datacontract.yaml").export(
        "sql", server="staging"
    )
    expected = """
-- Data Contract: urn:datacontract:checkout:orders-latest
-- SQL Dialect: databricks
CREATE OR REPLACE TABLE datacontract_staging.orders_latest.orders (
  order_id STRING not null COMMENT "An internal ID that identifies an order in the online shop.",
  order_timestamp TIMESTAMP not null COMMENT "The business timestamp in UTC when the order was successfully registered in the source system and the payment was successful.",
  order_total BIGINT not null COMMENT "Total amount the smallest monetary unit (e.g., cents).",
  customer_id STRING COMMENT "Unique identifier for the customer.",
  customer_email_address STRING not null COMMENT "The email address, as entered by the customer. The email address was not verified.",
  discounts ARRAY<STRUCT<discount_code STRING, discount_amount BIGINT>> COMMENT "This is an array of records"
) COMMENT "One record per order. Includes cancelled and deleted orders.";
CREATE OR REPLACE TABLE datacontract_staging.orders_latest.line_items (
  lines_item_id STRING not null COMMENT "Primary key of the lines_item_id table",
  order_id STRING COMMENT "An internal ID that identifies an order in the online shop.",
  sku STRING COMMENT "The purchased article number"
) COMMENT "A single article that is part of an order.";
""".strip()
    assert actual == expected
