from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

runner = CliRunner()

CONTRACT = """
apiVersion: v3.0.2
kind: DataContract
id: quality_id_filter_test
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
      # Passes: the fixture has 5 rows.
      - id: orders_not_empty
        type: library
        metric: rowCount
        mustBeGreaterThan: 1
        tags: ["critical", "cheap"]
      # Fails: the fixture has an amount of -5.
      - id: amounts_are_positive
        type: sql
        description: amounts are positive
        query: SELECT MIN(amount) FROM orders
        mustBeGreaterThan: 0
        tags: ["expensive"]
    properties:
      # Fails: the fixture repeats order_id 2.
      - name: order_id
        logicalType: integer
        quality:
          - id: order_id_is_unique
            type: library
            metric: duplicateValues
            mustBe: 0
            tags: ["critical"]
      - name: email
        logicalType: string
        quality:
          # No id, no tags: only reachable without a filter.
          - type: library
            metric: nullValues
            mustBe: 0
"""


def test_quality_id_runs_only_that_rule():
    run = DataContract(data_contract_str=CONTRACT, quality_ids={"order_id_is_unique"}).test()
    print(run.pretty())
    assert [check.type for check in run.checks] == ["field_duplicate_values"]
    assert run.result == "failed"


def test_quality_id_skips_schema_checks():
    run = DataContract(data_contract_str=CONTRACT, quality_ids={"orders_not_empty"}).test()
    print(run.pretty())
    assert [check.type for check in run.checks] == ["row_count"]
    assert run.result == "passed"


def test_quality_id_accepts_multiple_ids():
    run = DataContract(
        data_contract_str=CONTRACT,
        quality_ids={"orders_not_empty", "amounts_are_positive"},
    ).test()
    print(run.pretty())
    assert sorted(check.type for check in run.checks) == ["model_quality_sql", "row_count"]


def test_unknown_quality_id_fails_the_run():
    """An id that matches nothing is a typo — testing nothing must not pass."""
    run = DataContract(data_contract_str=CONTRACT, quality_ids={"does_not_exist"}).test()
    print(run.pretty())
    assert run.result == "failed"
    assert "does_not_exist" in run.checks[0].reason
    assert "orders_not_empty" in run.checks[0].reason


def test_tag_runs_every_rule_carrying_it():
    run = DataContract(data_contract_str=CONTRACT, tags={"critical"}).test()
    print(run.pretty())
    assert sorted(check.type for check in run.checks) == ["field_duplicate_values", "row_count"]


def test_tag_accepts_multiple_tags():
    run = DataContract(data_contract_str=CONTRACT, tags={"cheap", "expensive"}).test()
    print(run.pretty())
    assert sorted(check.type for check in run.checks) == ["model_quality_sql", "row_count"]


def test_unknown_tag_runs_nothing():
    run = DataContract(data_contract_str=CONTRACT, tags={"nightly"}).test()
    print(run.pretty())
    assert len(run.checks) == 0


def test_rules_without_id_or_tags_are_never_matched():
    run = DataContract(data_contract_str=CONTRACT, tags={"critical"}).test()
    assert not [check for check in run.checks if check.type == "field_null_values"]


def test_quality_id_and_tag_combine():
    """Both filters apply; here they select disjoint rules."""
    run = DataContract(
        data_contract_str=CONTRACT,
        quality_ids={"amounts_are_positive"},
        tags={"critical"},
    ).test()
    print(run.pretty())
    assert len(run.checks) == 0


def test_checks_report_the_id_and_tags_of_their_rule():
    """The results say which rule produced them, so it can be re-run by id."""
    run = DataContract(data_contract_str=CONTRACT).test()
    print(run.pretty())
    by_type = {check.type: check for check in run.checks}
    assert by_type["row_count"].quality_id == "orders_not_empty"
    assert by_type["row_count"].tags == ["critical", "cheap"]
    assert by_type["field_null_values"].quality_id is None
    assert by_type["field_null_values"].tags is None
    assert by_type["field_is_present"].quality_id is None


def test_quality_id_cli_option():
    result = runner.invoke(
        app,
        ["test", "--quality-id", "orders_not_empty", "./fixtures/quality-id/datacontract.yaml"],
    )
    assert result.exit_code == 0


def test_quality_id_cli_unknown_id_exits_non_zero():
    result = runner.invoke(
        app,
        ["test", "--quality-id", "typo", "./fixtures/quality-id/datacontract.yaml"],
    )
    assert result.exit_code == 1
    assert "typo" in result.stdout


def test_tag_cli_option():
    result = runner.invoke(
        app,
        ["test", "--tag", "critical, cheap", "./fixtures/quality-id/datacontract.yaml"],
    )
    assert result.exit_code == 0


def test_quality_id_cli_empty_value():
    result = runner.invoke(
        app,
        ["test", "--quality-id", "", "./fixtures/quality-id/datacontract.yaml"],
    )
    assert result.exit_code == 1
    assert "Empty --quality-id specified" in result.stdout
