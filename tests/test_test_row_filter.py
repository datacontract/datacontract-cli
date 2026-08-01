from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

runner = CliRunner()

# fixtures/diagnostics/data/orders.csv has 5 rows; order_id <= 2 matches 3 of them.
CONTRACT = "fixtures/row-filter/datacontract.yaml"

TWO_SCHEMA_CONTRACT = """
apiVersion: v3.0.2
kind: DataContract
id: row-filter-two-schemas
version: 1.0.0
status: active
servers:
  - server: local
    type: local
    path: ./fixtures/diagnostics/data/orders.csv
    format: csv
schema:
  - name: orders
    properties:
      - name: order_id
        logicalType: integer
  - name: customers
    properties:
      - name: order_id
        logicalType: integer
"""


def test_where_filters_rows():
    run = DataContract(data_contract_file=CONTRACT, where="order_id <= 2").test()
    print(run.pretty())
    assert run.result == "passed"
    assert run.filters == {"orders": "order_id <= 2"}
    row_count_check = next(c for c in run.checks if c.type == "row_count")
    assert "order_id <= 2" in row_count_check.implementation


def test_without_filter_fails():
    run = DataContract(data_contract_file=CONTRACT).test()
    print(run.pretty())
    assert run.result == "failed"
    assert run.filters is None


def test_filter_scopes_predicate_to_schema():
    run = DataContract(data_contract_file=CONTRACT, filters={"orders": "order_id <= 2"}).test()
    print(run.pretty())
    assert run.result == "passed"
    assert run.filters == {"orders": "order_id <= 2"}


def test_where_with_multiple_schemas_fails():
    run = DataContract(data_contract_str=TWO_SCHEMA_CONTRACT, where="order_id <= 2").test()
    print(run.pretty())
    assert run.result == "failed"
    assert any("--where is ambiguous" in str(check.reason) for check in run.checks)


def test_where_with_multiple_schemas_and_schema_name():
    run = DataContract(data_contract_str=TWO_SCHEMA_CONTRACT, schema_name="orders", where="order_id <= 2").test()
    print(run.pretty())
    assert run.filters == {"orders": "order_id <= 2"}


def test_filter_unknown_schema_fails():
    run = DataContract(data_contract_file=CONTRACT, filters={"unknown": "order_id <= 2"}).test()
    print(run.pretty())
    assert run.result == "failed"
    assert any("Filter schema(s) not found in data contract: unknown" in str(check.reason) for check in run.checks)


def test_cli_where():
    result = runner.invoke(app, ["test", CONTRACT, "--where", "order_id <= 2"])
    assert result.exit_code == 0
    assert "Row filter: orders WHERE order_id <= 2" in result.stdout


def test_cli_filter():
    result = runner.invoke(app, ["test", CONTRACT, "--filter", "orders=order_id <= 2"])
    assert result.exit_code == 0
    assert "Row filter: orders WHERE order_id <= 2" in result.stdout


def test_cli_filter_without_predicate():
    result = runner.invoke(app, ["test", CONTRACT, "--filter", "orders"])
    assert result.exit_code == 1
    assert "Invalid --filter specified" in result.stdout


def test_cli_filter_forgotten_schema_prefix():
    # "amount=50" parses as schema "amount", which does not exist in the contract.
    result = runner.invoke(app, ["test", CONTRACT, "--filter", "amount=50"])
    assert result.exit_code == 1
    assert "Filter schema(s) not found" in result.stdout


def test_cli_filter_duplicate_schema():
    result = runner.invoke(
        app, ["test", CONTRACT, "--filter", "orders=order_id <= 2", "--filter", "orders=order_id > 0"]
    )
    assert result.exit_code == 1
    assert "Duplicate --filter for schema 'orders'" in result.stdout


def test_cli_where_and_filter_conflict():
    result = runner.invoke(app, ["test", CONTRACT, "--where", "order_id <= 2", "--filter", "orders=order_id <= 2"])
    assert result.exit_code == 1
    assert "Use either --where or --filter, not both." in result.stdout
