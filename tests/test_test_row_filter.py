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


def test_filter_filters_rows():
    run = DataContract(data_contract_file=CONTRACT, filter="order_id <= 2").test()
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


def test_filters_scopes_predicate_to_schema():
    run = DataContract(data_contract_file=CONTRACT, filters={"orders": "order_id <= 2"}).test()
    print(run.pretty())
    assert run.result == "passed"
    assert run.filters == {"orders": "order_id <= 2"}


def test_filter_with_multiple_schemas_fails():
    run = DataContract(data_contract_str=TWO_SCHEMA_CONTRACT, filter="order_id <= 2").test()
    print(run.pretty())
    assert run.result == "failed"
    assert any("--filter is ambiguous" in str(check.reason) for check in run.checks)


def test_filter_with_multiple_schemas_and_schema_name():
    run = DataContract(data_contract_str=TWO_SCHEMA_CONTRACT, schema_name="orders", filter="order_id <= 2").test()
    print(run.pretty())
    assert run.filters == {"orders": "order_id <= 2"}


def test_filters_unknown_schema_fails():
    run = DataContract(data_contract_file=CONTRACT, filters={"unknown": "order_id <= 2"}).test()
    print(run.pretty())
    assert run.result == "failed"
    assert any("Filter schema(s) not found" in str(check.reason) for check in run.checks)


def test_cli_filter():
    result = runner.invoke(app, ["test", CONTRACT, "--filter", "order_id <= 2"])
    assert result.exit_code == 0
    assert "Row filter: orders WHERE order_id <= 2" in result.stdout


def test_cli_filters():
    result = runner.invoke(app, ["test", CONTRACT, "--filters", '{"orders": "order_id <= 2"}'])
    assert result.exit_code == 0
    assert "Row filter: orders WHERE order_id <= 2" in result.stdout


def test_cli_filters_invalid_json():
    result = runner.invoke(app, ["test", CONTRACT, "--filters", "orders=order_id <= 2"])
    assert result.exit_code == 1
    assert "Invalid --filters specified: not valid JSON" in result.stdout


def test_cli_filters_not_an_object():
    result = runner.invoke(app, ["test", CONTRACT, "--filters", '["order_id <= 2"]'])
    assert result.exit_code == 1
    assert "Invalid --filters specified" in result.stdout


def test_cli_filters_unknown_schema():
    result = runner.invoke(app, ["test", CONTRACT, "--filters", '{"unknown": "order_id <= 2"}'])
    assert result.exit_code == 1
    assert "Filter schema(s) not found" in result.stdout


def test_cli_filter_and_filters_conflict():
    result = runner.invoke(
        app, ["test", CONTRACT, "--filter", "order_id <= 2", "--filters", '{"orders": "order_id <= 2"}']
    )
    assert result.exit_code == 1
    assert "Use either --filter or --filters, not both." in result.stdout


def test_invalid_filter_predicate_errors_instead_of_failing():
    """A predicate that does not compile is a configuration problem, not a data violation."""
    run = DataContract(data_contract_file=CONTRACT, filter="no_such_column <= 2").test()
    print(run.pretty())
    assert run.result == "error"
    assert any("Could not apply row filter" in str(check.reason) for check in run.checks)
