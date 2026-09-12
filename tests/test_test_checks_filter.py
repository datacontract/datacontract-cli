from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

runner = CliRunner()

ROW_COUNT_CONTRACT = """
apiVersion: v3.0.2
kind: DataContract
id: row_count_category_test
version: 1.0.0
status: active
servers:
  - server: local
    type: local
    path: ./fixtures/diagnostics/data/orders.csv
    format: csv
schema:
  - name: orders
    quality:
      - type: library
        metric: rowCount
        mustBeGreaterThan: 1
    properties:
      - name: order_id
        logicalType: integer
"""


def test_checks_quality_only_runs_row_count_rule():
    run = DataContract(
        data_contract_str=ROW_COUNT_CONTRACT,
        check_categories={"quality"},
    ).test()
    print(run.pretty())
    assert run.result == "passed"
    assert [check.type for check in run.checks] == ["row_count"]


def test_checks_schema_only():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract.yaml",
        check_categories={"schema"},
    )
    run = data_contract.test()
    print(run.pretty())
    assert run.result == "passed"
    assert all(check.category == "schema" for check in run.checks)
    assert len(run.checks) > 0


def test_checks_quality_only_no_quality_checks_defined():
    data_contract = DataContract(
        data_contract_file="fixtures/parquet/datacontract.yaml",
        check_categories={"quality"},
    )
    run = data_contract.test()
    print(run.pretty())
    # No quality checks defined in parquet fixture, so no checks should run
    assert len(run.checks) == 0


def test_checks_all_categories_same_as_default():
    run_all = DataContract(
        data_contract_file="fixtures/parquet/datacontract.yaml",
    ).test()

    run_explicit = DataContract(
        data_contract_file="fixtures/parquet/datacontract.yaml",
        check_categories={"schema", "quality", "servicelevel", "custom"},
    ).test()

    assert len(run_all.checks) == len(run_explicit.checks)
    assert run_all.result == run_explicit.result


def test_checks_cli_option():
    result = runner.invoke(
        app,
        ["test", "--checks", "schema", "./fixtures/parquet/datacontract.yaml"],
    )
    assert result.exit_code == 0


def test_checks_cli_invalid_category():
    result = runner.invoke(
        app,
        ["test", "--checks", "invalid", "./fixtures/parquet/datacontract.yaml"],
    )
    assert result.exit_code == 1
    assert "Invalid --checks specified" in result.stdout
    assert "properties, quality, slaProperties, custom" in result.stdout
    assert "schema, servicelevel" in result.stdout


def test_checks_cli_empty_category():
    result = runner.invoke(
        app,
        ["test", "--checks", "", "./fixtures/parquet/datacontract.yaml"],
    )
    assert result.exit_code == 1
    assert "Empty --checks specified" in result.stdout
    assert "Available" in result.stdout


def test_checks_cli_multiple_categories():
    result = runner.invoke(
        app,
        ["test", "--checks", "schema,quality", "./fixtures/parquet/datacontract.yaml"],
    )
    assert result.exit_code == 0


def test_checks_cli_odcs_aliases():
    result = runner.invoke(
        app,
        ["test", "--checks", "properties,slaProperties", "./fixtures/parquet/datacontract.yaml"],
    )
    assert result.exit_code == 0


def test_checks_cli_case_insensitive():
    result = runner.invoke(
        app,
        ["test", "--checks", "SLAProperties,Schema", "./fixtures/parquet/datacontract.yaml"],
    )
    assert result.exit_code == 0


def test_checks_cli_spaces_after_comma():
    result = runner.invoke(
        app,
        ["test", "--checks", "schema, quality", "./fixtures/parquet/datacontract.yaml"],
    )
    assert result.exit_code == 0
