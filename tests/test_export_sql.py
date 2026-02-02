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
  field_one VARCHAR not null,
  field_two INTEGER,
  field_three TIMESTAMP
);
""".strip()
    assert actual == expected


def test_to_sql_ddl_snowflake():
    actual = DataContract(data_contract_file="fixtures/snowflake/datacontract.yaml").export("sql")
    expected = """
-- Data Contract: urn:datacontract:checkout:snowflake_orders_pii_v2
-- SQL Dialect: snowflake
CREATE TABLE ORDER_DB.ORDERS_PII_V2.orders (
  ORDER_ID TEXT not null COMMENT 'An internal ID that identifies an order in the online shop.',
  ORDER_TIMESTAMP TIMESTAMP not null COMMENT 'The business timestamp in UTC when the order was successfully registered in the source system and the payment was successful.',
  ORDER_TOTAL NUMBER not null COMMENT 'Total amount the smallest monetary unit (e.g., cents).',
  CUSTOMER_ID TEXT COMMENT 'Unique identifier for the customer.',
  CUSTOMER_EMAIL_ADDRESS TEXT not null COMMENT 'The email address, as entered by the customer. The email address was not verified.',
  PROCESSING_TIMESTAMP TIMESTAMP_LTZ not null COMMENT 'The processing timestamp in the current session's time zone.'
) COMMENT='One record per order. Includes cancelled and deleted orders.';
CREATE TABLE ORDER_DB.ORDERS_PII_V2.line_items (
  LINE_ITEM_ID TEXT not null COMMENT 'Primary key of the lines_item_id table',
  ORDER_ID TEXT COMMENT 'An internal ID that identifies an order in the online shop.',
  SKU TEXT COMMENT 'The purchased article number'
) COMMENT='A single article that is part of an order.';
""".strip()
    assert actual == expected


def test_to_sql_ddl_databricks_unity_catalog():
    actual = DataContract(data_contract_file="fixtures/databricks-sql/datacontract.yaml").export("sql")
    expected = """
-- Data Contract: urn:datacontract:checkout:orders-latest
-- SQL Dialect: databricks
CREATE OR REPLACE TABLE datacontract_test_2.orders_latest.orders (
  order_id TEXT not null COMMENT "An internal ID that identifies an order in the online shop.",
  order_timestamp TIMESTAMP not null COMMENT "The business timestamp in UTC when the order was successfully registered in the source system and the payment was successful.",
  order_total LONG not null COMMENT "Total amount the smallest monetary unit (e.g., cents).",
  customer_id STRING COMMENT "Unique identifier for the customer.",
  customer_email_address STRING not null COMMENT "The email address, as entered by the customer. The email address was not verified.",
  discounts ARRAY<STRUCT<discount_code:STRING, discount_amount:LONG>> COMMENT "This is an array of records"
) COMMENT "One record per order. Includes cancelled and deleted orders.";
CREATE OR REPLACE TABLE datacontract_test_2.orders_latest.line_items (
  lines_item_id STRING not null COMMENT "Primary key of the lines_item_id table",
  order_id TEXT COMMENT "An internal ID that identifies an order in the online shop.",
  sku TEXT COMMENT "The purchased article number"
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
  order_id TEXT not null COMMENT "An internal ID that identifies an order in the online shop.",
  order_timestamp TIMESTAMP not null COMMENT "The business timestamp in UTC when the order was successfully registered in the source system and the payment was successful.",
  order_total LONG not null COMMENT "Total amount the smallest monetary unit (e.g., cents).",
  customer_id STRING COMMENT "Unique identifier for the customer.",
  customer_email_address STRING not null COMMENT "The email address, as entered by the customer. The email address was not verified.",
  discounts ARRAY<STRUCT<discount_code:STRING, discount_amount:LONG>> COMMENT "This is an array of records"
) COMMENT "One record per order. Includes cancelled and deleted orders.";
CREATE OR REPLACE TABLE datacontract_staging.orders_latest.line_items (
  lines_item_id STRING not null COMMENT "Primary key of the lines_item_id table",
  order_id TEXT COMMENT "An internal ID that identifies an order in the online shop.",
  sku TEXT COMMENT "The purchased article number"
) COMMENT "A single article that is part of an order.";
""".strip()
    assert actual == expected

def test_to_sql_ddl_snowflake_multiple_pk():
    actual = DataContract(data_contract_file="fixtures/snowflake/dcMultiplePK.yaml", server="workspace1").export("sql")
    expected = """
-- Data Contract: urn:datacontract:example:composite-key-test
-- SQL Dialect: snowflake
CREATE TABLE my_database.public.MY_TABLE (
  id_part1 VARCHAR(50) not null,
  id_part2 VARCHAR(50) not null,
  data_field VARCHAR(256)
  , UNIQUE(id_part1,id_part2));""".strip()
    assert actual == expected