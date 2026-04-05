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


def test_to_sql_ddl_postgres_view():
    """Model with type=view should emit CREATE VIEW, not CREATE TABLE."""
    actual = DataContract(data_contract_file="fixtures/sql-view-export/datacontract.yaml").export("sql")
    expected = """
-- Data Contract: sql-view-export
-- SQL Dialect: postgres
CREATE VIEW my_view (
  col_a text not null,
  col_b integer
);
""".strip()
    assert actual == expected
    assert "CREATE VIEW" in actual
    assert "CREATE TABLE" not in actual
