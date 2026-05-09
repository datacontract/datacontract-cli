"""Unit + integration tests for `datacontract dbt sync` (PR B MVP)."""

from __future__ import annotations

import json
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional
from unittest import mock

import pytest
import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.integration.dbt_sync import (
    GENERATED_MODELS_DIR,
    GENERATED_TESTS_DIR,
    ModelResolution,
    _attach_test_config,
    _build_singular_sql,
    _check_dbt_on_path,
    _ensure_dbt_project,
    _rewrite_relationships_to_ref,
    detect_user_model_collisions,
    find_contract,
    generate_dbt_tests,
    generate_dbt_tests_for_schema,
    parse_run_results,
    resolve_model_names,
    run_dbt_test,
    run_tests,
    wipe_output_dirs,
)
from datacontract.lint.resolve import resolve_data_contract
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import Run

FIXTURE_DIR = Path(__file__).parent / "fixtures" / "dbt_sync"
CONTRACT_PATH = FIXTURE_DIR / "orders.odcs.yaml"
DBT_PROJECT_TEMPLATE = FIXTURE_DIR / "dbt_project"


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
) -> _SyncResult:
    """End-to-end orchestration helper for tests — mirrors what the CLI does."""
    if not skip_tests:
        _check_dbt_on_path()
    gen = generate_dbt_tests(
        contract=contract,
        project_dir=project_dir,
        schema_name=schema_name,
        model_resolution=model_resolution,
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


def test_ensure_dbt_project_ok(tmp_path: Path):
    project = _copy_dbt_project(tmp_path)
    _ensure_dbt_project(project)


def test_ensure_dbt_project_missing_raises(tmp_path: Path):
    with pytest.raises(DataContractException, match=r"dbt_project\.yml.*not found.*--project-dir"):
        _ensure_dbt_project(tmp_path)


# ---------------------------------------------------------------------------
# dbt PATH preflight
# ---------------------------------------------------------------------------


def test_check_dbt_on_path_missing(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _: None)
    with pytest.raises(DataContractException, match="dbt not found on PATH"):
        _check_dbt_on_path()


def test_check_dbt_on_path_present(monkeypatch):
    monkeypatch.setattr(shutil, "which", lambda _: "/fake/dbt")
    assert _check_dbt_on_path() == "/fake/dbt"


# ---------------------------------------------------------------------------
# Wipe-and-regen
# ---------------------------------------------------------------------------


def test_wipe_output_dirs_clears_existing(tmp_path: Path):
    project = _copy_dbt_project(tmp_path)
    leftover_yml = project / GENERATED_MODELS_DIR / "leftover.yml"
    leftover_sql = project / GENERATED_TESTS_DIR / "leftover.sql"
    leftover_yml.parent.mkdir(parents=True, exist_ok=True)
    leftover_sql.parent.mkdir(parents=True, exist_ok=True)
    leftover_yml.write_text("# stale")
    leftover_sql.write_text("-- stale")

    wipe_output_dirs(project)

    assert not leftover_yml.exists()
    assert not leftover_sql.exists()
    assert (project / GENERATED_MODELS_DIR).is_dir()
    assert (project / GENERATED_TESTS_DIR).is_dir()


# ---------------------------------------------------------------------------
# Preflight: user-authored model-entry collisions
# ---------------------------------------------------------------------------


def test_detect_user_model_collisions_finds_overlap(tmp_path: Path):
    project = _copy_dbt_project(tmp_path)
    schema_yml = project / "models" / "schema.yml"
    schema_yml.write_text("version: 2\nmodels:\n  - name: orders\n  - name: customers\n")
    hits = detect_user_model_collisions(project, {"orders", "stg_orders"})
    assert hits == {"orders": [schema_yml]}


def test_detect_user_model_collisions_ignores_generated_dir(tmp_path: Path):
    project = _copy_dbt_project(tmp_path)
    gen_dir = project / GENERATED_MODELS_DIR
    gen_dir.mkdir(parents=True, exist_ok=True)
    (gen_dir / "auto.yml").write_text("version: 2\nmodels:\n  - name: orders\n")
    assert detect_user_model_collisions(project, {"orders"}) == {}


def test_detect_user_model_collisions_handles_yaml_extension(tmp_path: Path):
    project = _copy_dbt_project(tmp_path)
    schema = project / "models" / "schema.yaml"
    schema.write_text("version: 2\nmodels:\n  - name: orders\n")
    assert detect_user_model_collisions(project, {"orders"}) == {"orders": [schema]}


def test_detect_user_model_collisions_skips_unparseable_yaml(tmp_path: Path):
    project = _copy_dbt_project(tmp_path)
    bad = project / "models" / "broken.yml"
    bad.write_text(": this is : not : yaml")
    assert detect_user_model_collisions(project, {"orders"}) == {}


def test_sync_preflight_blocks_on_collision(tmp_path: Path):
    project = _copy_dbt_project(tmp_path)
    (project / "models" / "schema.yml").write_text("version: 2\nmodels:\n  - name: orders\n")
    with pytest.raises(DataContractException) as exc:
        sync(contract=str(CONTRACT_PATH), project_dir=project, skip_tests=True)
    msg = exc.value.reason
    assert "`orders`" in msg
    assert "models/schema.yml" in msg
    assert "single source of truth" in msg
    # Preflight runs BEFORE wipe — confirm we didn't materialize anything.
    assert not (project / GENERATED_MODELS_DIR).exists() or not list((project / GENERATED_MODELS_DIR).iterdir())


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


def test_resolve_model_names_physicalname_unresolvable():
    odcs = resolve_data_contract(str(CONTRACT_PATH))
    assert resolve_model_names(odcs, ModelResolution.physicalName) == {"orders": None}


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
    result = _attach_test_config({"accepted_values": {"values": [1, 2]}}, "error")
    assert result == {
        "accepted_values": {
            "values": [1, 2],
            "config": {"severity": "error", "tags": ["datacontract_cli"]},
        }
    }


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

    # Sync-specific: every YAML test carries the datacontract_cli tag via inline config.
    cols = {c["name"]: c for c in model_dict["columns"]}
    for t in cols["order_id"]["data_tests"]:
        assert isinstance(t, dict)
        (args,) = t.values()
        assert args["config"]["tags"] == ["datacontract_cli"]

    # Single-PK in this fixture → no model-level data_tests.
    assert "data_tests" not in model_dict

    # Singular SQL: one column-level (95% rule), one model-level (row count).
    assert len(singulars) == 2
    assert all(s.filename.startswith("orders_sync_test__orders__") for s in singulars)
    assert all(s.filename.endswith(".sql") for s in singulars)
    assert any(s.description and "95%" in s.description for s in singulars)


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


def test_generate_outputs_singular_sql_carries_severity_and_tag():
    odcs = resolve_data_contract(str(CONTRACT_PATH))
    schema_obj = odcs.schema_[0]
    _, singulars = generate_dbt_tests_for_schema(odcs, schema_obj, "orders", Run.create_run())

    row_count = next(s for s in singulars if "row_count" in s.filename or "row" in s.filename.lower())
    # severity=error normalized from `severity: error` in the fixture
    assert "severity='error'" in row_count.sql
    assert "tags=['datacontract_cli']" in row_count.sql


def test_build_singular_sql_header_and_config():
    sql = _build_singular_sql("SELECT 1", "warn", "my-contract", "orders")
    assert "AUTO-GENERATED" in sql
    assert "my-contract" in sql
    assert "orders" in sql
    assert "{{ config(severity='warn', tags=['datacontract_cli']) }}" in sql


# ---------------------------------------------------------------------------
# End-to-end (no dbt invocation)
# ---------------------------------------------------------------------------


def test_sync_skip_tests_writes_files(tmp_path: Path):
    project = _copy_dbt_project(tmp_path)
    result = sync(
        contract=str(CONTRACT_PATH),
        project_dir=project,
        skip_tests=True,
    )

    assert len(result.written_yaml) == 1
    yml = result.written_yaml[0]
    assert yml.exists()
    content = yml.read_text()
    assert content.startswith("# AUTO-GENERATED")
    assert str(CONTRACT_PATH.resolve()) in content
    parsed = yaml.safe_load(content)
    assert parsed["models"][0]["name"] == "orders"
    # singular tests with descriptions get a top-level `data_tests:` companion
    assert "data_tests" in parsed
    assert any(entry.get("description") for entry in parsed["data_tests"])

    # Both singular SQL files materialize on disk.
    assert len(result.written_sql) == 2
    for sql_path in result.written_sql:
        assert sql_path.exists()
        assert "AUTO-GENERATED" in sql_path.read_text()


def test_sync_filter_to_unknown_schema_errors(tmp_path: Path):
    project = _copy_dbt_project(tmp_path)
    with pytest.raises(DataContractException, match="not found"):
        sync(
            contract=str(CONTRACT_PATH),
            project_dir=project,
            schema_name="not_a_schema",
            skip_tests=True,
        )


def test_sync_missing_contract_raises(tmp_path: Path):
    project = _copy_dbt_project(tmp_path)
    with pytest.raises(DataContractException, match="not found"):
        sync(
            contract=str(tmp_path / "missing.yaml"),
            project_dir=project,
            skip_tests=True,
        )


# ---------------------------------------------------------------------------
# Subprocess + run_results parsing
# ---------------------------------------------------------------------------


def test_run_dbt_test_selector_unions_tag_and_models(tmp_path: Path):
    project = _copy_dbt_project(tmp_path)
    captured: dict[str, list[str]] = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="ok", stderr="")

    with mock.patch.object(subprocess, "run", side_effect=fake_run):
        run_dbt_test(project, ["orders", "customers"], target=None, profiles_dir=None)

    args = captured["args"]
    select_idx = args.index("--select")
    selectors = args[select_idx + 1 : args.index("--project-dir")]
    assert selectors == ["tag:datacontract_cli", "orders", "customers"]


def test_run_dbt_test_decorates_duplicate_test_error(tmp_path: Path):
    project = _copy_dbt_project(tmp_path)
    duplicate_stderr = (
        'Compilation Error\n  dbt found two tests with the name "not_null_orders_id" in the same project\n'
    )

    def fake_run(args, **kwargs):
        return subprocess.CompletedProcess(args=args, returncode=2, stdout="", stderr=duplicate_stderr)

    with mock.patch.object(subprocess, "run", side_effect=fake_run):
        with pytest.raises(DataContractException) as exc:
            run_dbt_test(project, ["orders"], target=None, profiles_dir=None)

    msg = exc.value.reason
    assert "models/datacontract_cli/" in msg
    assert "contract is the source of truth" in msg


def test_run_dbt_test_surfaces_failure_when_no_run_results(tmp_path: Path):
    """If dbt fails before producing run_results.json, sync must surface — not swallow — the error."""
    project = _copy_dbt_project(tmp_path)
    parse_stderr = "Compilation Error\n  some unrelated parse failure\n"

    def fake_run(args, **kwargs):
        return subprocess.CompletedProcess(args=args, returncode=2, stdout="", stderr=parse_stderr)

    with mock.patch.object(subprocess, "run", side_effect=fake_run):
        with pytest.raises(DataContractException) as exc:
            run_dbt_test(project, ["orders"], target=None, profiles_dir=None)

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
        result = run_dbt_test(project, ["orders"], target=None, profiles_dir=None)
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
            run_dbt_test(project, ["orders"], target=None, profiles_dir=None)
    assert not stale.exists()


def test_run_dbt_test_target_and_profiles_forwarded(tmp_path: Path):
    project = _copy_dbt_project(tmp_path)
    captured: dict[str, list[str]] = {}

    def fake_run(args, **kwargs):
        captured["args"] = args
        return subprocess.CompletedProcess(args=args, returncode=0, stdout="", stderr="")

    with mock.patch.object(subprocess, "run", side_effect=fake_run):
        run_dbt_test(
            project,
            ["orders"],
            target="dev",
            profiles_dir=tmp_path / "profiles",
        )

    args = captured["args"]
    assert "--target" in args and args[args.index("--target") + 1] == "dev"
    assert "--profiles-dir" in args


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
    runner = CliRunner(env={"COLUMNS": "200"})
    result = runner.invoke(app, ["dbt", "sync", "--help"])
    assert result.exit_code == 0
    assert "Generate dbt tests" in result.stdout
    assert "--skip-tests" in result.stdout
    assert "--schema-name" in result.stdout


def test_cli_skip_tests_invocation(tmp_path: Path):
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
        ],
    )
    if result.exit_code != 0:
        sys.stderr.write(result.output)
        if result.exception:
            raise result.exception
    assert result.exit_code == 0
    assert (project / GENERATED_MODELS_DIR / "orders_sync_test__orders.yml").exists()


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
