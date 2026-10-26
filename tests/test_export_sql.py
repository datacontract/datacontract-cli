import re

from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(app, ["export", "sql", "./fixtures/postgres-export/datacontract.yaml"])
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
  ORDER_ID TEXT not null COMMENT 'An internal ID that identifies an order in the online shop.',
  ORDER_TIMESTAMP TIMESTAMP_TZ not null COMMENT 'The business timestamp in UTC when the order was successfully registered in the source system and the payment was successful.',
  ORDER_TOTAL NUMBER not null COMMENT 'Total amount the smallest monetary unit (e.g., cents).',
  CUSTOMER_ID TEXT COMMENT 'Unique identifier for the customer.',
  CUSTOMER_EMAIL_ADDRESS TEXT not null COMMENT 'The email address, as entered by the customer. The email address was not verified.',
  PROCESSING_TIMESTAMP TIMESTAMP_LTZ not null COMMENT 'The processing timestamp in the current session’s time zone.'
) COMMENT='One record per order. Includes cancelled and deleted orders.';
CREATE TABLE line_items (
  LINE_ITEM_ID TEXT not null COMMENT 'Primary key of the lines_item_id table',
  ORDER_ID TEXT COMMENT 'An internal ID that identifies an order in the online shop.',
  SKU TEXT COMMENT 'The purchased article number'
) COMMENT='A single article that is part of an order.';
""".strip()
    assert actual == expected


def test_to_sql_ddl_snowflake_escapes_quotes_in_comments():
    """Apostrophes and backslashes in descriptions must not break the single-quoted COMMENT literals."""
    actual = DataContract(
        data_contract_str="""
apiVersion: v3.1.0
kind: DataContract
id: snowflake-escaping
name: Snowflake Escaping
version: 1.0.0
status: active
schema:
- name: extracts
  description: The extractor's table, stored under C:\\data.
  properties:
  - name: amount
    logicalType: number
    description: The extractor's amount.
"""
    ).export("sql", sql_server_type="snowflake")
    expected = """
-- Data Contract: snowflake-escaping
-- SQL Dialect: snowflake
CREATE TABLE extracts (
  amount NUMBER COMMENT 'The extractor''s amount.'
) COMMENT='The extractor''s table, stored under C:\\\\data.';
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
  discounts ARRAY<STRUCT<discount_code:STRING,discount_amount:BIGINT>> COMMENT "This is an array of records"
) COMMENT "One record per order. Includes cancelled and deleted orders.";
CREATE OR REPLACE TABLE datacontract_test_2.orders_latest.line_items (
  lines_item_id STRING not null COMMENT "Primary key of the lines_item_id table",
  order_id STRING COMMENT "An internal ID that identifies an order in the online shop.",
  sku STRING COMMENT "The purchased article number"
) COMMENT "A single article that is part of an order.";
""".strip()
    assert actual == expected


def test_to_sql_ddl_physical_name():
    actual = DataContract(data_contract_file="fixtures/postgres-export-physical-name/datacontract.yaml").export("sql")
    expected = """
-- Data Contract: postgres-physical-name
-- SQL Dialect: postgres
CREATE TABLE my_table (
  FIELD_ONE text not null,
  FIELD_TWO integer,
  field_three timestamptz
);
""".strip()
    assert actual == expected


def test_to_sql_ddl_composite_primary_key():
    """Composite PKs should generate a table-level CONSTRAINT, not inline per-column primary key.

    Fixture (ODCS) has: order_id at primaryKeyPosition 2, product_id at position 1, note with no position.
    The constraint should list columns ordered by primaryKeyPosition (nulls last).
    """
    actual = DataContract(data_contract_file="fixtures/composite-pk-export/datacontract.yaml").export("sql")
    expected = """
-- Data Contract: composite-pk-test
-- SQL Dialect: postgres
CREATE TABLE orders (
  order_id integer not null,
  product_id integer not null,
  quantity integer,
  created_at timestamptz,
  note text,
  CONSTRAINT pk_orders PRIMARY KEY (product_id, order_id, note)
);
""".strip()
    assert actual == expected


def test_to_sql_ddl_single_primary_key():
    """Single PK should use inline primary key modifier (not a table-level CONSTRAINT)."""
    actual = DataContract(data_contract_file="fixtures/single-pk-export/datacontract.yaml").export("sql")
    expected = """
-- Data Contract: single-pk-test
-- SQL Dialect: postgres
CREATE TABLE users (
  user_id integer not null primary key,
  username text not null,
  email text
);
""".strip()
    assert actual == expected
    assert "CONSTRAINT pk_" not in actual


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
  discounts ARRAY<STRUCT<discount_code:STRING,discount_amount:BIGINT>> COMMENT "This is an array of records"
) COMMENT "One record per order. Includes cancelled and deleted orders.";
CREATE OR REPLACE TABLE datacontract_staging.orders_latest.line_items (
  lines_item_id STRING not null COMMENT "Primary key of the lines_item_id table",
  order_id STRING COMMENT "An internal ID that identifies an order in the online shop.",
  sku STRING COMMENT "The purchased article number"
) COMMENT "A single article that is part of an order.";
""".strip()
    assert actual == expected


VIEW_CONTRACT = """
apiVersion: v3.1.0
kind: DataContract
id: orders-view
name: orders-view
version: 1.0.0
status: active
schema:
  - name: orders_enriched
    physicalType: view
    description: One row per order with the customer's name.
    properties:
      - name: order_id
        logicalType: string
        required: true
        primaryKey: true
        description: Unique identifier of the order.
        transformSourceObjects:
          - bronze.orders.order_id
      - name: customer_id
        logicalType: string
        transformSourceObjects:
          - bronze.orders
      - name: customer_name
        logicalType: string
        transformSourceObjects:
          - bronze.orders
"""


def test_to_sql_ddl_view_postgres():
    actual = DataContract(data_contract_str=VIEW_CONTRACT).export("sql", sql_server_type="postgres")
    expected = """
-- Data Contract: orders-view
-- SQL Dialect: postgres
CREATE OR REPLACE VIEW orders_enriched AS
SELECT
  order_id,
  customer_id,
  customer_name
FROM bronze.orders;
""".strip()
    assert actual == expected


def test_to_sql_ddl_view_snowflake():
    actual = DataContract(data_contract_str=VIEW_CONTRACT).export("sql", sql_server_type="snowflake")
    expected = """
-- Data Contract: orders-view
-- SQL Dialect: snowflake
CREATE OR REPLACE VIEW orders_enriched (
  order_id COMMENT 'Unique identifier of the order.',
  customer_id,
  customer_name
) COMMENT='One row per order with the customer''s name.' AS
SELECT
  order_id,
  customer_id,
  customer_name
FROM bronze.orders;
""".strip()
    assert actual == expected


def test_to_sql_ddl_view_several_sources_is_a_draft():
    contract = VIEW_CONTRACT.removesuffix("bronze.orders\n") + "bronze.customers\n"
    actual = DataContract(data_contract_str=contract).export("sql", sql_server_type="postgres")
    assert actual.endswith("FROM bronze.orders\nJOIN bronze.customers ON <TODO: join condition>;")


def test_to_sql_ddl_view_without_sources_is_a_draft():
    contract = re.sub(r" +transformSourceObjects:\n( {10}- .*\n)+", "", VIEW_CONTRACT)
    actual = DataContract(data_contract_str=contract).export("sql", sql_server_type="postgres")
    assert actual.endswith("FROM <TODO: source object>;")


def test_to_sql_ddl_view_sqlserver_is_its_own_batch():
    contract = """
apiVersion: v3.1.0
kind: DataContract
id: orders
name: orders
version: 1.0.0
status: active
schema:
  - name: orders
    properties:
      - name: order_id
        logicalType: string
  - name: orders_v
    physicalType: view
    properties:
      - name: order_id
        logicalType: string
        transformSourceObjects:
          - orders
"""
    actual = DataContract(data_contract_str=contract).export("sql", sql_server_type="sqlserver")
    expected = """
-- Data Contract: orders
-- SQL Dialect: sqlserver
CREATE TABLE orders (
  order_id varchar
);
GO
CREATE OR ALTER VIEW orders_v AS
SELECT
  order_id
FROM orders;
GO
""".strip()
    assert actual == expected
