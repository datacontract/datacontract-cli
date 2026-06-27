"""Unit + integration tests for `datacontract dbt sync` (PR B MVP)."""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from unittest import mock

import pytest
import yaml
from open_data_contract_standard.model import DataQuality
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.integration.dbt_sync import (
    ModelResolution,
    _attach_test_config,
    _bound_violation_predicate,
    _build_singular_sql,
    _describe_dbt_test,
    _disambiguate_singular_filenames,
    _ensure_dbt_project,
    _rewrite_relationships_to_ref,
    _row_count_singular_test,
    _singular_tests_for_qualities,
    _sql_literal,
    check_dbt_on_path,
    find_contract,
    generate_dbt_tests,
    generate_dbt_tests_for_schema,
    parse_run_results,
    resolve_model_names,
    run_dbt_test,
    run_tests,
)
from datacontract.lint.resolve import resolve_data_contract
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import Run

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "dbt_sync"
CONTRACT_PATH = FIXTURE_DIR / "orders.odcs.yaml"
DBT_PROJECT_TEMPLATE = FIXTURE_DIR / "dbt_project"

# Default-config relative paths matching the fixture dbt project (models/, tests/).
# Runtime resolution honors `model-paths` / `test-paths` from `dbt_project.yml`;
# the fixture sticks to dbt's defaults, so tests can hard-code these.
GENERATED_MODELS_DIR = Path("models") / "datacontract_cli"
GENERATED_TESTS_DIR = Path("tests") / "datacontract_cli"


def _copy_dbt_project(tmp_path: Path) -> Path:
    """Materialize a fresh copy of the fixture dbt project under tmp_path."""
    dest = tmp_path / "dbt_project"
    shutil.copytree(DBT_PROJECT_TEMPLATE, dest)
    return dest


@dataclass
class _SyncResult:
    contract_path: Path
    project_dir: Path
    written_yaml: List[Path]
    written_sql: List[Path]
    run: Optional[Run]


def sync(
    *,
    contract: Optional[str],
    project_dir: Optional[Path],
    schema_name: str = "all",
    model_resolution: ModelResolution = ModelResolution.name,
    target: Optional[str] = None,
    profiles_dir: Optional[Path] = None,
    skip_tests: bool = False,
    prune: bool = False,
) -> _SyncResult:
    """End-to-end orchestration helper for tests — mirrors what the CLI does."""
    if not skip_tests:
        check_dbt_on_path()
    gen = generate_dbt_tests(
        contract=contract,
        project_dir=project_dir,
        schema_name=schema_name,
        model_resolution=model_resolution,
        prune=prune,
    )
    if skip_tests:
        gen.generation_run.log_info("Skipped `dbt test` (--skip-tests).")
        gen.generation_run.finish()
        run = gen.generation_run
    else:
        run = run_tests(gen, target=target, profiles_dir=profiles_dir)
    return _SyncResult(
        contract_path=gen.contract_path,
        project_dir=gen.project_dir,
        written_yaml=gen.written_yaml,
        written_sql=gen.written_sql,
        run=run,
    )


# ---------------------------------------------------------------------------
# Contract resolution
# ---------------------------------------------------------------------------


def test_find_contract_single_match(tmp_path: Path):
    target = tmp_path / "nested" / "x.odcs.yaml"
    target.parent.mkdir(parents=True)
    target.write_text("kind: DataContract\n")
    assert find_contract(tmp_path) == target


def test_find_contract_none_raises(tmp_path: Path):
    with pytest.raises(DataContractException, match="No `\\*.odcs.yaml`"):
        find_contract(tmp_path)


def test_find_contract_ambiguous_raises(tmp_path: Path):
    (tmp_path / "a.odcs.yaml").write_text("")
    (tmp_path / "b.odcs.yaml").write_text("")
    with pytest.raises(DataContractException, match="Multiple"):
        find_contract(tmp_path)


# ---------------------------------------------------------------------------
# dbt project resolution
# ---------------------------------------------------------------------------


def test_ensure_dbt_project_missing_raises(tmp_path: Path):
    with pytest.raises(DataContractException, match=r"dbt_project\.yml.*not found.*--project-dir"):
        _ensure_dbt_project(tmp_path)


# ---------------------------------------------------------------------------
# dbt PATH preflight
# ---------------------------------------------------------------------------


def test_check_dbt_on_path_missing(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _: None)
    with pytest.raises(DataContractException, match="dbt not found on PATH"):
        check_dbt_on_path()


def test_check_dbt_on_path_present(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _: "/fake/dbt")
    assert check_dbt_on_path() == "/fake/dbt"


# ---------------------------------------------------------------------------
# In-place merge into the user's existing model entry
# ---------------------------------------------------------------------------


def _orders_model_sql(project: Path, name: str = "orders") -> Path:
    sql = project / "models" / f"{name}.sql"
    sql.write_text("select 'B0000001' as order_id, 'pending' as order_status, 100 as order_total")
    return sql


def _user_orders_schema(project: Path, *, entry_name: str = "orders") -> Path:
    """A hand-authored model entry: a comment, a user test, a user description, an extra column."""
    schema = project / "models" / "schema.yml"
    schema.write_text(
        "version: 2\n"
        "models:\n"
        f"  - name: {entry_name}   # the orders fact table\n"
        "    description: My own description.\n"
        "    columns:\n"
        "      - name: order_id\n"
        "        description: The PK.\n"
        "        data_tests:\n"
        "          - not_null\n"
        "      - name: extra_user_col\n"
        "        description: not declared by the contract\n"
    )
    return schema


def _model_entry(schema_path: Path, name: str = "orders") -> dict:
    doc = yaml.safe_load(schema_path.read_text())
    return next(m for m in doc["models"] if m["name"].lower() == name.lower())


def test_merge_into_existing_entry_replaces_old_collision_error(tmp_path: Path):
    """A model already defined in the user's YAML is merged into — not a hard error (old behavior)."""
    project = _copy_dbt_project(tmp_path)
    _orders_model_sql(project)
    schema = _user_orders_schema(project)

    result = sync(contract=str(CONTRACT_PATH), project_dir=project, skip_tests=True)
    assert result.run is not None  # did not raise

    entry = _model_entry(schema)
    cols = {c["name"]: c for c in entry["columns"]}
    # Pre-existing user test is adopted: tagged datacontract_cli (+ dc:type) but NOT dc:generated.
    not_null = cols["order_id"]["data_tests"][0]["not_null"]
    assert "datacontract_cli" in not_null["config"]["tags"]
    assert "dc:field_required" in not_null["config"]["tags"]
    assert "dc:generated" not in not_null["config"]["tags"]
    # A test the CLI created from nothing carries dc:generated.
    unique = cols["order_id"]["data_tests"][1]["unique"]
    assert "dc:generated" in unique["config"]["tags"]
    # The user's own column + its description are preserved.
    assert "extra_user_col" in cols
    assert cols["order_id"]["description"] == "The PK."


def test_merge_preserves_comments_and_is_idempotent(tmp_path: Path):
    project = _copy_dbt_project(tmp_path)
    _orders_model_sql(project)
    schema = _user_orders_schema(project)

    sync(contract=str(CONTRACT_PATH), project_dir=project, skip_tests=True)
    after_first = schema.read_text()
    assert "# the orders fact table" in after_first  # ruamel round-trip kept the comment

    sync(contract=str(CONTRACT_PATH), project_dir=project, skip_tests=True)
    assert schema.read_text() == after_first  # second sync is a no-op


def test_merge_columns_the_cli_creates_are_marked(tmp_path: Path):
    """Columns the CLI adds to host tests carry meta.datacontract_cli so cleanup can drop them."""
    project = _copy_dbt_project(tmp_path)
    _orders_model_sql(project)
    schema = _user_orders_schema(project)
    sync(contract=str(CONTRACT_PATH), project_dir=project, skip_tests=True)

    cols = {c["name"]: c for c in _model_entry(schema)["columns"]}
    assert cols["order_status"]["meta"]["datacontract_cli"] is True
    assert "meta" not in cols["extra_user_col"]  # user column untouched
    assert "meta" not in cols["order_id"]  # pre-existing user column not marked


def test_sync_creates_owned_sidecar_when_no_yaml_entry(tmp_path: Path):
    project = _copy_dbt_project(tmp_path)
    _orders_model_sql(project)  # model SQL exists, but no YAML entry anywhere

    sync(contract=str(CONTRACT_PATH), project_dir=project, skip_tests=True)

    sidecar = project / "models" / "orders.yml"
    assert sidecar.exists()
    text = sidecar.read_text()
    assert text.lstrip().startswith("# AUTO-GENERATED by `datacontract dbt sync`")
    entry = _model_entry(sidecar)
    # Owned sidecar: every test is generated; columns are not marked (whole file is ours).
    assert entry["config"]["meta"]["data_contract"] == "orders-sync-test"
    order_id = {c["name"]: c for c in entry["columns"]}["order_id"]
    assert "dc:generated" in order_id["data_tests"][0]["not_null"]["config"]["tags"]


def test_sync_skips_model_with_no_sql_or_entry(tmp_path: Path):
    """A contract model with neither a `.sql` nor a YAML entry can't be tested — warn and skip."""
    project = _copy_dbt_project(tmp_path)  # empty models dir, no orders.sql
    result = sync(contract=str(CONTRACT_PATH), project_dir=project, skip_tests=True)

    assert result.written_yaml == []
    assert not (project / "models" / "orders.yml").exists()
    assert any("nothing to test" in log.message for log in result.run.logs)


def test_sync_matches_model_case_insensitively(tmp_path: Path):
    """Contract schema `orders` matches a dbt model `ORDERS`, preserving the project's casing (#1254)."""
    project = _copy_dbt_project(tmp_path)
    _orders_model_sql(project, name="ORDERS")
    schema = _user_orders_schema(project, entry_name="ORDERS")

    result = sync(contract=str(CONTRACT_PATH), project_dir=project, skip_tests=True)

    assert _model_entry(schema, "ORDERS")["name"] == "ORDERS"  # file casing preserved
    # Singular SQL refs the actual dbt model name, not the contract's casing.
    assert any("ref('ORDERS')" in p.read_text() for p in result.written_sql)


def _custom_paths_project(tmp_path: Path, *, model_paths: list[str], test_paths: list[str]) -> Path:
    """Materialize a dbt project with non-default `model-paths` / `test-paths`."""
    project = tmp_path / "dbt_project"
    project.mkdir()
    (project / "dbt_project.yml").write_text(
        "name: 'custom_paths_fixture'\n"
        "version: '1.0.0'\n"
        "config-version: 2\n"
        "profile: 'custom_paths_fixture'\n"
        f"model-paths: {model_paths!r}\n"
        f"test-paths: {test_paths!r}\n"
    )
    for p in model_paths + test_paths:
        (project / p).mkdir(parents=True, exist_ok=True)
    return project


def test_sync_writes_to_configured_model_and_test_paths(tmp_path: Path):
    """Sidecar YAML + singular SQL must follow `model-paths` / `test-paths` from dbt_project.yml.

    Otherwise dbt won't pick the files up and `--select tag:datacontract_cli` matches nothing.
    """
    project = _custom_paths_project(tmp_path, model_paths=["src/models"], test_paths=["src/tests"])
    (project / "src" / "models" / "orders.sql").write_text("select 1 as order_id")
    sync(contract=str(CONTRACT_PATH), project_dir=project, skip_tests=True)

    assert (project / "src" / "models" / "orders.yml").exists()  # sidecar next to the model
    tests_dir = project / "src" / "tests" / "datacontract_cli"
    assert tests_dir.is_dir() and any(tests_dir.iterdir())
    # Default paths must stay empty.
    assert not (project / "tests" / "datacontract_cli").exists()


def test_sync_migrates_legacy_generated_dir(tmp_path: Path):
    """A leftover `<model-paths>/datacontract_cli/` from the old behavior is removed on sync."""
    project = _copy_dbt_project(tmp_path)
    _orders_model_sql(project)
    legacy = project / GENERATED_MODELS_DIR
    legacy.mkdir(parents=True, exist_ok=True)
    (legacy / "orders_sync_test__orders.yml").write_text("# stale parallel patch")

    sync(contract=str(CONTRACT_PATH), project_dir=project, skip_tests=True)
    assert not legacy.exists()


# ---------------------------------------------------------------------------
# Schema name + model resolution
# ---------------------------------------------------------------------------


def test_resolve_model_names_default_uses_name():
    odcs = resolve_data_contract(str(CONTRACT_PATH))
    assert resolve_model_names(odcs, ModelResolution.name) == {"orders": "orders"}


def test_resolve_model_names_physicalname_when_set():
    odcs = resolve_data_contract(str(CONTRACT_PATH))
    odcs.schema_[0].physicalName = "stg_orders"
    assert resolve_model_names(odcs, ModelResolution.physicalName) == {"orders": "stg_orders"}


def test_resolve_model_names_physicalname_unresolvable_raises():
    odcs = resolve_data_contract(str(CONTRACT_PATH))
    with pytest.raises(DataContractException, match="`--model-resolution physicalName`.*`orders`"):
        resolve_model_names(odcs, ModelResolution.physicalName)


def test_resolve_model_names_filter_unknown_raises():
    odcs = resolve_data_contract(str(CONTRACT_PATH))
    with pytest.raises(DataContractException, match="Schema `nope` not found"):
        resolve_model_names(odcs, ModelResolution.name, schema_filter="nope")


# ---------------------------------------------------------------------------
# Helper-level: severity, config wrapping, relationships rewrite, slugs
# ---------------------------------------------------------------------------


def test_attach_config_string_test():
    assert _attach_test_config("not_null", "warn") == {
        "not_null": {"config": {"severity": "warn", "tags": ["datacontract_cli"]}}
    }


def test_attach_config_dict_test():
    result = _attach_test_config({"accepted_values": {"values": [1, 2]}}, "error", check_type="field_enum")
    assert result == {
        "accepted_values": {
            "values": [1, 2],
            "config": {"severity": "error", "tags": ["datacontract_cli", "dc:field_enum"]},
        }
    }


@pytest.mark.parametrize(
    "test, expected",
    [
        ("not_null", "Check that field order_id has no missing values"),
        ("unique", "Check that field order_id has no duplicate values"),
        (
            {"accepted_values": {"values": ["pending", "shipped"]}},
            "Check that field order_id only contains enum values ['pending', 'shipped']",
        ),
        ({"accepted_values": {"values": ["X"]}}, "Check that field order_id is equal to X"),
        (
            {"relationships": {"to": "ref('customers')", "field": "id"}},
            "Check that field order_id references ref('customers').id",
        ),
        (
            {"dbt_utils.unique_combination_of_columns": {"combination_of_columns": ["order_id", "order_status"]}},
            "Check that model orders has a unique combination of columns order_id, order_status",
        ),
    ],
)
def test_describe_dbt_test_templates(test, expected):
    """Templates should read like the equivalent built-in check names so the published UI matches."""
    assert _describe_dbt_test(test, "order_id", "orders") == expected


def test_generate_outputs_emits_descriptions_for_typed_field_tests():
    """`not_null`, `unique`, `accepted_values` must carry a synthesized description
    so the published Run.check name shows the human-readable form."""
    odcs = resolve_data_contract(str(CONTRACT_PATH))
    schema_obj = odcs.schema_[0]
    model_dict, _ = generate_dbt_tests_for_schema(odcs, schema_obj, "orders", Run.create_run())

    cols = {c["name"]: c for c in model_dict["columns"]}
    descriptions_by_test_name = {}
    for col_name, col in cols.items():
        for entry in col.get("data_tests", []):
            ((test_name, args),) = entry.items()
            descriptions_by_test_name[(col_name, test_name)] = args.get("description")

    assert descriptions_by_test_name[("order_id", "not_null")] == "Check that field order_id has no missing values"
    assert descriptions_by_test_name[("order_id", "unique")] == "Check that field order_id has no duplicate values"
    assert "only contains enum values" in descriptions_by_test_name[("order_status", "accepted_values")]


def test_rewrite_relationships_to_ref():
    tests = [
        {"relationships": {"to": 'source("contract-id", "customers")', "field": "id"}},
        "not_null",
    ]
    rewritten = _rewrite_relationships_to_ref(tests)
    assert rewritten[0] == {"relationships": {"to": "ref('customers')", "field": "id"}}
    assert rewritten[1] == "not_null"


# ---------------------------------------------------------------------------
# Schema → outputs (sync-specific structure; per-mapping coverage lives in
# tests/test_dbt_test_mapping.py)
# ---------------------------------------------------------------------------


def test_generate_outputs_wraps_tests_with_tag_and_emits_singulars():
    odcs = resolve_data_contract(str(CONTRACT_PATH))
    schema_obj = odcs.schema_[0]
    run = Run.create_run()

    model_dict, singulars = generate_dbt_tests_for_schema(odcs, schema_obj, "orders", run)

    assert model_dict["name"] == "orders"
    assert model_dict["description"] == "Orders table"

    # Sync-specific: every YAML test carries the datacontract_cli tag plus a dc:<type> tag.
    cols = {c["name"]: c for c in model_dict["columns"]}
    expected_dc_tag = {
        "not_null": "dc:field_required",
        "unique": "dc:field_unique",
        "accepted_values": "dc:field_enum",
        "relationships": "dc:field_relationships",
    }
    for t in cols["order_id"]["data_tests"]:
        assert isinstance(t, dict)
        ((test_name, args),) = t.items()
        tags = args["config"]["tags"]
        assert tags[0] == "datacontract_cli"
        assert tags[1] == expected_dc_tag[test_name]

    # Single-PK in this fixture → no model-level data_tests.
    assert "data_tests" not in model_dict

    # Singular SQL: three field-level bounds (length + regex on order_id, range on order_total)
    # plus two quality.query rules (95% column rule, model-level row count).
    assert len(singulars) == 5
    assert all(s.filename.startswith("orders_sync_test__orders__") for s in singulars)
    assert all(s.filename.endswith(".sql") for s in singulars)
    assert any(s.description and "95%" in s.description for s in singulars)
    by_name = {s.filename: s for s in singulars}
    assert "length between 8 and 10" in by_name["orders_sync_test__orders__order_id__length.sql"].description
    assert "matches regex pattern" in by_name["orders_sync_test__orders__order_id__pattern.sql"].description
    assert "minimum of 0" in by_name["orders_sync_test__orders__order_total__range.sql"].description


def test_generate_outputs_composite_pk_emits_model_level_unique():
    odcs = resolve_data_contract(str(CONTRACT_PATH))
    schema_obj = odcs.schema_[0]
    # Promote order_status to composite PK alongside order_id.
    for prop in schema_obj.properties:
        if prop.name == "order_status":
            prop.primaryKey = True
            prop.primaryKeyPosition = 2

    model_dict, _ = generate_dbt_tests_for_schema(odcs, schema_obj, "orders", Run.create_run())

    assert "data_tests" in model_dict
    pk_test = model_dict["data_tests"][0]
    assert "dbt_utils.unique_combination_of_columns" in pk_test
    args = pk_test["dbt_utils.unique_combination_of_columns"]
    assert args["combination_of_columns"] == ["order_id", "order_status"]


def test_field_singular_tests_emit_portable_violation_predicates():
    """Length/range/regex bounds become singular SQL — no `dbt_expectations` dependency."""
    odcs = resolve_data_contract(str(CONTRACT_PATH))
    schema_obj = odcs.schema_[0]
    _, singulars = generate_dbt_tests_for_schema(odcs, schema_obj, "orders", Run.create_run())

    by_name = {s.filename: s for s in singulars}

    length = by_name["orders_sync_test__orders__order_id__length.sql"]
    assert 'LENGTH("order_id") < 8' in length.sql
    assert 'LENGTH("order_id") > 10' in length.sql
    assert '"order_id" IS NOT NULL' in length.sql
    assert "dbt_expectations" not in length.sql

    pattern = by_name["orders_sync_test__orders__order_id__pattern.sql"]
    # Adapter-portable regex via Jinja dispatch on `target.type`.
    assert "{% if target.type == 'bigquery' %}" in pattern.sql
    assert "REGEXP_CONTAINS" in pattern.sql
    assert "REGEXP_LIKE" in pattern.sql
    assert "!~" in pattern.sql
    assert "^B[0-9]+$" in pattern.sql

    rng = by_name["orders_sync_test__orders__order_total__range.sql"]
    assert '"order_total" < 0' in rng.sql
    assert '"order_total" > 1000000' in rng.sql


def test_row_count_singular_test_wraps_count_with_bound_predicate():
    """Declarative `rowCount` bound → `SELECT COUNT(*)` wrapped with a bound-violation predicate."""
    quality = DataQuality(metric="rowCount", mustBeGreaterThan=1000)
    test = _row_count_singular_test(quality, contract_id="orders_sync_test", model="orders")
    assert test is not None
    assert "SELECT COUNT(*) FROM {{ ref('orders') }}" in test.sql
    assert "metric_value <= 1000" in test.sql


def test_generate_outputs_singular_sql_carries_severity_and_tag():
    odcs = resolve_data_contract(str(CONTRACT_PATH))
    schema_obj = odcs.schema_[0]
    _, singulars = generate_dbt_tests_for_schema(odcs, schema_obj, "orders", Run.create_run())

    row_count = next(s for s in singulars if "row_count" in s.filename)
    # severity=error normalized from `severity: error` in the fixture
    assert "severity='error'" in row_count.sql
    assert "tags=['datacontract_cli', 'dc:custom_sql']" in row_count.sql


def test_build_singular_sql_wraps_query_with_violation_predicate():
    sql = _build_singular_sql(
        "SELECT COUNT(*) FROM orders",
        "metric_value IS NULL OR metric_value <= 1000",
        "error",
        "my-contract",
        "orders",
        check_type="row_count",
    )
    assert "AUTO-GENERATED" in sql
    assert "my-contract" in sql
    assert "severity='error'" in sql
    assert "tags=['datacontract_cli', 'dc:row_count']" in sql
    assert '"dc_model": "orders"' in sql  # Model is round-tripped through `meta`
    assert "dc_field" not in sql  # model-level test, no field
    assert "WITH _dc_metric (metric_value) AS (" in sql
    assert "SELECT COUNT(*) FROM orders" in sql
    assert "WHERE metric_value IS NULL OR metric_value <= 1000" in sql


@pytest.mark.parametrize(
    "kwargs, expected",
    [
        ({"mustBe": 0}, "metric_value IS NULL OR metric_value <> 0"),
        ({"mustNotBe": 0}, "metric_value IS NULL OR metric_value = 0"),
        ({"mustBeGreaterThan": 10}, "metric_value IS NULL OR metric_value <= 10"),
        ({"mustBeGreaterOrEqualTo": 10}, "metric_value IS NULL OR metric_value < 10"),
        ({"mustBeLessThan": 100}, "metric_value IS NULL OR metric_value >= 100"),
        ({"mustBeLessOrEqualTo": 100}, "metric_value IS NULL OR metric_value > 100"),
        ({"mustBeBetween": [1, 9]}, "metric_value IS NULL OR metric_value < 1 OR metric_value > 9"),
        ({"mustNotBeBetween": [1, 9]}, "metric_value IS NULL OR (metric_value >= 1 AND metric_value <= 9)"),
    ],
)
def test_bound_violation_predicate_branches(kwargs, expected):
    assert _bound_violation_predicate(DataQuality(**kwargs)) == expected


def test_bound_violation_predicate_returns_none_without_bound():
    # No `mustBe*` field set → no predicate can be built; caller must skip the test.
    assert _bound_violation_predicate(DataQuality(description="metric only, no bound")) is None


@pytest.mark.parametrize(
    "value, expected",
    [
        (True, "TRUE"),
        (False, "FALSE"),
        (42, "42"),
        (3.14, "3.14"),
        ("plain", "'plain'"),
        ("O'Brien", "'O''Brien'"),
    ],
)
def test_sql_literal(value, expected):
    assert _sql_literal(value) == expected


def test_singular_tests_skipped_when_query_has_no_bound():
    """A quality with `query` but no `mustBe*` bound is logged + skipped — we can't build a predicate."""
    run = Run.create_run()
    qualities = [DataQuality(query="SELECT 1", description="no bound here", name="orphan_query")]
    out = _singular_tests_for_qualities(qualities, "c", "orders", run)
    assert out == []
    assert any("no `mustBe*` bound" in log.message for log in run.logs)


def test_disambiguate_singular_filenames_renames_duplicates():
    from datacontract.integration.dbt_sync import SingularTest

    tests = [
        SingularTest(filename="c__m__lbl.sql", sql="-- a", description=None),
        SingularTest(filename="c__m__lbl.sql", sql="-- b", description=None),
        SingularTest(filename="c__m__lbl.sql", sql="-- c", description=None),
        SingularTest(filename="c__m__other.sql", sql="-- d", description=None),
    ]
    _disambiguate_singular_filenames(tests)

    assert [t.filename for t in tests] == [
        "c__m__lbl.sql",
        "c__m__lbl__2.sql",
        "c__m__lbl__3.sql",
        "c__m__other.sql",
    ]


# ---------------------------------------------------------------------------
# End-to-end (no dbt invocation)
# ---------------------------------------------------------------------------


def test_sync_skip_tests_writes_files(tmp_path: Path):
    project = _copy_dbt_project(tmp_path)
    _orders_model_sql(project)  # no YAML entry → owned sidecar
    result = sync(
        contract=str(CONTRACT_PATH),
        project_dir=project,
        skip_tests=True,
    )

    assert len(result.written_yaml) == 1
    yml = result.written_yaml[0]
    assert yml.exists()
    content = yml.read_text()
    assert content.lstrip().startswith("# AUTO-GENERATED")
    parsed = yaml.safe_load(content)
    assert parsed["models"][0]["name"] == "orders"

    # All singular SQL files materialize on disk: three field-level bounds
    # (length, regex, range) plus the two `quality.query` rules from the fixture.
    assert len(result.written_sql) == 5
    for sql_path in result.written_sql:
        assert sql_path.exists()
        assert "AUTO-GENERATED" in sql_path.read_text()


def test_sync_with_no_resolvable_schemas_still_wipes_stale_artifacts(tmp_path: Path):
    """A contract that resolves to zero models must still wipe prior generated artifacts —
    otherwise old `tag:datacontract_cli` files from an earlier run keep getting executed."""
    project = _copy_dbt_project(tmp_path)
    stale_legacy = project / GENERATED_MODELS_DIR / "stale.yml"
    stale_sql = project / GENERATED_TESTS_DIR / "stale.sql"
    stale_legacy.parent.mkdir(parents=True, exist_ok=True)
    stale_sql.parent.mkdir(parents=True, exist_ok=True)
    stale_legacy.write_text("# stale")
    stale_sql.write_text("-- stale")

    empty_contract = tmp_path / "empty.odcs.yaml"
    empty_contract.write_text(
        "kind: DataContract\napiVersion: v3.1.0\nid: empty-contract\nname: Empty\nversion: 1.0.0\nstatus: active\n"
    )

    sync(contract=str(empty_contract), project_dir=project, skip_tests=True)

    assert not stale_sql.exists()  # singular-SQL dir is wiped + regenerated
    assert not (project / GENERATED_MODELS_DIR).exists()  # legacy parallel-YAML dir is migrated away


def test_sync_missing_contract_raises(tmp_path: Path):
    project = _copy_dbt_project(tmp_path)
    with pytest.raises(DataContractException, match="not found"):
        sync(
            contract=str(tmp_path / "missing.yaml"),
            project_dir=project,
            skip_tests=True,
        )


# ---------------------------------------------------------------------------
# Metadata sync (description / config.meta / tags) + --prune
# ---------------------------------------------------------------------------

_TAGGED_CONTRACT = """\
kind: DataContract
apiVersion: v3.1.0
id: tagged-contract
name: Tagged
version: 1.0.0
status: active
team:
  name: data-eng
schema:
  - name: orders
    description: Orders model from the contract.
    tags: [pii, gold]
    properties:
      - name: order_id
        required: true
        unique: true
        primaryKey: true
        primaryKeyPosition: 1
        description: The order identifier.
        tags: [identifier]
"""


def _write(tmp_path: Path, name: str, body: str) -> Path:
    p = tmp_path / name
    p.write_text(body)
    return p


def test_sync_overwrites_descriptions_and_sets_meta_without_clobbering(tmp_path: Path):
    project = _copy_dbt_project(tmp_path)
    _orders_model_sql(project)
    schema = project / "models" / "schema.yml"
    schema.write_text(
        "version: 2\n"
        "models:\n"
        "  - name: orders\n"
        "    description: stale user description\n"
        "    config:\n"
        "      materialized: table\n"
        "      meta:\n"
        "        custom_key: keep me\n"
        "    columns:\n"
        "      - name: order_id\n"
        "        description: stale column description\n"
    )
    contract = _write(tmp_path, "tagged.odcs.yaml", _TAGGED_CONTRACT)
    sync(contract=str(contract), project_dir=project, skip_tests=True)

    entry = _model_entry(schema)
    assert entry["description"] == "Orders model from the contract."  # contract wins
    assert entry["config"]["materialized"] == "table"  # user config preserved
    assert entry["config"]["meta"]["custom_key"] == "keep me"  # other meta preserved
    assert entry["config"]["meta"]["data_contract"] == "tagged-contract"
    assert entry["config"]["meta"]["owner"] == "data-eng"
    cols = {c["name"]: c for c in entry["columns"]}
    assert cols["order_id"]["description"] == "The order identifier."  # contract wins


def test_resync_clears_owner_when_contract_loses_team(tmp_path: Path):
    project = _copy_dbt_project(tmp_path)
    _orders_model_sql(project)
    schema = project / "models" / "schema.yml"
    schema.write_text("version: 2\nmodels:\n  - name: orders\n    config:\n      meta:\n        custom_key: keep me\n")
    tagged = _write(tmp_path, "tagged.odcs.yaml", _TAGGED_CONTRACT)
    sync(contract=str(tagged), project_dir=project, skip_tests=True)
    assert _model_entry(schema)["config"]["meta"]["owner"] == "data-eng"

    no_team = _write(tmp_path, "no_team.odcs.yaml", _TAGGED_CONTRACT.replace("team:\n  name: data-eng\n", ""))
    sync(contract=str(no_team), project_dir=project, skip_tests=True)

    meta = _model_entry(schema)["config"]["meta"]
    assert "owner" not in meta  # stale owner cleared
    assert meta["data_contract"] == "tagged-contract"  # still authoritative
    assert meta["custom_key"] == "keep me"  # user meta preserved


def test_sync_unions_tags_preserving_user_tags(tmp_path: Path):
    project = _copy_dbt_project(tmp_path)
    _orders_model_sql(project)
    schema = project / "models" / "schema.yml"
    schema.write_text(
        "version: 2\n"
        "models:\n"
        "  - name: orders\n"
        "    config:\n"
        "      tags: [user_model_tag, pii]\n"  # `pii` overlaps with the contract
        "    columns:\n"
        "      - name: order_id\n"
        "        config:\n"
        "          tags: [user_col_tag]\n"
    )
    contract = _write(tmp_path, "tagged.odcs.yaml", _TAGGED_CONTRACT)
    sync(contract=str(contract), project_dir=project, skip_tests=True)

    entry = _model_entry(schema)
    # Union, no duplicates, user tag preserved.
    assert entry["config"]["tags"] == ["user_model_tag", "pii", "gold"]
    cols = {c["name"]: c for c in entry["columns"]}
    assert cols["order_id"]["config"]["tags"] == ["user_col_tag", "identifier"]


def test_prune_strict_mirrors_columns_and_tags(tmp_path: Path):
    project = _copy_dbt_project(tmp_path)
    _orders_model_sql(project)
    schema = project / "models" / "schema.yml"
    schema.write_text(
        "version: 2\n"
        "models:\n"
        "  - name: orders\n"
        "    config:\n"
        "      tags: [user_model_tag]\n"  # not in the contract → pruned
        "    columns:\n"
        "      - name: order_id\n"
        "      - name: undeclared_col\n"  # not in the contract → pruned
    )
    contract = _write(tmp_path, "tagged.odcs.yaml", _TAGGED_CONTRACT)
    sync(contract=str(contract), project_dir=project, skip_tests=True, prune=True)

    entry = _model_entry(schema)
    assert [c["name"] for c in entry["columns"]] == ["order_id"]  # undeclared column dropped
    assert entry["config"]["tags"] == ["pii", "gold"]  # strict mirror (contract order), user tag dropped


# ---------------------------------------------------------------------------
# Provenance-aware cleanup when the contract changes
# ---------------------------------------------------------------------------


def test_resync_drops_generated_but_untags_adopted_when_test_removed(tmp_path: Path):
    project = _copy_dbt_project(tmp_path)
    _orders_model_sql(project)
    schema = project / "models" / "schema.yml"
    schema.write_text(
        "version: 2\n"
        "models:\n"
        "  - name: orders\n"
        "    columns:\n"
        "      - name: order_id\n"
        "        data_tests:\n"
        "          - not_null\n"  # user-authored → will be adopted, then un-tagged
    )
    full = _write(tmp_path, "full.odcs.yaml", _TAGGED_CONTRACT)
    sync(contract=str(full), project_dir=project, skip_tests=True)
    cols = {c["name"]: c for c in _model_entry(schema)["columns"]}
    assert "datacontract_cli" in cols["order_id"]["data_tests"][0]["not_null"]["config"]["tags"]
    assert any(t == "unique" or "unique" in t for t in [next(iter(t)) for t in cols["order_id"]["data_tests"]])

    # New contract: order_id is no longer required/unique → only the description test remains.
    reduced = _write(
        tmp_path,
        "reduced.odcs.yaml",
        "kind: DataContract\napiVersion: v3.1.0\nid: tagged-contract\nname: Tagged\nversion: 2.0.0\n"
        "status: active\nschema:\n  - name: orders\n    properties:\n      - name: order_id\n"
        "        description: still here\n",
    )
    sync(contract=str(reduced), project_dir=project, skip_tests=True)

    tests = {next(iter(t)): t for t in _model_entry(schema)["columns"][0].get("data_tests", [])}
    # Generated `unique` is gone; adopted `not_null` survives un-tagged as the user's plain test.
    assert "unique" not in tests
    assert tests.get("not_null") == "not_null" or "datacontract_cli" not in str(tests.get("not_null"))


# ---------------------------------------------------------------------------
# Subprocess + run_results parsing
# ---------------------------------------------------------------------------


def test_run_dbt_test_selects_only_tagged_tests(tmp_path: Path):
    project = _copy_dbt_project(tmp_path)
    captured: dict[str, list[str]] = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="ok", stderr="")

    with mock.patch.object(subprocess, "run", side_effect=fake_run):
        run_dbt_test(project, target=None, profiles_dir=None)

    args = captured["args"]
    select_idx = args.index("--select")
    selectors = args[select_idx + 1 : args.index("--project-dir")]
    assert selectors == ["tag:datacontract_cli"]


def test_run_dbt_test_surfaces_failure_when_no_run_results(tmp_path: Path):
    """If dbt fails before producing run_results.json, sync must surface — not swallow — the error."""
    project = _copy_dbt_project(tmp_path)
    parse_stderr = "Compilation Error\n  some unrelated parse failure\n"

    def fake_run(args, **kwargs):
        return subprocess.CompletedProcess(args=args, returncode=2, stdout="", stderr=parse_stderr)

    with mock.patch.object(subprocess, "run", side_effect=fake_run):
        with pytest.raises(DataContractException) as exc:
            run_dbt_test(project, target=None, profiles_dir=None)

    assert "exit code 2" in exc.value.reason
    assert "some unrelated parse failure" in exc.value.reason


def test_run_dbt_test_does_not_raise_when_run_results_present(tmp_path: Path):
    """Test failures (non-zero exit but run_results.json exists) are normal, not errors."""
    project = _copy_dbt_project(tmp_path)
    target_dir = project / "target"
    target_dir.mkdir()

    def fake_run(args, **kwargs):
        # Simulate a real dbt run: it produces run_results.json before exiting non-zero
        # if some tests failed. The pre-run cleanup that run_dbt_test does should not
        # mistake this for a parse-time failure.
        (target_dir / "run_results.json").write_text('{"results": []}')
        return subprocess.CompletedProcess(args=args, returncode=1, stdout="some tests failed", stderr="")

    with mock.patch.object(subprocess, "run", side_effect=fake_run):
        result = run_dbt_test(project, target=None, profiles_dir=None)
        assert result.returncode == 1


def test_run_dbt_test_clears_stale_run_results(tmp_path: Path):
    """A pre-existing run_results.json must not leak into the next run when dbt fails."""
    project = _copy_dbt_project(tmp_path)
    target_dir = project / "target"
    target_dir.mkdir()
    stale = target_dir / "run_results.json"
    stale.write_text('{"results": [{"unique_id": "stale", "status": "pass"}]}')

    def fake_run(args, **kwargs):
        # Simulate dbt failing at parse time — does NOT regenerate run_results.json.
        return subprocess.CompletedProcess(args=args, returncode=2, stdout="", stderr="some parse error")

    with mock.patch.object(subprocess, "run", side_effect=fake_run):
        with pytest.raises(DataContractException, match="some parse error"):
            run_dbt_test(project, target=None, profiles_dir=None)
    assert not stale.exists()


def test_run_dbt_test_target_and_profiles_forwarded(tmp_path: Path):
    project = _copy_dbt_project(tmp_path)
    captured: dict[str, list[str]] = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    with mock.patch.object(subprocess, "run", side_effect=fake_run):
        # Relative path: run_dbt_test cwds into project_dir, so it must resolve to absolute first.
        run_dbt_test(
            project,
            target="dev",
            profiles_dir=Path("relative/profiles"),
        )

    args = captured["args"]
    assert "--target" in args and args[args.index("--target") + 1] == "dev"
    profiles_value = args[args.index("--profiles-dir") + 1]
    assert Path(profiles_value).is_absolute()


def test_parse_run_results_maps_status_and_failures(tmp_path: Path):
    project = _copy_dbt_project(tmp_path)
    target_dir = project / "target"
    target_dir.mkdir()

    run_results = {
        "results": [
            {
                "unique_id": "test.proj.not_null_orders_order_id.abc",
                "status": "pass",
                "failures": 0,
                "message": None,
            },
            {
                "unique_id": "test.proj.row_count_check.def",
                "status": "fail",
                "failures": 5,
                "message": "Got 5 results, configured to fail if != 0",
            },
            {
                "unique_id": "test.proj.warn_check.ghi",
                "status": "warn",
                "failures": 1,
                "message": "Got 1 result, configured to warn if != 0",
            },
            {
                "unique_id": "test.proj.error_check.jkl",
                "status": "error",
                "failures": None,
                "message": "Compilation error",
            },
            {
                "unique_id": "test.proj.skipped_check.mno",
                "status": "skipped",
                "failures": None,
                "message": None,
            },
        ]
    }
    (target_dir / "run_results.json").write_text(json.dumps(run_results))

    manifest = {
        "nodes": {
            "test.proj.not_null_orders_order_id.abc": {
                "name": "not_null_orders_order_id",
                "column_name": "order_id",
                "attached_node": "model.proj.orders",
                "description": "Order ID must not be null",
            },
            "test.proj.row_count_check.def": {
                "name": "row_count_check",
                "depends_on": {"nodes": ["model.proj.orders"]},
                "description": None,
            },
        }
    }
    (target_dir / "manifest.json").write_text(json.dumps(manifest))

    odcs = resolve_data_contract(str(CONTRACT_PATH))
    parsed = parse_run_results(project, odcs)

    assert parsed.dataContractId == "orders-sync-test"
    assert len(parsed.checks) == 5
    by_name = {c.name: c for c in parsed.checks}
    assert by_name["Order ID must not be null"].result.value == "passed"
    assert by_name["Order ID must not be null"].field == "order_id"
    assert by_name["Order ID must not be null"].model == "orders"

    fail_check = by_name["row_count_check"]
    assert fail_check.result.value == "failed"
    assert "failures=5" in fail_check.reason
    assert "configured to fail" in fail_check.reason

    statuses = {c.result.value for c in parsed.checks}
    assert statuses == {"passed", "failed", "warning", "error", "info"}


def test_parse_run_results_derives_check_type_from_dc_tag(tmp_path: Path):
    """`Check.type` is read from the `dc:<type>` tag attached to each test node.

    Falls back to `dbt_test` when no `dc:*` tag is present.
    """
    project = _copy_dbt_project(tmp_path)
    target_dir = project / "target"
    target_dir.mkdir()

    run_results = {
        "results": [
            {"unique_id": "test.proj.a", "status": "pass", "failures": 0, "message": None},
            {"unique_id": "test.proj.b", "status": "pass", "failures": 0, "message": None},
            {"unique_id": "test.proj.c", "status": "pass", "failures": 0, "message": None},
        ]
    }
    (target_dir / "run_results.json").write_text(json.dumps(run_results))

    manifest = {
        "nodes": {
            "test.proj.a": {"name": "a", "tags": ["datacontract_cli", "dc:field_required"]},
            "test.proj.b": {"name": "b", "tags": ["datacontract_cli", "dc:row_count"]},
            # Legacy artifact without a dc:* tag — must fall back to "dbt_test".
            "test.proj.c": {"name": "c", "tags": ["datacontract_cli"]},
        }
    }
    (target_dir / "manifest.json").write_text(json.dumps(manifest))

    odcs = resolve_data_contract(str(CONTRACT_PATH))
    parsed = parse_run_results(project, odcs)

    by_name = {c.name: c for c in parsed.checks}
    assert by_name["a"].type == "field_required"
    assert by_name["b"].type == "row_count"
    assert by_name["c"].type == "dbt_test"


def test_parse_run_results_recovers_model_and_field_from_config_meta(tmp_path: Path):
    """Singular SQL tests have no `column_name`/`attached_node` in the manifest.

    `dbt sync` round-trips both names through `config(meta={...})`, which dbt
    surfaces on `node.config.meta`. The parser must fall back to it.
    """
    project = _copy_dbt_project(tmp_path)
    target_dir = project / "target"
    target_dir.mkdir()
    (target_dir / "run_results.json").write_text(
        json.dumps(
            {
                "results": [
                    {"unique_id": "test.proj.field_bound", "status": "fail", "failures": 2, "message": "boom"},
                    {"unique_id": "test.proj.no_ref_quality", "status": "pass", "failures": 0, "message": None},
                ]
            }
        )
    )
    (target_dir / "manifest.json").write_text(
        json.dumps(
            {
                "nodes": {
                    # Singular SQL: no `column_name`, no `attached_node`. Meta supplies both.
                    "test.proj.field_bound": {
                        "name": "orders_sync_test__orders__order_id__length",
                        "config": {"meta": {"dc_model": "orders", "dc_field": "order_id"}},
                    },
                    # User `quality.query` without `ref()` → `depends_on.nodes` is empty;
                    # meta is the only signal we have for the model.
                    "test.proj.no_ref_quality": {
                        "name": "no_ref_quality",
                        "config": {"meta": {"dc_model": "orders"}},
                    },
                }
            }
        )
    )

    odcs = resolve_data_contract(str(CONTRACT_PATH))
    parsed = parse_run_results(project, odcs)

    by_name = {c.name: c for c in parsed.checks}
    field_bound = by_name["orders_sync_test__orders__order_id__length"]
    assert field_bound.model == "orders"
    assert field_bound.field == "order_id"

    no_ref = by_name["no_ref_quality"]
    assert no_ref.model == "orders"
    assert no_ref.field is None


def test_parse_run_results_recovers_description_from_config_meta(tmp_path: Path):
    """dbt 1.11's manifest leaves `node.description == ''` for singular SQL tests even
    when a description is set in the model YAML's top-level `data_tests:` block.
    `dbt sync` round-trips the human-readable description through `config(meta={...})`
    so `Check.name` reads "Check that field email matches…" instead of the SQL filename.
    """
    project = _copy_dbt_project(tmp_path)
    target_dir = project / "target"
    target_dir.mkdir()
    (target_dir / "run_results.json").write_text(
        json.dumps(
            {
                "results": [
                    {"unique_id": "test.proj.email_pattern", "status": "warn", "failures": 1, "message": None},
                ]
            }
        )
    )
    (target_dir / "manifest.json").write_text(
        json.dumps(
            {
                "nodes": {
                    "test.proj.email_pattern": {
                        "name": "orders_sync_test__customers__email__pattern",
                        # Empty string (what dbt 1.11 actually writes), not None.
                        "description": "",
                        "config": {
                            "meta": {
                                "dc_model": "customers",
                                "dc_field": "email",
                                "dc_description": "Check that field email matches regex pattern ^[^@]+@[^@]+$",
                            }
                        },
                    },
                }
            }
        )
    )

    odcs = resolve_data_contract(str(CONTRACT_PATH))
    parsed = parse_run_results(project, odcs)
    assert len(parsed.checks) == 1
    assert parsed.checks[0].name == "Check that field email matches regex pattern ^[^@]+@[^@]+$"


def test_parse_run_results_honors_custom_target_path(tmp_path: Path):
    """When `target-path` is overridden, dbt writes artifacts to that dir — not `target/`."""
    project = _custom_paths_project(tmp_path, model_paths=["models"], test_paths=["tests"])
    (project / "dbt_project.yml").write_text((project / "dbt_project.yml").read_text() + "target-path: 'build'\n")
    build_dir = project / "build"
    build_dir.mkdir()
    (build_dir / "run_results.json").write_text(
        json.dumps({"results": [{"unique_id": "test.x.y", "status": "pass", "failures": 0, "message": None}]})
    )

    odcs = resolve_data_contract(str(CONTRACT_PATH))
    parsed = parse_run_results(project, odcs)
    assert len(parsed.checks) == 1
    assert parsed.checks[0].result.value == "passed"


def test_parse_run_results_missing_file(tmp_path: Path):
    project = _copy_dbt_project(tmp_path)
    odcs = resolve_data_contract(str(CONTRACT_PATH))
    parsed = parse_run_results(project, odcs)
    assert parsed.checks == []
    assert any("not found" in log.message for log in parsed.logs)


# ---------------------------------------------------------------------------
# CLI surface
# ---------------------------------------------------------------------------


def test_cli_help_renders():
    result = CliRunner().invoke(app, ["dbt", "sync", "--help"], terminal_width=200, color=False)
    assert result.exit_code == 0
    # Strip ANSI + collapse whitespace. CI on Linux ignores `color=False` and emits escape
    # codes inside flag names (e.g. `--\x1b[…m\x1b[…m-skip-tests`), so a literal substring
    # match fails without this normalization.
    plain = re.sub(r"\s+", "", re.sub(r"\x1b\[[0-9;]*[mGKHF]", "", result.stdout))
    assert "Generatedbttestsandmodelmetadata" in plain
    assert "--skip-tests" in plain
    assert "--schema-name" in plain
    assert "--prune" in plain


def test_cli_skip_tests_invocation(tmp_path: Path):
    project = _copy_dbt_project(tmp_path)
    _orders_model_sql(project)
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "dbt",
            "sync",
            str(CONTRACT_PATH),
            "--project-dir",
            str(project),
            "--skip-tests",
        ],
    )
    if result.exit_code != 0:
        sys.stderr.write(result.output)
        if result.exception:
            raise result.exception
    assert result.exit_code == 0
    assert (project / "models" / "orders.yml").exists()  # owned sidecar (no pre-existing entry)


# ---------------------------------------------------------------------------
# Integration: real `dbt test` (only if dbt + dbt-duckdb are on PATH)
# ---------------------------------------------------------------------------


def _dbt_available() -> bool:
    if not shutil.which("dbt"):
        return False
    try:
        out = subprocess.run(["dbt", "--version"], capture_output=True, text=True, timeout=5)
    except (OSError, subprocess.TimeoutExpired):
        return False
    return "duckdb" in (out.stdout or "").lower() or "duckdb" in (out.stderr or "").lower()


@pytest.mark.skipif(not _dbt_available(), reason="dbt + dbt-duckdb not on PATH")
def test_integration_end_to_end(tmp_path: Path):
    """End-to-end: a real dbt-duckdb run on the fixture project."""
    project = _copy_dbt_project(tmp_path)

    # Seed a tiny DuckDB-backed model so dbt has something to test against.
    (project / "models" / "orders.sql").write_text(
        "select 'B0000001' as order_id, 'pending' as order_status, 100 as order_total"
    )
    profiles_dir = tmp_path / "profiles"
    profiles_dir.mkdir()
    (profiles_dir / "profiles.yml").write_text(
        "datacontract_sync_fixture:\n"
        "  target: dev\n"
        "  outputs:\n"
        "    dev:\n"
        "      type: duckdb\n"
        f"      path: {tmp_path / 'warehouse.duckdb'}\n"
    )

    result = sync(
        contract=str(CONTRACT_PATH),
        project_dir=project,
        profiles_dir=profiles_dir,
        skip_tests=False,
    )

    assert result.run is not None


# ---------------------------------------------------------------------------
# --publish flag
# ---------------------------------------------------------------------------


def _stub_dbt_test(monkeypatch, project: Path) -> None:
    """Replace `subprocess.run` so `dbt test` succeeds and leaves a minimal run_results.json."""
    _orders_model_sql(project)  # a resolvable model so sync runs `dbt test` instead of skipping
    target_dir = project / "target"
    target_dir.mkdir(exist_ok=True)

    def fake_run(args, **kwargs):
        (target_dir / "run_results.json").write_text(
            json.dumps(
                {"results": [{"unique_id": "test.proj.x.abc", "status": "pass", "failures": 0, "message": None}]}
            )
        )
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(shutil, "which", lambda _: "/fake/dbt")
    monkeypatch.setattr(subprocess, "run", fake_run)


def test_run_tests_forwards_dbt_output_to_run_logs(monkeypatch, tmp_path: Path):
    """`run_tests` must surface `dbt test` stdout/stderr through `run.logs` so the
    published Run carries the same context an operator would see locally — minus
    ANSI codes and empty lines."""
    project = _copy_dbt_project(tmp_path)
    _orders_model_sql(project)
    target_dir = project / "target"
    target_dir.mkdir()

    dbt_stdout = "\x1b[0m13:59:19  Running with dbt=1.11.7\n\x1b[0m13:59:19  \n13:59:20  Done. PASS=1\n"
    dbt_stderr = "deprecation warning: foo\n"

    def fake_run(args, **kwargs):
        (target_dir / "run_results.json").write_text(
            json.dumps(
                {"results": [{"unique_id": "test.proj.x.abc", "status": "pass", "failures": 0, "message": None}]}
            )
        )
        return subprocess.CompletedProcess(args=args, returncode=0, stdout=dbt_stdout, stderr=dbt_stderr)

    monkeypatch.setattr(shutil, "which", lambda _: "/fake/dbt")
    monkeypatch.setattr(subprocess, "run", fake_run)

    result = sync(contract=str(CONTRACT_PATH), project_dir=project)
    messages = [log.message for log in result.run.logs]
    assert "13:59:19  Running with dbt=1.11.7" in messages
    assert "13:59:20  Done. PASS=1" in messages
    assert "deprecation warning: foo" in messages
    # ANSI escape codes are stripped and empty lines dropped.
    assert not any("\x1b[" in m for m in messages)
    assert "" not in messages


def test_publish_not_called_when_flag_absent(monkeypatch, tmp_path: Path):
    project = _copy_dbt_project(tmp_path)
    _stub_dbt_test(monkeypatch, project)

    publish_mock = mock.MagicMock()
    monkeypatch.setattr("datacontract.command_dbt.publish_test_results_to_entropy_data", publish_mock)

    runner = CliRunner()
    result = runner.invoke(app, ["dbt", "sync", str(CONTRACT_PATH), "--project-dir", str(project)])
    assert result.exit_code == 0, result.output
    publish_mock.assert_not_called()


def test_publish_failure_exits_non_zero(monkeypatch, tmp_path: Path):
    """Publish failure → exit 1 so CI scripts catch it. The error message itself
    surfaces via stdlib logging (same path as every other `run.log_*` call); the
    CLI doesn't double-print it on stdout."""
    project = _copy_dbt_project(tmp_path)
    _stub_dbt_test(monkeypatch, project)

    def failing_publish(run, publish_url, ssl_verification):
        run.log_error("Failed publishing test results. Error: boom")
        return False

    monkeypatch.setattr("datacontract.command_dbt.publish_test_results_to_entropy_data", failing_publish)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "dbt",
            "sync",
            str(CONTRACT_PATH),
            "--project-dir",
            str(project),
            "--server",
            "prod",
            "--publish",
            "https://example.com/results",
        ],
    )
    assert result.exit_code == 1, result.output


def test_cli_publish_flag_forwards_url_and_ssl(monkeypatch, tmp_path: Path):
    project = _copy_dbt_project(tmp_path)
    _stub_dbt_test(monkeypatch, project)

    captured: dict = {}

    def fake_publish(run, publish_url, ssl_verification):
        captured["url"] = publish_url
        captured["ssl"] = ssl_verification
        run.log_info("Published test results successfully")
        return True

    monkeypatch.setattr("datacontract.command_dbt.publish_test_results_to_entropy_data", fake_publish)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "dbt",
            "sync",
            str(CONTRACT_PATH),
            "--project-dir",
            str(project),
            "--server",
            "prod",
            "--publish",
            "https://example.com/results",
            "--no-ssl-verification",
        ],
    )
    if result.exit_code != 0:
        sys.stderr.write(result.output)
        if result.exception:
            raise result.exception
    assert result.exit_code == 0
    assert captured["url"] == "https://example.com/results"
    assert captured["ssl"] is False


def test_cli_publish_with_skip_tests_rejected(tmp_path: Path):
    project = _copy_dbt_project(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "dbt",
            "sync",
            str(CONTRACT_PATH),
            "--project-dir",
            str(project),
            "--skip-tests",
            "--publish",
            "https://example.com",
        ],
    )
    assert result.exit_code == 1
    assert "--publish cannot be combined with --skip-tests" in result.stdout


def test_cli_publish_rejects_non_http_url(tmp_path: Path):
    project = _copy_dbt_project(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "dbt",
            "sync",
            str(CONTRACT_PATH),
            "--project-dir",
            str(project),
            "--publish",
            "ftp://foo",
        ],
    )
    assert result.exit_code == 1
    assert "must start with http:// or https://" in result.stdout


def test_cli_publish_skipped_when_no_server_resolvable(monkeypatch, tmp_path: Path):
    """No --server, no --target, and no `servers:` block → warn and skip publish."""
    project = _copy_dbt_project(tmp_path)
    _stub_dbt_test(monkeypatch, project)

    publish_mock = mock.MagicMock(return_value=True)
    monkeypatch.setattr("datacontract.command_dbt.publish_test_results_to_entropy_data", publish_mock)

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "dbt",
            "sync",
            str(CONTRACT_PATH),
            "--project-dir",
            str(project),
            "--publish",
            "https://example.com",
        ],
    )
    assert result.exit_code == 0, result.output
    assert "Skipping publish" in result.stdout
    publish_mock.assert_not_called()


def test_cli_server_flag_overrides_target(monkeypatch, tmp_path: Path):
    project = _copy_dbt_project(tmp_path)
    _stub_dbt_test(monkeypatch, project)

    captured: dict = {}

    def fake_publish(run, publish_url, ssl_verification):
        captured["server"] = run.server
        return True

    monkeypatch.setattr("datacontract.command_dbt.publish_test_results_to_entropy_data", fake_publish)

    # Contract declares a single server. Make it match what we'll pass via --server.
    contract = tmp_path / "with-server.odcs.yaml"
    contract.write_text(
        CONTRACT_PATH.read_text()
        + "\nservers:\n  - server: production\n    type: duckdb\n    database: warehouse\n    path: ./w.duckdb\n"
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "dbt",
            "sync",
            str(contract),
            "--project-dir",
            str(project),
            "--target",
            "ci",
            "--server",
            "production",
            "--publish",
            "https://example.com",
        ],
    )
    assert result.exit_code == 0, result.output
    assert captured["server"] == "production"


def test_cli_server_defaults_to_single_contract_server(monkeypatch, tmp_path: Path):
    """Single-server contracts are unambiguous; --target should be ignored for run.server."""
    project = _copy_dbt_project(tmp_path)
    _stub_dbt_test(monkeypatch, project)

    captured: dict = {}

    def fake_publish(run, publish_url, ssl_verification):
        captured["server"] = run.server
        return True

    monkeypatch.setattr("datacontract.command_dbt.publish_test_results_to_entropy_data", fake_publish)

    contract = tmp_path / "with-server.odcs.yaml"
    contract.write_text(
        CONTRACT_PATH.read_text()
        + "\nservers:\n  - server: production\n    type: duckdb\n    database: warehouse\n    path: ./w.duckdb\n"
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "dbt",
            "sync",
            str(contract),
            "--project-dir",
            str(project),
            "--target",
            "ci",
            "--publish",
            "https://example.com",
        ],
    )
    assert result.exit_code == 0, result.output
    assert captured["server"] == "production"


def test_cli_server_rejects_unknown_name(tmp_path: Path):
    project = _copy_dbt_project(tmp_path)
    contract = tmp_path / "with-server.odcs.yaml"
    contract.write_text(
        CONTRACT_PATH.read_text()
        + "\nservers:\n  - server: production\n    type: duckdb\n    database: warehouse\n    path: ./w.duckdb\n"
    )

    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "dbt",
            "sync",
            str(contract),
            "--project-dir",
            str(project),
            "--server",
            "typo",
            "--skip-tests",
        ],
    )
    assert result.exit_code == 1
    assert "not declared in the contract" in result.stdout
    assert "production" in result.stdout
