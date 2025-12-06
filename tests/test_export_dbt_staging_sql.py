import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.export.dbt_converter import to_dbt_staging_sql
from datacontract.imports.dcs_importer import convert_dcs_to_odcs
from datacontract_specification.model import DataContractSpecification

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
    dcs = DataContractSpecification.from_file("fixtures/dbt/export/datacontract.yaml")
    data_contract = convert_dcs_to_odcs(dcs)
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
