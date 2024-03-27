import logging

from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(app, ["export", "./examples/postgres-export/datacontract.yaml", "--format", "sql"])
    assert result.exit_code == 0


def test_to_sql_ddl_postgres():
    actual = DataContract(data_contract_file="./examples/postgres-export/datacontract.yaml").export("sql")
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
    actual = DataContract(data_contract_file="./examples/snowflake/datacontract.yaml").export("sql")
    expected = """
-- Data Contract: urn:datacontract:checkout:snowflake_orders_pii_v2
-- SQL Dialect: snowflake
CREATE TABLE orders (
  ORDER_ID TEXT not null,
  ORDER_TIMESTAMP TIMESTAMP_TZ not null,
  ORDER_TOTAL NUMBER not null,
  CUSTOMER_ID TEXT,
  CUSTOMER_EMAIL_ADDRESS TEXT not null
);
CREATE TABLE line_items (
  LINE_ITEM_ID TEXT not null,
  ORDER_ID TEXT,
  SKU TEXT
);
""".strip()
    assert actual == expected


def test_to_sql_ddl_databricks_unity_catalog():
    actual = DataContract(data_contract_file="./examples/databricks-sql/datacontract.yaml").export("sql")
    expected = """
-- Data Contract: urn:datacontract:checkout:orders-latest
-- SQL Dialect: databricks
CREATE TABLE datacontract_test_2.orders_latest.orders (
  order_id STRING not null,
  order_timestamp TIMESTAMP not null,
  order_total BIGINT not null,
  customer_id STRING,
  customer_email_address STRING not null
);
CREATE TABLE datacontract_test_2.orders_latest.line_items (
  line_item_id STRING not null,
  order_id STRING,
  sku STRING
);
""".strip()
    assert actual == expected
