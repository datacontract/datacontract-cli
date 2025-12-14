import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract
from datacontract.export.dbt_exporter import to_dbt_staging_sql

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "./fixtures/dbt/export/datacontract.odcs.yaml",
            "--format",
            "dbt-staging-sql",
            "--schema-name",
            "orders",
        ],
    )
    print(result.stdout)
    assert result.exit_code == 0


def test_to_dbt_staging():
    data_contract = DataContract(data_contract_file="fixtures/dbt/export/datacontract.odcs.yaml").get_data_contract()
    expected = """
select
    order_id,
    order_total,
    order_status,
    user_id
from {{ source('orders-unit-test', 'orders') }}
"""

    # Find the orders schema
    orders_schema = next((s for s in data_contract.schema_ if s.name == "orders"), None)
    result = to_dbt_staging_sql(data_contract, "orders", orders_schema)

    assert yaml.safe_load(result) == yaml.safe_load(expected)
