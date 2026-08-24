from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

runner = CliRunner()

DIMENSION_CONTRACT = """
apiVersion: v3.0.2
kind: DataContract
id: dimension_filter_test
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
      - type: library
        metric: rowCount
        mustBeGreaterThan: 1
        dimension: completeness
      # Fails: the fixture has an amount of -5.
      - type: sql
        description: amounts are positive
        query: SELECT MIN(amount) FROM orders
        mustBeGreaterThan: 0
        dimension: accuracy
    properties:
      # Fails: the fixture repeats order_id 2.
      - name: order_id
        logicalType: integer
        quality:
          - type: library
            metric: duplicateValues
            mustBe: 0
            dimension: uniqueness
      - name: email
        logicalType: string
"""


def test_dimension_runs_only_matching_quality_rules():
    run = DataContract(
        data_contract_str=DIMENSION_CONTRACT,
        dimensions={"uniqueness"},
    ).test()
    print(run.pretty())
    assert [check.type for check in run.checks] == ["field_duplicate_values"]


def test_dimension_selecting_a_passing_rule_passes():
    run = DataContract(
        data_contract_str=DIMENSION_CONTRACT,
        dimensions={"completeness"},
    ).test()
    print(run.pretty())
    assert run.result == "passed"
    assert [check.type for check in run.checks] == ["row_count"]


def test_dimension_accepts_multiple_dimensions():
    run = DataContract(
        data_contract_str=DIMENSION_CONTRACT,
        dimensions={"completeness", "accuracy"},
    ).test()
    print(run.pretty())
    assert sorted(check.type for check in run.checks) == ["model_quality_sql", "row_count"]


def test_dimension_skips_schema_checks_of_other_dimensions():
    """The contract's schema checks are all conformity, so completeness excludes them."""
    run = DataContract(
        data_contract_str=DIMENSION_CONTRACT,
        dimensions={"completeness"},
    ).test()
    print(run.pretty())
    assert all(check.category == "quality" for check in run.checks)
    assert len(run.checks) == 1


def test_dimension_without_matching_rules_runs_nothing():
    run = DataContract(
        data_contract_str=DIMENSION_CONTRACT,
        dimensions={"timeliness"},
    ).test()
    print(run.pretty())
    assert len(run.checks) == 0


BUILTIN_CONTRACT = """
apiVersion: v3.0.2
kind: DataContract
id: builtin_dimension_test
version: 1.0.0
status: active
servers:
  - server: local
    type: local
    path: ./fixtures/diagnostics/data/orders.csv
    format: csv
slaProperties:
  - property: freshness
    element: orders.order_id
    value: 100000
    unit: d
  - property: retention
    element: orders.order_id
    value: 1
    unit: y
schema:
  - name: orders
    properties:
      - name: order_id
        logicalType: integer
        required: true
        unique: true
      - name: email
        logicalType: string
"""


def test_builtin_required_check_maps_to_completeness():
    run = DataContract(data_contract_str=BUILTIN_CONTRACT, dimensions={"completeness"}).test()
    print(run.pretty())
    assert [check.type for check in run.checks] == ["field_required"]


def test_builtin_unique_check_maps_to_uniqueness():
    run = DataContract(data_contract_str=BUILTIN_CONTRACT, dimensions={"uniqueness"}).test()
    print(run.pretty())
    assert [check.type for check in run.checks] == ["field_unique"]


def test_builtin_presence_check_maps_to_conformity():
    """A CSV source emits no type checks, so presence is the conformity schema check here."""
    run = DataContract(data_contract_str=BUILTIN_CONTRACT, dimensions={"conformity"}).test()
    print(run.pretty())
    assert {check.type for check in run.checks} == {"field_is_present", "servicelevel_retention"}


def test_builtin_dimension_mapping():
    """The classification of every built-in check, as documented."""
    from datacontract.engines.checks.dimensions import default_dimension

    assert default_dimension("field_required") == "completeness"
    assert default_dimension("field_primary_key_required") == "completeness"
    assert default_dimension("field_unique") == "uniqueness"
    assert default_dimension("field_primary_key_unique") == "uniqueness"
    assert default_dimension("primary_key_unique") == "uniqueness"
    for check_type in (
        "field_is_present",
        "field_type",
        "field_physical_type",
        "field_nested_type",
        "field_nested_physical_type",
        "field_regex",
        "field_enum",
        "field_min_length",
        "field_max_length",
        "field_minimum",
        "field_maximum",
        "field_not_equal",
        "schema",
        "servicelevel_retention",
    ):
        assert default_dimension(check_type) == "conformity", check_type
    assert default_dimension("servicelevel_freshness") == "timeliness"
    assert default_dimension("row_count") is None  # quality rules: author-declared only
    assert default_dimension(None) is None


def test_builtin_freshness_maps_to_timeliness():
    run = DataContract(data_contract_str=BUILTIN_CONTRACT, dimensions={"timeliness"}).test()
    print(run.pretty())
    assert [check.type for check in run.checks] == ["servicelevel_freshness"]


def test_builtin_retention_maps_to_conformity():
    """The dataset conforms to the retention period it promises."""
    run = DataContract(data_contract_str=BUILTIN_CONTRACT, dimensions={"conformity"}).test()
    print(run.pretty())
    assert [c for c in run.checks if c.type == "servicelevel_retention"]
    # and no other dimension picks it up
    for dimension in ("accuracy", "completeness", "consistency", "coverage", "timeliness", "uniqueness"):
        other = DataContract(data_contract_str=BUILTIN_CONTRACT, dimensions={dimension}).test()
        assert not [c for c in other.checks if c.type == "servicelevel_retention"], dimension


def test_every_schema_and_servicelevel_check_has_a_dimension():
    """A new built-in check without a mapping would be silently unreachable."""
    from datacontract.engines.checks.create_checks import create_checks
    from datacontract.lint import resolve

    data_contract = resolve.resolve_data_contract(data_contract_str=BUILTIN_CONTRACT, inline_references=False)
    specs = create_checks(data_contract, data_contract.servers[0])
    unmapped = [s.type for s in specs if s.category == "schema" and s.dimension is None]
    assert not unmapped, f"schema checks without a dimension: {sorted(set(unmapped))}"


def test_author_dimension_wins_over_the_builtin_default():
    """An explicit quality.dimension is never overridden by the mapping."""
    from datacontract.engines.checks.create_checks import create_checks
    from datacontract.lint import resolve

    data_contract = resolve.resolve_data_contract(data_contract_str=DIMENSION_CONTRACT, inline_references=False)
    specs = create_checks(data_contract, data_contract.servers[0])
    by_type = {s.type: s.dimension for s in specs}
    # field_duplicate_values would map to uniqueness by name alone; the author said so too
    assert by_type["field_duplicate_values"] == "uniqueness"
    assert by_type["row_count"] == "completeness"
    assert by_type["model_quality_sql"] == "accuracy"


def test_quality_rules_without_dimension_are_never_matched():
    run = DataContract(
        data_contract_file="fixtures/quality-local-fallback/datacontract.yaml",
        dimensions={"accuracy"},
    ).test()
    print(run.pretty())
    assert len(run.checks) == 0


def test_dimension_combines_with_checks_filter():
    """--checks and --dimension both apply; here they select disjoint sets."""
    run = DataContract(
        data_contract_str=DIMENSION_CONTRACT,
        check_categories={"schema"},
        dimensions={"uniqueness"},
    ).test()
    print(run.pretty())
    assert len(run.checks) == 0


def test_no_dimension_filter_runs_everything():
    run_all = DataContract(data_contract_str=DIMENSION_CONTRACT).test()
    assert len(run_all.checks) > 3
    assert any(check.category == "schema" for check in run_all.checks)


def test_dimension_reports_the_failing_rule():
    """The filter selects checks, it does not change their outcome."""
    run = DataContract(
        data_contract_str=DIMENSION_CONTRACT,
        dimensions={"accuracy"},
    ).test()
    print(run.pretty())
    assert run.result == "failed"
    assert [check.type for check in run.checks] == ["model_quality_sql"]


def test_dimension_cli_option():
    result = runner.invoke(
        app,
        ["test", "--dimension", "completeness", "./fixtures/quality-dimensions/datacontract.yaml"],
    )
    assert result.exit_code == 0


def test_dimension_cli_invalid_dimension():
    result = runner.invoke(
        app,
        ["test", "--dimension", "freshness", "./fixtures/quality-dimensions/datacontract.yaml"],
    )
    assert result.exit_code == 1
    assert "Invalid --dimension specified" in result.stdout


def test_dimension_cli_empty_dimension():
    result = runner.invoke(
        app,
        ["test", "--dimension", "", "./fixtures/quality-dimensions/datacontract.yaml"],
    )
    assert result.exit_code == 1
    assert "Empty --dimension specified" in result.stdout
    assert "Available" in result.stdout


def test_dimension_cli_spaces_after_comma():
    result = runner.invoke(
        app,
        ["test", "--dimension", "completeness, uniqueness", "./fixtures/quality-dimensions/datacontract.yaml"],
    )
    assert result.exit_code == 0


def test_a_json_schema_check_carries_the_conformity_dimension():
    """Every check the engine emits shares the type "schema", so one dimension covers all."""
    run = DataContract(data_contract_file="fixtures/local-json/datacontract.yaml").test()

    schema_checks = [c for c in run.checks if c.engine == "jsonschema"]
    assert schema_checks
    assert all(c.dimension == "conformity" for c in schema_checks)
