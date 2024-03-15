import logging

from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(app, [
        "export",
        "./examples/postgres-export/datacontract.yaml",
        "--format", "sql"
    ])
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

