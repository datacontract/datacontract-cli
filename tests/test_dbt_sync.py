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
    _get_test_metadata,
    _resolved_generated_dirs,
    _rewrite_relationships_to_ref,
    _row_count_singular_test,
    _singular_tests_for_qualities,
    _sql_literal,
    check_dbt_on_path,
    find_contract,
    generate_dbt_tests,
    generate_dbt_tests_for_schema,
    parse_filename_version,
    parse_run_results_file,
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
        run = run_tests(
            gen.odcs,
            gen.project_dir,
            target=target,
            profiles_dir=profiles_dir,
            generation_run=gen.generation_run,
        )
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


def _broken_yaml(project: Path, name: str = "schema.yml") -> Path:
    path = project / "models" / name
    path.write_text("models: [\n  - name: orders\n")  # unclosed flow sequence → parse error
    return path


def test_merge_into_existing_entry_replaces_old_collision_error(tmp_path: Path):
    """A model already defined in the user's YAML is merged into — not a hard error (old behavior)."""
    project = _copy_dbt_project(tmp_path)
    _orders_model_sql(project)
    schema = _user_orders_schema(project)

    result = sync(contract=str(CONTRACT_PATH), project_dir=project, skip_tests=True)
    assert result.run is not None  # did not raise

    entry = _model_entry(schema)
    cols = {c["name"]: c for c in entry["columns"]}
    # Pre-existing user test is adopted: meta block stamped, check recorded, generated=False.
    not_null = cols["order_id"]["data_tests"][0]["not_null"]
    assert "tags" not in not_null["config"]  # no tag emitted — provenance lives in meta
    assert not_null["config"]["meta"]["datacontract_cli"]["check"] == "orders__order_id__field_required"
    assert not_null["config"]["meta"]["datacontract_cli"]["generated"] is False
    assert not_null["config"]["meta"]["datacontract_cli"]["include_in_tests"] is True  # adopted tests still run
    # A test the CLI created from nothing has generated=True.
    unique = cols["order_id"]["data_tests"][1]["unique"]
    assert unique["config"]["meta"]["datacontract_cli"]["check"] == "orders__order_id__field_unique"
    assert unique["config"]["meta"]["datacontract_cli"]["generated"] is True
    assert unique["config"]["meta"]["datacontract_cli"]["include_in_tests"] is True
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


def test_resync_preserves_user_opt_out_via_include_in_tests(tmp_path: Path):
    """A user who flips `include_in_tests: false` to opt a test out keeps it across re-syncs."""
    project = _copy_dbt_project(tmp_path)
    _orders_model_sql(project)
    schema = _user_orders_schema(project)
    sync(contract=str(CONTRACT_PATH), project_dir=project, skip_tests=True)

    # User opts the generated `unique` test out of the dbt run.
    entry = _model_entry(schema)
    unique = {c["name"]: c for c in entry["columns"]}["order_id"]["data_tests"][1]["unique"]
    assert unique["config"]["meta"]["datacontract_cli"]["include_in_tests"] is True
    unique["config"]["meta"]["datacontract_cli"]["include_in_tests"] = False
    schema.write_text(yaml.safe_dump({"version": 2, "models": [entry]}))

    sync(contract=str(CONTRACT_PATH), project_dir=project, skip_tests=True)

    unique = {c["name"]: c for c in _model_entry(schema)["columns"]}["order_id"]["data_tests"][1]["unique"]
    assert unique["config"]["meta"]["datacontract_cli"]["include_in_tests"] is False


def test_merge_columns_the_cli_creates_are_marked(tmp_path: Path):
    """Columns the CLI adds to host tests carry meta.datacontract_cli so cleanup can drop them."""
    project = _copy_dbt_project(tmp_path)
    _orders_model_sql(project)
    schema = _user_orders_schema(project)
    sync(contract=str(CONTRACT_PATH), project_dir=project, skip_tests=True)

    cols = {c["name"]: c for c in _model_entry(schema)["columns"]}
    assert cols["order_status"]["meta"]["datacontract_cli"]["generated"] is True
    assert "meta" not in cols["extra_user_col"]  # user column untouched
    assert "meta" not in cols["order_id"]  # pre-existing user column not marked


def test_sync_creates_model_yaml_when_no_yaml_entry(tmp_path: Path):
    project = _copy_dbt_project(tmp_path)
    _orders_model_sql(project)  # model SQL exists, but no YAML entry anywhere

    sync(contract=str(CONTRACT_PATH), project_dir=project, skip_tests=True)

    sidecar = project / "models" / "orders.yml"
    assert sidecar.exists()
    text = sidecar.read_text()
    # No "do not edit" notice — a generated file is a plain schema file the user is free to edit.
    assert "AUTO-GENERATED" not in text
    entry = _model_entry(sidecar)
    assert entry["config"]["meta"]["datacontract_cli"]["contract_id"] == "orders-sync-test"
    # Version provenance lives per-test; the entry-level roll-up was write-only and is no longer emitted.
    assert "contract_versions" not in entry["config"]["meta"]["datacontract_cli"]
    order_id = {c["name"]: c for c in entry["columns"]}["order_id"]
    not_null_meta = order_id["data_tests"][0]["not_null"]["config"]["meta"]["datacontract_cli"]
    assert not_null_meta["contract_versions"] == ["1.0.0"]
    assert not_null_meta["generated"] is True
    # Columns we create carry the managed marker so a later sync can retire them cleanly.
    assert order_id["meta"]["datacontract_cli"]["generated"] is True


def test_sync_skips_model_with_no_sql_or_entry(tmp_path: Path):
    """A contract model with neither a `.sql` nor a YAML entry can't be tested — warn and skip."""
    project = _copy_dbt_project(tmp_path)  # empty models dir, no orders.sql
    result = sync(contract=str(CONTRACT_PATH), project_dir=project, skip_tests=True)

    assert result.written_yaml == []
    assert not (project / "models" / "orders.yml").exists()
    assert any("nothing to test" in log.message for log in result.run.logs)


def test_sync_hard_errors_on_unparseable_yaml_when_sidecar_needed(tmp_path: Path):
    """A broken model-path YAML could be the model's own schema file; writing a sidecar would risk a
    dbt duplicate-patch error, so refuse before writing anything."""
    project = _copy_dbt_project(tmp_path)
    _orders_model_sql(project)  # matches via .sql → sidecar in play
    _broken_yaml(project)

    with pytest.raises(DataContractException, match="Cannot parse YAML file"):
        sync(contract=str(CONTRACT_PATH), project_dir=project, skip_tests=True)

    assert not (project / "models" / "orders.yml").exists()  # nothing written


def test_sync_warns_and_continues_when_unparseable_yaml_is_irrelevant(tmp_path: Path):
    """When the model resolves via an existing entry (no sidecar), an unparseable unrelated YAML can't
    be one of ours — warn and continue instead of aborting."""
    project = _copy_dbt_project(tmp_path)
    _user_orders_schema(project)  # valid orders entry → resolves via entry, no sidecar
    _broken_yaml(project, name="broken_sources.yml")

    result = sync(contract=str(CONTRACT_PATH), project_dir=project, skip_tests=True)

    assert result.written_yaml  # sync proceeded
    assert any("Ignoring unparseable YAML file" in log.message for log in result.run.logs)


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

    Otherwise dbt won't pick the files up and the `config.meta.datacontract_cli` selector matches nothing.
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
    assert _attach_test_config("not_null", "warn") == {"not_null": {"config": {"severity": "warn"}}}


def test_attach_config_dict_test():
    result = _attach_test_config(
        {"accepted_values": {"values": [1, 2]}}, "error", check_type="field_enum", model="orders", field="status"
    )
    assert result == {
        "accepted_values": {
            "values": [1, 2],
            "config": {
                "severity": "error",
                "meta": {"datacontract_cli": {"check": "orders__status__field_enum"}},
            },
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


def test_generate_outputs_wraps_tests_with_meta_and_emits_singulars():
    odcs = resolve_data_contract(str(CONTRACT_PATH))
    schema_obj = odcs.schema_[0]
    run = Run.create_run()

    model_dict, singulars = generate_dbt_tests_for_schema(odcs, schema_obj, "orders", run)

    assert model_dict["name"] == "orders"
    assert model_dict["description"] == "Orders table"

    # Sync-specific: every YAML test carries the datacontract_cli meta block (no tag) with a
    # fully-qualified check key.
    cols = {c["name"]: c for c in model_dict["columns"]}
    expected_check = {
        "not_null": "orders__order_id__field_required",
        "unique": "orders__order_id__field_unique",
        "accepted_values": "orders__order_id__field_enum",
        "relationships": "orders__order_id__field_relationships",
    }
    for t in cols["order_id"]["data_tests"]:
        assert isinstance(t, dict)
        ((test_name, args),) = t.items()
        assert "tags" not in args["config"]
        assert args["config"]["meta"]["datacontract_cli"]["check"] == expected_check[test_name]

    # Single-PK in this fixture → no model-level data_tests.
    assert "data_tests" not in model_dict

    # Singular SQL: three field-level bounds (length + regex on order_id, range on order_total)
    # plus two quality.query rules (95% column rule, model-level row count).
    assert len(singulars) == 5
    assert all(s.filename.startswith("orders_sync_test__1_0_0__orders__") for s in singulars)
    assert all(s.filename.endswith(".sql") for s in singulars)
    assert any(s.description and "95%" in s.description for s in singulars)
    by_name = {s.filename: s for s in singulars}
    assert "length between 8 and 10" in by_name["orders_sync_test__1_0_0__orders__order_id__length.sql"].description
    assert "matches regex pattern" in by_name["orders_sync_test__1_0_0__orders__order_id__pattern.sql"].description
    assert "minimum of 0" in by_name["orders_sync_test__1_0_0__orders__order_total__range.sql"].description


def test_generate_outputs_composite_pk_emits_dep_free_singular_unique():
    odcs = resolve_data_contract(str(CONTRACT_PATH))
    schema_obj = odcs.schema_[0]
    # Promote order_status to composite PK alongside order_id.
    for prop in schema_obj.properties:
        if prop.name == "order_status":
            prop.primaryKey = True
            prop.primaryKeyPosition = 2

    model_dict, singulars = generate_dbt_tests_for_schema(odcs, schema_obj, "orders", Run.create_run())

    # Composite PK is emitted as dependency-free singular SQL, not a dbt_utils YAML test.
    assert "data_tests" not in model_dict
    by_name = {s.filename: s for s in singulars}
    pk = by_name["orders_sync_test__1_0_0__orders__unique_combination.sql"]
    assert "dbt_utils" not in pk.sql
    assert 'GROUP BY "order_id", "order_status"' in pk.sql
    assert "HAVING COUNT(*) > 1" in pk.sql
    assert pk.description == "Check that model orders has a unique combination of columns order_id, order_status"


def test_field_singular_tests_emit_portable_violation_predicates():
    """Length/range/regex bounds become singular SQL — no `dbt_expectations` dependency."""
    odcs = resolve_data_contract(str(CONTRACT_PATH))
    schema_obj = odcs.schema_[0]
    _, singulars = generate_dbt_tests_for_schema(odcs, schema_obj, "orders", Run.create_run())

    by_name = {s.filename: s for s in singulars}

    length = by_name["orders_sync_test__1_0_0__orders__order_id__length.sql"]
    assert 'LENGTH("order_id") < 8' in length.sql
    assert 'LENGTH("order_id") > 10' in length.sql
    assert '"order_id" IS NOT NULL' in length.sql
    assert "dbt_expectations" not in length.sql

    pattern = by_name["orders_sync_test__1_0_0__orders__order_id__pattern.sql"]
    # Adapter-portable regex via Jinja dispatch on `target.type`.
    assert "{% if target.type == 'bigquery' %}" in pattern.sql
    assert "REGEXP_CONTAINS" in pattern.sql
    assert "REGEXP_LIKE" in pattern.sql
    assert "TO_CHAR" in pattern.sql
    assert "RLIKE" in pattern.sql
    assert "regexp_like" in pattern.sql
    assert "REGEXP" in pattern.sql
    assert "match(" in pattern.sql
    assert "REGEXP_SIMILAR" in pattern.sql
    assert "!~" in pattern.sql
    assert "^B[0-9]+$" in pattern.sql

    rng = by_name["orders_sync_test__1_0_0__orders__order_total__range.sql"]
    assert '"order_total" < 0' in rng.sql
    assert '"order_total" > 1000000' in rng.sql


def test_row_count_singular_test_wraps_count_with_bound_predicate():
    """Declarative `rowCount` bound → `SELECT COUNT(*)` wrapped with a bound-violation predicate."""
    quality = DataQuality(metric="rowCount", mustBeGreaterThan=1000)
    test = _row_count_singular_test(quality, contract_id="orders_sync_test", contract_version="1.0.0", model="orders")
    assert test is not None
    assert "SELECT COUNT(*) FROM {{ ref('orders') }}" in test.sql
    assert "metric_value <= 1000" in test.sql


def test_generate_outputs_singular_sql_carries_severity_and_meta():
    odcs = resolve_data_contract(str(CONTRACT_PATH))
    schema_obj = odcs.schema_[0]
    _, singulars = generate_dbt_tests_for_schema(odcs, schema_obj, "orders", Run.create_run())

    row_count = next(s for s in singulars if "row_count" in s.filename)
    # severity=error normalized from `severity: error` in the fixture
    assert "severity='error'" in row_count.sql
    assert "tags=[" not in row_count.sql  # no tag emitted — provenance lives in meta
    assert '"check": "orders__custom_sql"' in row_count.sql


def test_build_singular_sql_wraps_query_with_violation_predicate():
    sql = _build_singular_sql(
        "SELECT COUNT(*) FROM orders",
        "metric_value IS NULL OR metric_value <= 1000",
        "error",
        "my-contract",
        "1.0.0",
        "orders",
        check_type="row_count",
    )
    assert "AUTO-GENERATED" in sql
    assert "my-contract" in sql
    assert "severity='error'" in sql
    assert "tags=[" not in sql  # no tag emitted — provenance lives in meta
    assert '"include_in_tests": true' in sql  # what the `dbt test` selector keys off
    assert '"check": "orders__row_count"' in sql  # fully-qualified key
    assert '"model": "orders"' in sql  # Model is round-tripped through `meta`
    assert '"contract_versions": ["1.0.0"]' in sql  # what the version-scoped `dbt test` selector keys off
    assert '"field"' not in sql  # model-level test, no field
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
    out = _singular_tests_for_qualities(qualities, "c", "1.0.0", "orders", run)
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
    _orders_model_sql(project)  # no YAML entry → sync generates the model YAML
    result = sync(
        contract=str(CONTRACT_PATH),
        project_dir=project,
        skip_tests=True,
    )

    assert len(result.written_yaml) == 1
    yml = result.written_yaml[0]
    assert yml.exists()
    content = yml.read_text()
    assert "AUTO-GENERATED" not in content
    parsed = yaml.safe_load(content)
    assert parsed["models"][0]["name"] == "orders"

    # All singular SQL files materialize on disk: three field-level bounds
    # (length, regex, range) plus the two `quality.query` rules from the fixture.
    assert len(result.written_sql) == 5
    for sql_path in result.written_sql:
        assert sql_path.exists()
        assert "AUTO-GENERATED" in sql_path.read_text()


def test_sync_with_no_resolvable_schemas_still_wipes_stale_artifacts(tmp_path: Path):
    """A contract that resolves to zero models must still wipe its own prior generated artifacts —
    otherwise old generated files from an earlier run keep getting executed. (Scoped to the
    contract's id-slug so a multi-contract project doesn't drop other contracts' tests.)"""
    project = _copy_dbt_project(tmp_path)
    stale_legacy = project / GENERATED_MODELS_DIR / "stale.yml"
    stale_sql = project / GENERATED_TESTS_DIR / "empty_contract__stale.sql"
    stale_legacy.parent.mkdir(parents=True, exist_ok=True)
    stale_sql.parent.mkdir(parents=True, exist_ok=True)
    stale_legacy.write_text("# stale")
    stale_sql.write_text("-- stale")

    empty_contract = tmp_path / "empty.odcs.yaml"
    empty_contract.write_text(
        "kind: DataContract\napiVersion: v3.1.0\nid: empty-contract\nname: Empty\nversion: 1.0.0\nstatus: active\n"
    )

    sync(contract=str(empty_contract), project_dir=project, skip_tests=True)

    assert not stale_sql.exists()  # this contract's stale singular SQL is wiped + regenerated
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
    assert entry["config"]["meta"]["datacontract_cli"]["contract_id"] == "tagged-contract"
    assert "contract_versions" not in entry["config"]["meta"]["datacontract_cli"]  # write-only key gone
    assert entry["config"]["meta"]["datacontract_cli"]["owner"] == "data-eng"
    cols = {c["name"]: c for c in entry["columns"]}
    assert cols["order_id"]["description"] == "The order identifier."  # contract wins


def test_resync_clears_owner_when_contract_loses_team(tmp_path: Path):
    project = _copy_dbt_project(tmp_path)
    _orders_model_sql(project)
    schema = project / "models" / "schema.yml"
    schema.write_text("version: 2\nmodels:\n  - name: orders\n    config:\n      meta:\n        custom_key: keep me\n")
    tagged = _write(tmp_path, "tagged.odcs.yaml", _TAGGED_CONTRACT)
    sync(contract=str(tagged), project_dir=project, skip_tests=True)
    assert _model_entry(schema)["config"]["meta"]["datacontract_cli"]["owner"] == "data-eng"

    no_team = _write(tmp_path, "no_team.odcs.yaml", _TAGGED_CONTRACT.replace("team:\n  name: data-eng\n", ""))
    sync(contract=str(no_team), project_dir=project, skip_tests=True)

    meta = _model_entry(schema)["config"]["meta"]
    assert "owner" not in meta["datacontract_cli"]  # stale owner cleared
    assert meta["datacontract_cli"]["contract_id"] == "tagged-contract"  # still authoritative
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


def test_resync_drops_generated_but_unmanages_adopted_when_test_removed(tmp_path: Path):
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
        "          - not_null\n"  # user-authored → will be adopted, then released
    )
    full = _write(tmp_path, "full.odcs.yaml", _TAGGED_CONTRACT)
    sync(contract=str(full), project_dir=project, skip_tests=True)
    cols = {c["name"]: c for c in _model_entry(schema)["columns"]}
    adopted = cols["order_id"]["data_tests"][0]["not_null"]
    assert "tags" not in adopted["config"]  # no tag emitted — provenance lives in meta
    assert adopted["config"]["meta"]["datacontract_cli"]["generated"] is False
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

    remaining = _model_entry(schema)["columns"][0].get("data_tests", [])
    names = [t if isinstance(t, str) else next(iter(t)) for t in remaining]
    # Generated `unique` is gone; adopted `not_null` survives, released back to the user's plain
    # bare-string test now that our meta block has been stripped.
    assert "unique" not in names
    assert "not_null" in remaining


def test_resync_preserves_user_edits_to_generated_yaml(tmp_path: Path):
    """A file sync generated is a plain schema file: a later sync merges into it additively, so a
    column the user hand-added (not declared by the contract) survives — same as any user file."""
    project = _copy_dbt_project(tmp_path)
    _orders_model_sql(project)  # no YAML entry → sync generates models/orders.yml
    sync(contract=str(CONTRACT_PATH), project_dir=project, skip_tests=True)
    generated = project / "models" / "orders.yml"
    assert generated.exists()

    doc = yaml.safe_load(generated.read_text())
    doc["models"][0].setdefault("columns", []).append({"name": "user_notes"})
    generated.write_text(yaml.safe_dump(doc, sort_keys=False))

    sync(contract=str(CONTRACT_PATH), project_dir=project, skip_tests=True)

    names = [c["name"] for c in _model_entry(generated)["columns"]]
    assert "user_notes" in names  # user edit to a generated file is not clobbered


def test_resync_deletes_generated_yaml_when_it_becomes_empty(tmp_path: Path):
    """When the contract stops declaring a model, its generated entry is stripped bare; a file left
    with nothing but that entry is deleted rather than lingering as an empty stub."""
    project = _copy_dbt_project(tmp_path)
    _orders_model_sql(project)
    sync(contract=str(CONTRACT_PATH), project_dir=project, skip_tests=True)
    generated = project / "models" / "orders.yml"
    assert generated.exists()

    # Same contract id, but the `orders` schema is gone → nothing left in the generated file.
    empty = _write(
        tmp_path,
        "empty.odcs.yaml",
        "kind: DataContract\napiVersion: v3.1.0\nid: orders-sync-test\nname: Orders\nversion: 2.0.0\nstatus: active\n",
    )
    sync(contract=str(empty), project_dir=project, skip_tests=True)

    assert not generated.exists()


# ---------------------------------------------------------------------------
# Subprocess + run_results parsing
# ---------------------------------------------------------------------------


def test_run_dbt_test_selects_only_managed_tests(tmp_path: Path):
    """Tests are selected by `config.meta.datacontract_cli.include_in_tests`, not a tag — a single
    config selector that targets every CLI-managed (generated + adopted) test."""
    project = _copy_dbt_project(tmp_path)
    captured: dict[str, list[str]] = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="ok", stderr="")

    with mock.patch.object(subprocess, "run", side_effect=fake_run):
        run_dbt_test(project, target=None, profiles_dir=None)

    args = captured["args"]
    selectors = [args[i + 1] for i, a in enumerate(args) if a == "--select"]
    assert selectors == ["config.meta.datacontract_cli.include_in_tests:true"]


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
            "model.proj.orders": {"name": "orders", "resource_type": "model"},
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
    parsed = parse_run_results_file(project, odcs)

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


def test_get_test_metadata_resolves_versioned_model_name():
    """A versioned model's unique_id is `model.project.name.vN`, so the model must be read from the
    manifest node's `name` — not the id's last segment, which is the version. Covers a generic test
    (via `attached_node`) and a singular SQL test (via `depends_on`)."""
    manifest_nodes = {
        "model.proj.orders.v1": {"name": "orders", "resource_type": "model"},
    }
    generic = {"attached_node": "model.proj.orders.v1", "column_name": "order_id"}
    singular = {"depends_on": {"nodes": ["model.proj.orders.v1"]}}

    assert _get_test_metadata(generic, manifest_nodes)[0] == "orders"
    assert _get_test_metadata(singular, manifest_nodes)[0] == "orders"


def test_parse_run_results_derives_key_and_type_from_config_meta(tmp_path: Path):
    """`Check.key` is the fully-qualified key from `config.meta.datacontract_cli.check`;
    `Check.type` is its final `__`-segment (mirrors `CheckSpec.key`/`.type`).

    Falls back to `dbt_test` / no key when no check is present.
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
            "test.proj.a": {
                "name": "a",
                "config": {"meta": {"datacontract_cli": {"check": "orders__order_id__field_required"}}},
            },
            "test.proj.b": {"name": "b", "config": {"meta": {"datacontract_cli": {"check": "orders__row_count"}}}},
            # No check in meta — must fall back to "dbt_test" with no key.
            "test.proj.c": {"name": "c", "config": {"meta": {"datacontract_cli": {}}}},
        }
    }
    (target_dir / "manifest.json").write_text(json.dumps(manifest))

    odcs = resolve_data_contract(str(CONTRACT_PATH))
    parsed = parse_run_results_file(project, odcs)

    by_name = {c.name: c for c in parsed.checks}
    assert by_name["a"].key == "orders__order_id__field_required"
    assert by_name["a"].type == "field_required"
    assert by_name["b"].key == "orders__row_count"
    assert by_name["b"].type == "row_count"
    assert by_name["c"].key is None
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
                        "config": {"meta": {"datacontract_cli": {"model": "orders", "field": "order_id"}}},
                    },
                    # User `quality.query` without `ref()` → `depends_on.nodes` is empty;
                    # meta is the only signal we have for the model.
                    "test.proj.no_ref_quality": {
                        "name": "no_ref_quality",
                        "config": {"meta": {"datacontract_cli": {"model": "orders"}}},
                    },
                }
            }
        )
    )

    odcs = resolve_data_contract(str(CONTRACT_PATH))
    parsed = parse_run_results_file(project, odcs)

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
                                "datacontract_cli": {
                                    "model": "customers",
                                    "field": "email",
                                    "description": "Check that field email matches regex pattern ^[^@]+@[^@]+$",
                                }
                            }
                        },
                    },
                }
            }
        )
    )

    odcs = resolve_data_contract(str(CONTRACT_PATH))
    parsed = parse_run_results_file(project, odcs)
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
    parsed = parse_run_results_file(project, odcs)
    assert len(parsed.checks) == 1
    assert parsed.checks[0].result.value == "passed"


def test_parse_run_results_missing_file(tmp_path: Path):
    project = _copy_dbt_project(tmp_path)
    odcs = resolve_data_contract(str(CONTRACT_PATH))
    parsed = parse_run_results_file(project, odcs)
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
    assert "--run-tests" in plain
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
    assert (project / "models" / "orders.yml").exists()  # generated model YAML (no pre-existing entry)


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
    # The `include_in_tests` selector must actually match the generated tests — otherwise dbt
    # runs nothing and we'd silently report zero checks.
    assert result.run.checks, "dbt selected no managed tests — check the config.meta selector"


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


def test_cli_publish_implies_run(monkeypatch, tmp_path: Path):
    """`--publish` has no meaning without a run, so it implies `--run-tests`: dbt runs and we publish."""
    project = _copy_dbt_project(tmp_path)
    _stub_dbt_test(monkeypatch, project)

    contract = tmp_path / "with-server.odcs.yaml"
    contract.write_text(
        CONTRACT_PATH.read_text()
        + "\nservers:\n  - server: production\n    type: duckdb\n    database: warehouse\n    path: ./w.duckdb\n"
    )

    publish_mock = mock.MagicMock(return_value=True)
    monkeypatch.setattr("datacontract.command_dbt.publish_test_results_to_entropy_data", publish_mock)

    runner = CliRunner()
    result = runner.invoke(
        app,
        ["dbt", "sync", str(contract), "--project-dir", str(project), "--publish", "https://example.com"],
    )
    assert result.exit_code == 0, result.output
    publish_mock.assert_called_once()


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


# ---------------------------------------------------------------------------
# `dbt test` (run-only)
# ---------------------------------------------------------------------------


def _stub_dbt_test_results(monkeypatch, project: Path, results: list, model: str = "orders") -> None:
    """Stub `subprocess.run` so `dbt test` leaves run_results.json + a manifest attributing each
    result to `model` (so `dbt test`'s per-contract model filter keeps them)."""
    target_dir = project / "target"
    target_dir.mkdir(exist_ok=True)
    nodes = {
        r["unique_id"]: {"config": {"meta": {"datacontract_cli": {"model": model, "include_in_tests": True}}}}
        for r in results
    }

    def fake_run(args, **kwargs):
        (target_dir / "run_results.json").write_text(json.dumps({"results": results}))
        (target_dir / "manifest.json").write_text(json.dumps({"nodes": nodes}))
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(shutil, "which", lambda _: "/fake/dbt")
    monkeypatch.setattr(subprocess, "run", fake_run)


def test_dbt_test_command_runs_and_reports(monkeypatch, tmp_path: Path):
    """`dbt test` runs the managed tests sync wrote and reports the parsed results."""
    project = _copy_dbt_project(tmp_path)
    _orders_model_sql(project)
    sync(contract=str(CONTRACT_PATH), project_dir=project, skip_tests=True)  # generate managed tests

    _stub_dbt_test_results(
        monkeypatch, project, [{"unique_id": "test.proj.x.abc", "status": "pass", "failures": 0, "message": None}]
    )

    runner = CliRunner()
    result = runner.invoke(app, ["dbt", "test", str(CONTRACT_PATH), "--project-dir", str(project)])
    assert result.exit_code == 0, result.output
    assert "dbt tests passed" in result.stdout


def test_dbt_test_command_no_managed_tests(monkeypatch, tmp_path: Path):
    """`dbt test` when sync never ran (nothing selected) → soft note, exit 0, hint to run sync."""
    project = _copy_dbt_project(tmp_path)
    _stub_dbt_test_results(monkeypatch, project, [])

    runner = CliRunner()
    result = runner.invoke(app, ["dbt", "test", str(CONTRACT_PATH), "--project-dir", str(project)])
    assert result.exit_code == 0, result.output
    assert "No managed tests found" in result.stdout
    assert "dbt sync" in result.stdout


def test_dbt_test_command_autodiscovers_contract(monkeypatch, tmp_path: Path):
    """`dbt test` with no positional contract resolves the single `*.odcs.yaml` under --project-dir."""
    project = _copy_dbt_project(tmp_path)
    shutil.copy(CONTRACT_PATH, project / "orders.odcs.yaml")
    _stub_dbt_test_results(
        monkeypatch, project, [{"unique_id": "test.proj.x.abc", "status": "pass", "failures": 0, "message": None}]
    )

    runner = CliRunner()
    result = runner.invoke(app, ["dbt", "test", "--project-dir", str(project)])
    assert result.exit_code == 0, result.output
    assert "Resolved contract" in result.stdout


# ---------------------------------------------------------------------------
# Multiple contracts
# ---------------------------------------------------------------------------

_CUSTOMERS_CONTRACT = """\
kind: DataContract
apiVersion: v3.1.0
id: customers-sync-test
name: Customers
version: 1.0.0
status: active
schema:
  - name: customers
    physicalType: table
    properties:
      - name: customer_id
        physicalType: varchar
        primaryKey: true
        primaryKeyPosition: 1
        logicalType: string
        required: true
        unique: true
    quality:
      - description: Row count above 10.
        type: sql
        mustBeGreaterThan: 10
        severity: error
        query: |
          SELECT COUNT(*) AS row_count FROM customers
"""


def _add_customers(project: Path) -> Path:
    """A second resolvable contract + model alongside orders, for multi-contract tests."""
    _orders_model_sql(project, name="customers")
    path = project / "customers.odcs.yaml"
    path.write_text(_CUSTOMERS_CONTRACT)
    return path


def _stub_dbt_test_by_model(monkeypatch, project: Path, results_by_model: dict) -> dict:
    """Stub `dbt test` to emit results attributed to several models. Returns a dict capturing args."""
    target_dir = project / "target"
    target_dir.mkdir(exist_ok=True)
    all_results, nodes = [], {}
    for model, rs in results_by_model.items():
        for r in rs:
            all_results.append(r)
            nodes[r["unique_id"]] = {
                "config": {"meta": {"datacontract_cli": {"model": model, "include_in_tests": True}}}
            }
    captured: dict = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        (target_dir / "run_results.json").write_text(json.dumps({"results": all_results}))
        (target_dir / "manifest.json").write_text(json.dumps({"nodes": nodes}))
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    monkeypatch.setattr(shutil, "which", lambda _: "/fake/dbt")
    monkeypatch.setattr(subprocess, "run", fake_run)
    return captured


def test_sync_discovers_and_syncs_all_contracts(tmp_path: Path):
    """No positional → every `*.odcs.yaml` under the project is synced, each reported with its name."""
    project = _copy_dbt_project(tmp_path)
    _orders_model_sql(project)
    shutil.copy(CONTRACT_PATH, project / "orders.odcs.yaml")
    _add_customers(project)

    runner = CliRunner()
    result = runner.invoke(app, ["dbt", "sync", "--project-dir", str(project), "--skip-tests"])
    assert result.exit_code == 0, result.output
    assert "orders.odcs.yaml: Synced" in result.stdout
    assert "customers.odcs.yaml: Synced" in result.stdout


def test_sync_overlapping_model_is_hard_error(tmp_path: Path):
    """Two contracts claiming the same dbt model abort the whole run before writing anything."""
    project = _copy_dbt_project(tmp_path)
    _orders_model_sql(project)
    shutil.copy(CONTRACT_PATH, project / "orders.odcs.yaml")
    # A second contract that also resolves to the `orders` model.
    (project / "orders-dup.odcs.yaml").write_text(
        _CUSTOMERS_CONTRACT.replace("id: customers-sync-test", "id: orders-dup").replace(
            "name: customers", "name: orders"
        )
    )

    runner = CliRunner()
    result = runner.invoke(app, ["dbt", "sync", "--project-dir", str(project), "--skip-tests"])
    assert result.exit_code == 1
    assert "claimed by different contracts" in result.stdout


def test_sync_glob_selects_matching_contracts(tmp_path: Path):
    """A glob positional expands to every matching contract."""
    project = _copy_dbt_project(tmp_path)
    _orders_model_sql(project)
    shutil.copy(CONTRACT_PATH, project / "orders.odcs.yaml")
    _add_customers(project)

    runner = CliRunner()
    result = runner.invoke(
        app, ["dbt", "sync", str(project / "*.odcs.yaml"), "--project-dir", str(project), "--skip-tests"]
    )
    assert result.exit_code == 0, result.output
    assert "orders.odcs.yaml: Synced" in result.stdout
    assert "customers.odcs.yaml: Synced" in result.stdout


def test_dbt_test_reports_each_contract_separately(monkeypatch, tmp_path: Path):
    """Multi-contract `dbt test` reports (and tallies) each contract's results on its own."""
    project = _copy_dbt_project(tmp_path)
    _orders_model_sql(project)
    shutil.copy(CONTRACT_PATH, project / "orders.odcs.yaml")
    sync(contract=str(project / "orders.odcs.yaml"), project_dir=project, skip_tests=True)
    customers = _add_customers(project)
    sync(contract=str(customers), project_dir=project, skip_tests=True)

    _stub_dbt_test_by_model(
        monkeypatch,
        project,
        {
            "orders": [{"unique_id": "test.proj.o.1", "status": "pass", "failures": 0, "message": None}],
            "customers": [{"unique_id": "test.proj.c.1", "status": "pass", "failures": 0, "message": None}],
        },
    )

    runner = CliRunner()
    result = runner.invoke(app, ["dbt", "test", "--project-dir", str(project)])
    assert result.exit_code == 0, result.output
    assert "Contract results:" in result.stdout
    assert "orders-sync-test@1.0.0" in result.stdout
    assert "customers-sync-test@1.0.0" in result.stdout
    assert "Tested 2 contract(s)" in result.stdout


def test_dbt_test_scopes_selection_to_requested_contract(monkeypatch, tmp_path: Path):
    """A single requested contract scopes the `dbt test` selection to that contract's model."""
    project = _copy_dbt_project(tmp_path)
    _orders_model_sql(project)
    captured = _stub_dbt_test_by_model(
        monkeypatch, project, {"orders": [{"unique_id": "test.proj.o.1", "status": "pass"}]}
    )

    runner = CliRunner()
    result = runner.invoke(app, ["dbt", "test", str(CONTRACT_PATH), "--project-dir", str(project)])
    assert result.exit_code == 0, result.output
    selectors = [captured["args"][i + 1] for i, a in enumerate(captured["args"]) if a == "--select"]
    assert selectors == [
        "orders,config.meta.datacontract_cli.include_in_tests:true,config.meta.datacontract_cli.contract_versions:1.0.0",
        "config.meta.datacontract_cli.model:orders,config.meta.datacontract_cli.include_in_tests:true,"
        "config.meta.datacontract_cli.contract_versions:1.0.0",
    ]


def test_sync_second_contract_keeps_first_contracts_singular_sql(tmp_path: Path):
    """Syncing a second contract must not wipe the first contract's generated singular SQL (#bug)."""
    project = _copy_dbt_project(tmp_path)
    _orders_model_sql(project)
    sync(contract=str(CONTRACT_PATH), project_dir=project, skip_tests=True)
    _, tests_dir = _resolved_generated_dirs(project)
    orders_singular = list((tests_dir / "orders_sync_test").glob("*.sql"))
    assert orders_singular, "orders contract should have produced a singular SQL test"

    customers = _add_customers(project)
    sync(contract=str(customers), project_dir=project, skip_tests=True)

    assert all(p.exists() for p in orders_singular), "second sync wiped the first contract's singular SQL"
    assert list((tests_dir / "customers_sync_test").glob("*.sql")), "customers singular SQL was not written"


def _orders_contract_at_version(project: Path, version: str) -> Path:
    """A copy of the orders contract (same id) at a different version, for version-wipe tests."""
    text = CONTRACT_PATH.read_text().replace("version: 1.0.0", f"version: {version}")
    path = project / f"orders-{version}.odcs.yaml"
    path.write_text(text)
    return path


def test_sync_bump_version_keeps_old_singular_sql(tmp_path: Path):
    """A version bump keeps the prior version's singular SQL — retiring a version is always manual."""
    project = _copy_dbt_project(tmp_path)
    _orders_model_sql(project)
    _, tests_dir = _resolved_generated_dirs(project)
    subdir = tests_dir / "orders_sync_test"

    sync(contract=str(_orders_contract_at_version(project, "1.0.0")), project_dir=project, skip_tests=True)
    assert list(subdir.glob("orders_sync_test__1_0_0__*.sql"))

    sync(contract=str(_orders_contract_at_version(project, "2.0.0")), project_dir=project, skip_tests=True)
    assert list(subdir.glob("orders_sync_test__1_0_0__*.sql")), "old version's singular SQL was dropped"
    assert list(subdir.glob("orders_sync_test__2_0_0__*.sql")), "new version's tests were not written"


def test_sync_same_id_two_versions_coexist(tmp_path: Path):
    """Syncing a second version of the same id keeps the first version's singular SQL."""
    project = _copy_dbt_project(tmp_path)
    _orders_model_sql(project)
    _, tests_dir = _resolved_generated_dirs(project)
    subdir = tests_dir / "orders_sync_test"

    generate_dbt_tests(contract=str(_orders_contract_at_version(project, "1.0.0")), project_dir=project)
    generate_dbt_tests(contract=str(_orders_contract_at_version(project, "2.0.0")), project_dir=project)
    assert list(subdir.glob("orders_sync_test__1_0_0__*.sql")), "sibling version's tests were dropped"
    assert list(subdir.glob("orders_sync_test__2_0_0__*.sql")), "current version's tests missing"


def test_sync_migrates_v1_0_9_flat_singular_sql(tmp_path: Path):
    """A leftover flat `datacontract_cli/*.sql` from v1.0.9 is removed and replaced by the subdir layout."""
    project = _copy_dbt_project(tmp_path)
    _orders_model_sql(project)
    _, tests_dir = _resolved_generated_dirs(project)
    tests_dir.mkdir(parents=True, exist_ok=True)
    flat = tests_dir / "orders_sync_test__orders__order_id__length.sql"
    flat.write_text("-- AUTO-GENERATED by `datacontract dbt sync`. Do not edit.\nselect 1\n")

    sync(contract=str(CONTRACT_PATH), project_dir=project, skip_tests=True)

    assert not flat.exists(), "the old flat-layout singular SQL was not migrated away"
    assert list((tests_dir / "orders_sync_test").glob("*.sql")), "subdir layout not written"


# ---------------------------------------------------------------------------
# Filename → dbt model version parsing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "filename,expected",
    [
        ("orders-v2.odcs.yaml", "2"),
        ("orders_v2.odcs.yaml", "2"),
        ("orders.v3.odcs.yaml", "3"),
        ("orders-v02.odcs.yaml", "2"),  # zero-padded normalized
        ("orders-v2-v2.odcs.yaml", "2"),  # repeated same token is not ambiguous
        ("orders.odcs.yaml", None),  # no token
        ("rev2-orders.odcs.yaml", None),  # `v` after a letter is not a token
    ],
)
def test_parse_filename_version(filename: str, expected: Optional[str]):
    assert parse_filename_version(Path("/some/dir") / filename) == expected


def test_parse_filename_version_ambiguous_raises():
    with pytest.raises(DataContractException, match="multiple version tokens"):
        parse_filename_version(Path("orders-v1-v2.odcs.yaml"))


# ---------------------------------------------------------------------------
# Versioned models: multiple contract versions → one dbt versioned model
# ---------------------------------------------------------------------------

_V1_CONTRACT = """\
kind: DataContract
apiVersion: v3.1.0
id: shop
name: Shop
version: 1.0.0
status: active
schema:
  - name: customers
    properties:
      - name: id
        logicalType: string
        primaryKey: true
        required: true
        unique: true
      - name: status
        logicalType: string
        customProperties:
          - property: enum
            value: [a, b]
"""

_V2_CONTRACT = """\
kind: DataContract
apiVersion: v3.1.0
id: shop
name: Shop
version: 2.0.0
status: active
schema:
  - name: customers
    properties:
      - name: id
        logicalType: string
        primaryKey: true
        required: true
        unique: true
      - name: status
        logicalType: string
        customProperties:
          - property: enum
            value: [a, b, c]
      - name: region
        logicalType: string
        required: true
"""


def _versioned_project(tmp_path: Path) -> Path:
    """A dbt project with `customers_v1.sql` / `customers_v2.sql` and both contract files."""
    project = _copy_dbt_project(tmp_path)
    (project / "models" / "customers_v1.sql").write_text("select 1 as id")
    (project / "models" / "customers_v2.sql").write_text("select 1 as id")
    (project / "customers-v1.odcs.yaml").write_text(_V1_CONTRACT)
    (project / "customers-v2.odcs.yaml").write_text(_V2_CONTRACT)
    return project


def _sync_versioned(project: Path, filename: str, version: str) -> None:
    generate_dbt_tests(contract=str(project / filename), project_dir=project, model_version=version)


def _versioned_entry(project: Path) -> dict:
    y = yaml.safe_load((project / "models" / "customers.yml").read_text())
    return y["models"][0]


def _cv(test: dict) -> list:
    body = next(iter(test.values()))
    return body["config"]["meta"]["datacontract_cli"]["contract_versions"]


def _col(entry: dict, name: str) -> dict:
    return {c["name"]: c for c in entry.get("columns", [])}[name]


def _bullet(entry: dict, v: int) -> dict:
    return {b["v"]: b for b in entry["versions"]}[v]


def test_versioned_sync_builds_versions_block(tmp_path: Path):
    project = _versioned_project(tmp_path)
    _sync_versioned(project, "customers-v1.odcs.yaml", "1")
    _sync_versioned(project, "customers-v2.odcs.yaml", "2")

    entry = _versioned_entry(project)
    assert entry["latest_version"] == 2
    # No `contract_versions` on the model entry (it would cascade to every test node); the bullets
    # carry `contract_version` instead so the CLI can map an ODCS version to its dbt model version.
    assert "contract_versions" not in entry["config"]["meta"]["datacontract_cli"]
    assert _bullet(entry, 1)["config"]["meta"]["datacontract_cli"]["contract_version"] == "1.0.0"
    assert _bullet(entry, 2)["config"]["meta"]["datacontract_cli"]["contract_version"] == "2.0.0"

    # v1 lacks region (added in v2) → excluded; v2 has every column → no exclude element.
    v1_inc = [e for e in _bullet(entry, 1)["columns"] if "include" in e][0]
    assert v1_inc["exclude"] == ["region"]
    assert all("exclude" not in e for e in _bullet(entry, 2).get("columns", []) if "include" in e)

    # Shared columns carry both versions; version-specific columns carry only their own.
    id_tests = {next(iter(t)): _cv(t) for t in _col(entry, "id")["data_tests"]}
    assert id_tests["not_null"] == ["1.0.0", "2.0.0"]
    assert id_tests["unique"] == ["1.0.0", "2.0.0"]
    assert _cv(_col(entry, "region")["data_tests"][0]) == ["2.0.0"]


def _override(entry: dict, v: int, col: str) -> dict:
    return {e["name"]: e for e in _bullet(entry, v)["columns"] if "name" in e}[col]


def test_versioned_sync_divergent_column_goes_to_override(tmp_path: Path):
    project = _versioned_project(tmp_path)
    _sync_versioned(project, "customers-v1.odcs.yaml", "1")
    _sync_versioned(project, "customers-v2.odcs.yaml", "2")

    entry = _versioned_entry(project)
    # `status` diverges (enum grows in v2). dbt COMBINES a version override with the top-level column,
    # so a divergent column must have NO top-level tests — each version carries its full set in its bullet.
    assert "data_tests" not in _col(entry, "status")
    v1_status = _override(entry, 1, "status")["data_tests"][0]
    assert v1_status["accepted_values"]["values"] == ["a", "b"]
    assert _cv(v1_status) == ["1.0.0"]
    v2_status = _override(entry, 2, "status")["data_tests"][0]
    assert v2_status["accepted_values"]["values"] == ["a", "b", "c"]
    assert _cv(v2_status) == ["2.0.0"]

    # Each override must ride alongside an `include: '*'` element, else dbt reads the version as having only `status`.
    for v in (1, 2):
        assert [e for e in _bullet(entry, v)["columns"] if "include" in e][0]["include"] == "*"


def _effective(entry: dict) -> dict:
    """Order-independent semantic fingerprint: {version: {column: {test: (args, frozenset(versions))}}}."""
    top = {c["name"]: c for c in entry.get("columns", [])}
    out = {}
    for bullet in entry.get("versions", []):
        inc = [e for e in bullet.get("columns", []) if "include" in e]
        exclude = set(inc[0].get("exclude", []) if inc else [])
        overrides = {e["name"]: e for e in bullet.get("columns", []) if "name" in e}
        cols = {}
        for name, col in top.items():
            if name in exclude:
                continue
            src = overrides.get(name, col)
            tests = {}
            for t in src.get("data_tests", []):
                tn = next(iter(t))
                body = t[tn]
                args = tuple(
                    sorted(
                        (k, tuple(v) if isinstance(v, list) else v)
                        for k, v in body.items()
                        if k not in ("config", "description")
                    )
                )
                tests[tn] = (args, frozenset(body["config"]["meta"]["datacontract_cli"]["contract_versions"]))
            cols[name] = tests
        out[str(bullet["v"])] = cols
    return out


def test_versioned_sync_confluent_regardless_of_order(tmp_path: Path):
    forward = _versioned_project(tmp_path / "fwd")
    _sync_versioned(forward, "customers-v1.odcs.yaml", "1")
    _sync_versioned(forward, "customers-v2.odcs.yaml", "2")

    reverse = _versioned_project(tmp_path / "rev")
    _sync_versioned(reverse, "customers-v2.odcs.yaml", "2")
    _sync_versioned(reverse, "customers-v1.odcs.yaml", "1")

    fe, re_ = _effective(_versioned_entry(forward)), _effective(_versioned_entry(reverse))
    assert fe == re_
    assert _versioned_entry(forward)["latest_version"] == _versioned_entry(reverse)["latest_version"] == 2


def test_versioned_sync_keeps_sibling_version_behavior(tmp_path: Path):
    project = _versioned_project(tmp_path)
    _sync_versioned(project, "customers-v1.odcs.yaml", "1")
    _sync_versioned(project, "customers-v2.odcs.yaml", "2")
    entry = _versioned_entry(project)
    # v1's effective slice is unchanged by the v2 sync: it still excludes region and still tests
    # `status` against [a,b] (relocated from top level to v1's bullet when v2 made the column diverge).
    assert [e for e in _bullet(entry, 1)["columns"] if "include" in e][0]["exclude"] == ["region"]
    assert _override(entry, 1, "status")["data_tests"][0]["accepted_values"]["values"] == ["a", "b"]


_V2_NO_REGION = _V2_CONTRACT.replace("      - name: region\n        logicalType: string\n        required: true\n", "")


def test_versioned_prune_drops_version_only_column(tmp_path: Path):
    project = _versioned_project(tmp_path)
    _sync_versioned(project, "customers-v1.odcs.yaml", "1")
    _sync_versioned(project, "customers-v2.odcs.yaml", "2")
    assert "region" in {c["name"] for c in _versioned_entry(project).get("columns", [])}

    # region is a v2-only column. Drop it from v2 and re-sync v2 with --prune.
    (project / "customers-v2.odcs.yaml").write_text(_V2_NO_REGION)
    generate_dbt_tests(
        contract=str(project / "customers-v2.odcs.yaml"), project_dir=project, model_version="2", prune=True
    )

    entry = _versioned_entry(project)
    # region was referenced only by v2; now dropped → pruned from the shared columns entirely,
    # and cleared from v1's exclude list (nothing references it anymore).
    assert "region" not in {c["name"] for c in entry.get("columns", [])}
    assert "region" not in [e for e in _bullet(entry, 1)["columns"] if "include" in e][0].get("exclude", [])
    # v1's slice is untouched: still tests `status` against [a, b].
    assert _override(entry, 1, "status")["data_tests"][0]["accepted_values"]["values"] == ["a", "b"]


def test_versioned_prune_leaves_sibling_shared_column(tmp_path: Path):
    """Pruning a column from one version must not remove it when a sibling version still declares it."""
    project = _versioned_project(tmp_path)
    _sync_versioned(project, "customers-v1.odcs.yaml", "1")
    _sync_versioned(project, "customers-v2.odcs.yaml", "2")

    # Drop `status` from v2 only (v1 still has it). With --prune on v2, `status` must survive for v1.
    v2_no_status = _V2_NO_REGION.replace(
        "      - name: status\n        logicalType: string\n        customProperties:\n"
        "          - property: enum\n            value: [a, b, c]\n",
        "",
    )
    (project / "customers-v2.odcs.yaml").write_text(v2_no_status)
    generate_dbt_tests(
        contract=str(project / "customers-v2.odcs.yaml"), project_dir=project, model_version="2", prune=True
    )

    entry = _versioned_entry(project)
    # status is still referenced by v1 → kept; v2 now excludes it.
    assert _override(entry, 1, "status")["data_tests"][0]["accepted_values"]["values"] == ["a", "b"]
    assert "status" in [e for e in _bullet(entry, 2)["columns"] if "include" in e][0].get("exclude", [])


def test_sync_cli_versioned_two_contracts(tmp_path: Path):
    """`dbt sync customers-v1 customers-v2` builds one versioned model from both contracts."""
    project = _versioned_project(tmp_path)
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "dbt",
            "sync",
            str(project / "customers-v1.odcs.yaml"),
            str(project / "customers-v2.odcs.yaml"),
            "--project-dir",
            str(project),
            "--skip-tests",
        ],
    )
    assert result.exit_code == 0, result.output
    entry = _versioned_entry(project)
    assert {b["v"] for b in entry["versions"]} == {1, 2}
    assert entry["latest_version"] == 2


def test_sync_same_id_missing_v_token_errors(tmp_path: Path):
    """Two same-id contracts sharing a model but lacking a mappable `v<N>` are a hard error."""
    project = _copy_dbt_project(tmp_path)
    _orders_model_sql(project)  # a plain `orders.sql`, not versioned
    shutil.copy(CONTRACT_PATH, project / "orders.odcs.yaml")
    (project / "orders-2024.odcs.yaml").write_text(
        CONTRACT_PATH.read_text().replace("version: 1.0.0", "version: 2.0.0")
    )

    runner = CliRunner()
    result = runner.invoke(app, ["dbt", "sync", "--project-dir", str(project), "--skip-tests"])
    assert result.exit_code == 1
    assert "can't map to dbt model versions" in result.stdout


def test_dbt_test_versioned_selector_targets_version_node(monkeypatch, tmp_path: Path):
    """`dbt test` on a versioned contract scopes selection to the `model.vN` node."""
    project = _versioned_project(tmp_path)
    sync(contract=str(project / "customers-v1.odcs.yaml"), project_dir=project, skip_tests=True)
    generate_dbt_tests(contract=str(project / "customers-v2.odcs.yaml"), project_dir=project, model_version="2")
    captured = _stub_dbt_test_by_model(
        monkeypatch, project, {"customers": [{"unique_id": "test.proj.c.1", "status": "pass"}]}
    )

    runner = CliRunner()
    result = runner.invoke(app, ["dbt", "test", str(project / "customers-v2.odcs.yaml"), "--project-dir", str(project)])
    assert result.exit_code == 0, result.output
    selectors = [captured["args"][i + 1] for i, a in enumerate(captured["args"]) if a == "--select"]
    assert selectors == [
        "customers.v2,config.meta.datacontract_cli.include_in_tests:true,"
        "config.meta.datacontract_cli.contract_versions:2.0.0",
        "config.meta.datacontract_cli.model:customers,config.meta.datacontract_cli.include_in_tests:true,"
        "config.meta.datacontract_cli.contract_versions:2.0.0",
    ]


def test_versioned_sync_same_version_twice_is_idempotent(tmp_path: Path):
    """Re-syncing the same version doesn't duplicate tests or accumulate versions in the membership list."""
    project = _versioned_project(tmp_path)
    _sync_versioned(project, "customers-v1.odcs.yaml", "1")
    _sync_versioned(project, "customers-v2.odcs.yaml", "2")
    first = (project / "models" / "customers.yml").read_text()

    _sync_versioned(project, "customers-v1.odcs.yaml", "1")
    _sync_versioned(project, "customers-v2.odcs.yaml", "2")
    second = (project / "models" / "customers.yml").read_text()

    assert first == second  # a no-op re-sync is a fixed point
    entry = _versioned_entry(project)
    id_not_null = _col(entry, "id")["data_tests"][0]
    assert _cv(id_not_null) == ["1.0.0", "2.0.0"]  # not ["1.0.0","2.0.0","1.0.0","2.0.0"]
