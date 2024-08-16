from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(app, ["export", "./fixtures/postgres-export/datacontract.yaml", "--format", "sql-query"])
    assert result.exit_code == 0


def test_to_sql_query_postgres():
    actual = DataContract(data_contract_file="fixtures/postgres-export/datacontract.yaml").export("sql-query")
    expected = """
-- Data Contract: postgres
-- SQL Dialect: postgres
select
    field_one,
    field_two,
    field_three
from my_table
"""
    assert actual.strip() == expected.strip()


def test_to_sql_query_snowflake():
    actual = DataContract(data_contract_file="fixtures/snowflake/datacontract.yaml").export("sql-query", model="orders")
    expected = """
-- Data Contract: urn:datacontract:checkout:snowflake_orders_pii_v2
-- SQL Dialect: snowflake
select
    ORDER_ID,
    ORDER_TIMESTAMP,
    ORDER_TOTAL,
    CUSTOMER_ID,
    CUSTOMER_EMAIL_ADDRESS,
    PROCESSING_TIMESTAMP
from orders
"""
    assert actual.strip() == expected.strip()
