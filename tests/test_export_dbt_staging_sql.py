import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.export.dbt_converter import to_dbt_staging_sql
from datacontract.model.data_contract_specification import DataContractSpecification

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "./fixtures/dbt/export/datacontract.yaml",
            "--format",
            "dbt-staging-sql",
            "--model",
            "orders",
        ],
    )
    print(result.stdout)
    assert result.exit_code == 0


def test_to_dbt_staging():
    data_contract = DataContractSpecification.from_file("fixtures/dbt/export/datacontract.yaml")
    expected = """
select 
    order_id,
    order_total,
    order_status,
    user_id
from {{ source('orders-unit-test', 'orders') }}
"""

    result = to_dbt_staging_sql(data_contract, "orders", data_contract.models.get("orders"))

    assert yaml.safe_load(result) == yaml.safe_load(expected)
