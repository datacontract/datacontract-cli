"""Core logic for `datacontract dbt sync`."""

from __future__ import annotations

import json
import logging
import re
import shutil
import subprocess
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from pathlib import Path
from typing import Any, List, Optional, Tuple

import yaml
from open_data_contract_standard.model import (
    DataQuality,
    OpenDataContractStandard,
    SchemaObject,
    SchemaProperty,
)
from rich.console import Console

from datacontract.integration.dbt_test_mapping import field_to_data_tests
from datacontract.lint.resolve import resolve_data_contract
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import Check, ResultEnum, Run

logger = logging.getLogger(__name__)

OUTPUT_TAG = "datacontract_cli"
GENERATED_MODELS_DIR = Path("models") / "datacontract_cli"
GENERATED_TESTS_DIR = Path("tests") / "datacontract_cli"


class ModelResolution(str, Enum):
    name = "name"
    physicalName = "physicalName"


# ---------------------------------------------------------------------------
# Contract / project resolution
# ---------------------------------------------------------------------------


def find_contract(cwd: Path) -> Path:
    """Recursive `*.odcs.yaml` search; raise on 0 or >1 matches."""
    candidates = sorted(p for p in cwd.rglob("*.odcs.yaml") if p.is_file())
    if not candidates:
        raise DataContractException(
            type="dbt_sync",
            name="resolve contract",
            reason=(
                f"No `*.odcs.yaml` found below {cwd}. "
                "Pass the contract path explicitly: `datacontract dbt sync <contract>`."
            ),
            engine="dbt-sync",
        )
    if len(candidates) > 1:
        shown = candidates[:10]
        listing = "\n  - ".join(str(c.relative_to(cwd)) for c in shown)
        more = f"\n  ... and {len(candidates) - len(shown)} more" if len(candidates) > len(shown) else ""
        raise DataContractException(
            type="dbt_sync",
            name="resolve contract",
            reason=(
                f"Multiple `*.odcs.yaml` files found below {cwd}:\n  - {listing}{more}\n"
                "Pass one explicitly: `datacontract dbt sync <contract>`."
            ),
            engine="dbt-sync",
        )
    return candidates[0]


def _ensure_dbt_project(project_dir: Path) -> None:
    if not (project_dir / "dbt_project.yml").is_file():
        raise DataContractException(
            type="dbt_sync",
            name="resolve dbt project",
            reason=(
                f"`dbt_project.yml` not found in {project_dir}. Pass `--project-dir` to point at a dbt project root."
            ),
            engine="dbt-sync",
        )


def _check_dbt_on_path() -> str:
    dbt_path = shutil.which("dbt")
    if not dbt_path:
        raise DataContractException(
            type="dbt_sync",
            name="dbt preflight",
            reason="""\
dbt not found on PATH. If you want to update the dbt project without running the tests, pass `--skip-tests`.

Otherwise the dbt adapter that matches your warehouse, e.g.:
  pip install dbt-postgres        # Postgres
  pip install dbt-snowflake       # Snowflake
  pip install dbt-bigquery        # BigQuery
  pip install dbt-databricks      # Databricks
  pip install dbt-duckdb          # DuckDB (for local testing)

Full list of adapters: https://docs.getdbt.com/docs/supported-data-platforms
Install guide: https://docs.getdbt.com/docs/core/installation-overview""",
            engine="dbt-sync",
        )
    return dbt_path


# ---------------------------------------------------------------------------
# Model resolution
# ---------------------------------------------------------------------------


def resolve_model_names(
    odcs: OpenDataContractStandard,
    strategy: ModelResolution,
    schema_filter: str = "all",
) -> dict[str, Optional[str]]:
    """Map `schema.name` → dbt model name (or ``None`` if unresolvable)."""
    mapping: dict[str, Optional[str]] = {}
    schemas = odcs.schema_ or []
    if schema_filter != "all":
        schemas = [s for s in schemas if s.name == schema_filter]
        if not schemas:
            available = ", ".join(s.name for s in (odcs.schema_ or []) if s.name) or "(none)"
            raise DataContractException(
                type="dbt_sync",
                name="resolve schema",
                reason=f"Schema `{schema_filter}` not found in contract. Available: {available}.",
                engine="dbt-sync",
            )
    for schema_obj in schemas:
        if not schema_obj.name:
            continue
        if strategy == ModelResolution.name:
            mapping[schema_obj.name] = schema_obj.name
        elif strategy == ModelResolution.physicalName:
            mapping[schema_obj.name] = schema_obj.physicalName or None
    return mapping


# ---------------------------------------------------------------------------
# Output filesystem management
# ---------------------------------------------------------------------------


def wipe_output_dirs(project_dir: Path) -> None:
    for sub in (GENERATED_MODELS_DIR, GENERATED_TESTS_DIR):
        target = project_dir / sub
        if target.exists():
            shutil.rmtree(target)
        target.mkdir(parents=True, exist_ok=True)


# ---------------------------------------------------------------------------
# Test emission
# ---------------------------------------------------------------------------


def _normalize_severity(severity: Optional[str]) -> str:
    if severity and severity.lower() in {"error", "critical", "high", "fatal"}:
        return "error"
    return "warn"


def _attach_test_config(test: Any, severity: str) -> Any:
    """Wrap a test entry with `config: { severity, tags }`.

    Strings (`"not_null"`) become single-key dicts so the config can ride along
    in the same form dbt accepts.
    """
    config = {"severity": severity, "tags": [OUTPUT_TAG]}
    if isinstance(test, str):
        return {test: {"config": config}}
    if isinstance(test, dict) and len(test) == 1:
        ((name, args),) = test.items()
        merged = dict(args) if isinstance(args, dict) else {"value": args}
        merged["config"] = config
        return {name: merged}
    return test


_REL_SOURCE_RE = re.compile(r'source\(\s*"[^"]*"\s*,\s*"([^"]+)"\s*\)')


def _rewrite_relationships_to_ref(tests: list) -> list:
    """Rewrite the helper's `to: source(...)` to `to: ref('<table>')`.

    Sync targets the user's dbt models, so `ref()` is correct. The helper is
    shared with `export dbt`, which legitimately wants `source()`.
    """
    out = []
    for t in tests:
        if isinstance(t, dict) and "relationships" in t and isinstance(t["relationships"], dict):
            rel = dict(t["relationships"])
            to_value = rel.get("to") or ""
            m = _REL_SOURCE_RE.match(to_value)
            if m:
                rel["to"] = f"ref('{m.group(1)}')"
            out.append({"relationships": rel})
        else:
            out.append(t)
    return out


def _slugify(value: str) -> str:
    return re.sub(r"[^a-z0-9_]", "_", value.lower()).strip("_") or "quality"


def _quality_label(quality: DataQuality, fallback_idx: int) -> str:
    if quality.name:
        return quality.name
    if quality.description:
        return quality.description[:40] + "..."
    return f"q{fallback_idx}"


def _row_count_test(quality: DataQuality, run: Run, schema_name: Optional[str]) -> Optional[dict]:
    """Map table-level rowCount quality to a YAML dbt_expectations test."""
    if quality.mustBe is not None:
        return {"dbt_expectations.expect_table_row_count_to_equal": {"value": quality.mustBe}}

    # warn if we cannot do a precise conversion
    strict_lower = quality.mustBeGreaterThan is not None
    inclusive_lower = not strict_lower and (quality.mustBeGreaterOrEqualTo is not None or bool(quality.mustBeBetween))
    strict_higher = quality.mustBeLessThan is not None
    inclusive_higher = not strict_higher and (quality.mustBeLessOrEqualTo is not None or bool(quality.mustBeBetween))
    if (strict_lower and inclusive_higher) or (strict_higher and inclusive_lower):
        run.log_warn(
            f"Row-count quality on `{schema_name}` mixes strict and inclusive bounds, which is not natively supported by dbt_expectations. "
            "The `strictly` flag will be applied to both sides."
        )

    args: dict = {}
    if quality.mustBeBetween:
        args["min_value"] = quality.mustBeBetween[0]
        args["max_value"] = quality.mustBeBetween[1]
    if quality.mustBeGreaterThan is not None:
        args["min_value"] = quality.mustBeGreaterThan
        args["strictly"] = True
    elif quality.mustBeGreaterOrEqualTo is not None:
        args["min_value"] = quality.mustBeGreaterOrEqualTo
    if quality.mustBeLessThan is not None:
        args["max_value"] = quality.mustBeLessThan
        args["strictly"] = True
    elif quality.mustBeLessOrEqualTo is not None:
        args["max_value"] = quality.mustBeLessOrEqualTo
    if not args:
        return None
    return {"dbt_expectations.expect_table_row_count_to_be_between": args}


# ---------------------------------------------------------------------------
# Singular SQL test generation
# ---------------------------------------------------------------------------


@dataclass
class SingularTest:
    filename: str
    sql: str
    description: Optional[str]


def _singular_test_filename(contract_id: str, model: str, label: str) -> str:
    return f"{_slugify(contract_id)}__{_slugify(model)}__{_slugify(label)}"


# ---------------------------------------------------------------------------
# Schema → outputs
# ---------------------------------------------------------------------------


def _singular_tests_for_qualities(
    qualities: Optional[list],
    contract_id: str,
    model: str,
    *,
    label_prefix: str = "",
) -> List[SingularTest]:
    """Generate singular tests for ODCS quality entries that have an associated `query`."""
    out: List[SingularTest] = []
    for idx, quality in enumerate(qualities or [], start=1):
        if not quality.query:
            continue
        severity = _normalize_severity(quality.severity)
        label = f"{label_prefix}{_quality_label(quality, idx)}" if label_prefix else _quality_label(quality, idx)
        filename = _singular_test_filename(contract_id, model, label)
        out.append(
            SingularTest(
                filename=f"{filename}.sql",
                sql=_build_singular_sql(quality.query, severity, contract_id, model),
                description=quality.description,
            )
        )
    return out


def _build_singular_sql(query: str, severity: str, contract_id: str, model: str) -> str:
    return (
        f"-- AUTO-GENERATED by `datacontract dbt sync`. Do not edit.\n"
        f"-- Source contract: {contract_id} (model: {model})\n"
        f"{{{{ config(severity='{severity}', tags=['{OUTPUT_TAG}']) }}}}\n"
        f"{query.rstrip()}\n"
    )


def _model_data_tests(schema_obj: SchemaObject, run: Run) -> list:
    """Model-level tests: composite PK + table-level rowCount quality."""
    out: list = []
    pk_cols = [p.name for p in (schema_obj.properties or []) if p.primaryKey]
    if len(pk_cols) > 1:
        out.append(
            _attach_test_config(
                {"dbt_utils.unique_combination_of_columns": {"combination_of_columns": pk_cols}},
                severity="warn",
            )
        )
    for q in schema_obj.quality or []:
        if q.query:
            continue  # singular SQL handles it
        if q.metric and q.metric.lower() == "rowcount":
            test = _row_count_test(q, run, schema_obj.name)
            if test is None:
                run.log_warn(f"Skipping unsupported row-count quality on `{schema_obj.name}`")
                continue
            out.append(_attach_test_config(test, severity=_normalize_severity(q.severity)))
        else:
            run.log_warn(f"Skipping unsupported quality on `{schema_obj.name}`: metric={q.metric!r}")
    return out


def _column_dict(prop: SchemaProperty, odcs: OpenDataContractStandard, single_pk_name: Optional[str], run: Run) -> dict:
    column: dict = {"name": prop.name}
    base = field_to_data_tests(
        prop,
        is_primary_key=bool(prop.primaryKey),
        is_single_pk=(prop.name == single_pk_name),
        supports_constraints=False,
        source_name=odcs.id or "_source",
    )
    base = _rewrite_relationships_to_ref(base)
    tests = [_attach_test_config(t, severity="warn") for t in base]

    for q in prop.quality or []:
        if q.metric and q.metric.lower() == "invalidvalues":
            continue
        if q.query:
            continue
        if q.mustBe is not None:
            tests.append(
                _attach_test_config({"accepted_values": {"values": [q.mustBe]}}, _normalize_severity(q.severity))
            )
            continue
        run.log_warn(f"Skipping unsupported quality on `{prop.name}`: metric={q.metric!r}")

    if tests:
        column["data_tests"] = tests
    return column


def generate_dbt_tests_for_schema(
    odcs: OpenDataContractStandard,
    schema_obj: SchemaObject,
    model_name: str,
    run: Run,
) -> Tuple[dict, List[SingularTest]]:
    """Build the YAML model dict + list of singular SQL tests for one schema."""
    pk_cols = [p.name for p in (schema_obj.properties or []) if p.primaryKey]
    single_pk_name = pk_cols[0] if len(pk_cols) == 1 else None

    model_dict: dict = {"name": model_name}
    if schema_obj.description:
        model_dict["description"] = schema_obj.description.strip().replace("\n", " ")

    model_tests = _model_data_tests(schema_obj, run)
    if model_tests:
        model_dict["data_tests"] = model_tests

    columns: list = []
    for prop in schema_obj.properties or []:
        columns.append(_column_dict(prop, odcs, single_pk_name, run))
    if columns:
        model_dict["columns"] = columns

    contract_id = odcs.id or "contract"
    singulars: List[SingularTest] = []
    for prop in schema_obj.properties or []:
        singulars.extend(
            _singular_tests_for_qualities(prop.quality, contract_id, model_name, label_prefix=f"{prop.name}__")
        )
    singulars.extend(_singular_tests_for_qualities(schema_obj.quality, contract_id, model_name))

    return model_dict, singulars


# ---------------------------------------------------------------------------
# File writing
# ---------------------------------------------------------------------------


def write_dbt_tests(
    project_dir: Path,
    contract_path: Path,
    odcs: OpenDataContractStandard,
    model_name: str,
    model_dict: dict,
    singular_tests: List[SingularTest],
) -> Tuple[Path, List[Path]]:
    contract_id = odcs.id or "contract"
    yaml_doc: dict = {"version": 2, "models": [model_dict]}
    singulars_with_description = [t for t in singular_tests if t.description]
    if singulars_with_description:
        yaml_doc["data_tests"] = [
            {
                "name": Path(singular_test.filename).stem,
                "description": singular_test.description.strip().replace("\n", " "),
            }
            for singular_test in singulars_with_description
        ]

    yaml_path = project_dir / GENERATED_MODELS_DIR / f"{_slugify(contract_id)}__{_slugify(model_name)}.yml"
    yaml_path.parent.mkdir(parents=True, exist_ok=True)
    header = (
        f"# AUTO-GENERATED by `datacontract dbt sync`. Do not edit.\n# Source contract: {contract_path.resolve()}\n"
    )
    if odcs.version:
        header += f"# Contract id/version: {contract_id}@{odcs.version}\n"
    else:
        header += f"# Contract id: {contract_id}\n"

    with yaml_path.open("w", encoding="utf-8") as f:
        f.write(header)
        yaml.safe_dump(yaml_doc, f, indent=2, sort_keys=False, allow_unicode=True)

    sql_paths: List[Path] = []
    for s in singular_tests:
        sql_path = project_dir / GENERATED_TESTS_DIR / s.filename
        sql_path.parent.mkdir(parents=True, exist_ok=True)
        with sql_path.open("w", encoding="utf-8") as f:
            f.write(s.sql)
        sql_paths.append(sql_path)

    return yaml_path, sql_paths


# ---------------------------------------------------------------------------
# Subprocess + result parsing
# ---------------------------------------------------------------------------


_ANSI_RE = re.compile(r"\x1b\[[0-9;]*[mGKHF]")


def _strip_ansi_characters(text: str) -> str:
    return _ANSI_RE.sub("", text)


def _format_collision_message(collisions: dict[str, list[Path]], project_dir: Path) -> str:
    entries: list[str] = []
    for name, files in collisions.items():
        for f in files:
            try:
                rel = f.relative_to(project_dir)
            except ValueError:
                rel = f
            entries.append(f"  - `{name}` in {rel}")

    lines = ["The contract describes models that are already defined in your dbt project:"]
    lines.extend(entries[:10])
    remaining = len(entries) - 10
    if remaining > 0:
        lines.append(f"  ... and {remaining} more.")
    lines.append("")
    lines.append("Remove these model entries to establish the contract as single source of truth.")
    return "\n".join(lines)


def detect_user_model_collisions(project_dir: Path, target_model_names: set[str]) -> dict[str, list[Path]]:
    """Find user-authored YAML files that already declare a model the contract is about to emit.

    Walks ``<project>/models/`` recursively, parses every ``*.yml`` / ``*.yaml`` (skipping
    our generated dir), and collects any ``models[].name`` entry that overlaps with the
    contract's resolved models. Returns a mapping ``model_name -> [files...]``.
    """
    hits: dict[str, list[Path]] = {}
    models_root = project_dir / "models"
    if not models_root.is_dir():
        return hits
    generated_dir = (project_dir / GENERATED_MODELS_DIR).resolve()

    for pattern in ("*.yml", "*.yaml"):
        for yml_path in models_root.rglob(pattern):
            if generated_dir in yml_path.resolve().parents:
                continue
            try:
                with yml_path.open("r", encoding="utf-8") as f:
                    doc = yaml.safe_load(f) or {}
            except (OSError, yaml.YAMLError):
                continue
            if not isinstance(doc, dict):
                continue
            for entry in doc.get("models") or []:
                if not isinstance(entry, dict):
                    continue
                name = entry.get("name")
                if isinstance(name, str) and name in target_model_names:
                    hits.setdefault(name, []).append(yml_path)
    return hits


def run_dbt_test(
    project_dir: Path,
    resolved_models: List[str],
    *,
    target: Optional[str],
    profiles_dir: Optional[Path],
) -> subprocess.CompletedProcess:
    selectors: List[str] = [f"tag:{OUTPUT_TAG}", *resolved_models]
    args = ["dbt", "test", "--select", *selectors, "--project-dir", str(project_dir)]
    if target:
        args.extend(["--target", target])
    if profiles_dir:
        # Resolve to absolute — we cwd into project_dir below, so a relative
        # `--profiles-dir` from the user's shell would otherwise miss.
        args.extend(["--profiles-dir", str(Path(profiles_dir).resolve())])

    # Drop any prior run_results.json so we don't mistake a stale file for fresh output
    # if dbt fails before regenerating it.
    run_results_path = project_dir / "target" / "run_results.json"
    if run_results_path.is_file():
        run_results_path.unlink()

    try:
        # cwd=project_dir lets dbt find a project-local profiles.yml the way users expect
        # when running `dbt test` from inside their project.
        result = subprocess.run(args, capture_output=True, text=True, check=False, cwd=str(project_dir))
    except OSError as e:
        raise DataContractException(
            type="dbt_sync",
            name="dbt test",
            reason=f"Failed to invoke dbt: {e}",
            engine="dbt-sync",
            original_exception=e,
        )

    output = _strip_ansi_characters((result.stderr or "") + (result.stdout or ""))
    if result.returncode != 0 and not run_results_path.is_file():
        raise DataContractException(
            type="dbt_sync",
            name="dbt test",
            reason=f"`dbt test` failed (exit code {result.returncode}):\n{output}",
            engine="dbt-sync",
        )
    return result


def _load_manifest(project_dir: Path) -> dict:
    manifest_path = project_dir / "target" / "manifest.json"
    if not manifest_path.is_file():
        return {}
    try:
        with manifest_path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _get_test_metadata(test_node: dict) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """Return (model, column, description) extracted from a manifest.json test node."""
    if not test_node:
        return None, None, None
    description = test_node.get("description") or None

    column = test_node.get("column_name")
    test_metadata = test_node.get("test_metadata") or {}
    kwargs = test_metadata.get("kwargs") or {}
    if not column:
        kw_col = kwargs.get("column_name")
        if isinstance(kw_col, str):
            column = kw_col

    model = None
    attached = test_node.get("attached_node")
    if isinstance(attached, str) and attached.startswith("model."):
        model = attached.split(".")[-1]
    if not model:
        for dep in (test_node.get("depends_on") or {}).get("nodes") or []:
            if isinstance(dep, str) and dep.startswith("model."):
                model = dep.split(".")[-1]
                break
    return model, column, description


def parse_run_results(project_dir: Path, odcs: OpenDataContractStandard) -> Run:
    run = Run.create_run()
    run.dataContractId = odcs.id
    run.dataContractVersion = odcs.version

    run_results_path = project_dir / "target" / "run_results.json"
    if not run_results_path.is_file():
        run.log_warn(f"`{run_results_path}` not found — no test results to record.")
        run.finish()
        return run

    try:
        with run_results_path.open("r", encoding="utf-8") as f:
            run_results = json.load(f)
    except (OSError, json.JSONDecodeError) as e:
        run.log_warn(f"Could not read `{run_results_path}` — {e}")
        run.finish()
        return run

    manifest = _load_manifest(project_dir)
    nodes = manifest.get("nodes") or {}

    status_map = {
        "pass": ResultEnum.passed,
        "fail": ResultEnum.failed,
        "warn": ResultEnum.warning,
        "error": ResultEnum.error,
        "skipped": ResultEnum.info,
    }
    for r in run_results.get("results") or []:
        unique_id = r.get("unique_id") or ""
        status = (r.get("status") or "").lower()
        result_enum = status_map.get(status, ResultEnum.unknown)
        failures = r.get("failures")
        message = r.get("message")
        node = nodes.get(unique_id) or {}
        model, column, description = _get_test_metadata(node)
        fallback_name = node.get("name")
        if not fallback_name:
            parts = unique_id.split(".")
            fallback_name = parts[-2] if len(parts) >= 3 else unique_id
        reason_parts = []
        if failures:
            reason_parts.append(f"failures={failures}")
        if message:
            reason_parts.append(message)
        run.checks.append(
            Check(
                type="dbt_test",
                name=description or fallback_name,
                model=model,
                field=column,
                engine="dbt",
                result=result_enum,
                reason=" | ".join(reason_parts) or None,
            )
        )

    run.finish()
    return run


# ---------------------------------------------------------------------------
# Top-level orchestrator
# ---------------------------------------------------------------------------


@dataclass
class DbtTestGenerationResult:
    contract_path: Path
    project_dir: Path
    odcs: OpenDataContractStandard
    resolved_models: List[str]
    written_yaml: List[Path]
    written_sql: List[Path]
    generation_run: Run


def generate_dbt_tests(
    *,
    contract: Optional[str],
    project_dir: Optional[Path],
    schema_name: str = "all",
    model_resolution: ModelResolution = ModelResolution.name,
    console: Optional[Console] = None,
) -> DbtTestGenerationResult:
    """Resolve the contract, validate the dbt project, and emit YAML/SQL test files."""
    project_dir = (project_dir or Path.cwd()).resolve()
    _ensure_dbt_project(project_dir)

    if contract:
        contract_path = Path(contract).resolve()
        if not contract_path.is_file():
            raise DataContractException(
                type="dbt_sync",
                name="resolve contract",
                reason=f"Contract file not found: {contract_path}",
                engine="dbt-sync",
            )
    else:
        contract_path = find_contract(Path.cwd())

    odcs = resolve_data_contract(str(contract_path))
    logger.info(f"Resolved contract {odcs.id}@{odcs.version} from {contract_path}")
    if console is not None and not contract:
        console.print(f"Resolved contract {contract_path}")

    run = Run.create_run()
    run.dataContractId = odcs.id
    run.dataContractVersion = odcs.version
    run.timestampStart = datetime.now(timezone.utc)

    name_map = resolve_model_names(odcs, model_resolution, schema_name)
    if not name_map:
        run.log_info("No quality to sync (contract has no schemas with names).")
        return DbtTestGenerationResult(
            contract_path=contract_path,
            project_dir=project_dir,
            odcs=odcs,
            resolved_models=[],
            written_yaml=[],
            written_sql=[],
            generation_run=run,
        )

    target_names = {m for m in name_map.values() if m}
    collisions = detect_user_model_collisions(project_dir, target_names)
    if collisions:
        raise DataContractException(
            type="dbt_sync",
            name="duplicate model entry",
            reason=_format_collision_message(collisions, project_dir),
            engine="dbt-sync",
        )

    wipe_output_dirs(project_dir)

    yaml_test_paths: List[Path] = []
    sql_test_paths: List[Path] = []
    resolved_models: List[str] = []

    schemas_by_name = {s.name: s for s in (odcs.schema_ or []) if s.name}
    for schema_name_key, model_name in name_map.items():
        schema_obj = schemas_by_name[schema_name_key]
        if not model_name:
            run.log_error(f"Cannot resolve dbt model for schema `{schema_name_key}` — skipping.")
            continue

        model_dict, singulars = generate_dbt_tests_for_schema(odcs, schema_obj, model_name, run)
        yaml_path, sql_paths = write_dbt_tests(project_dir, contract_path, odcs, model_name, model_dict, singulars)
        yaml_test_paths.append(yaml_path)
        sql_test_paths.extend(sql_paths)
        resolved_models.append(model_name)

    return DbtTestGenerationResult(
        contract_path=contract_path,
        project_dir=project_dir,
        odcs=odcs,
        resolved_models=resolved_models,
        written_yaml=yaml_test_paths,
        written_sql=sql_test_paths,
        generation_run=run,
    )


def run_tests(
    generated: DbtTestGenerationResult,
    *,
    target: Optional[str] = None,
    profiles_dir: Optional[Path] = None,
) -> Run:
    """Run `dbt test` against the generated tests and return the parsed results."""
    if not generated.resolved_models:
        gen_run = generated.generation_run
        gen_run.log_warn("No models resolved — skipping test execution.")
        gen_run.finish()
        return gen_run

    completed = run_dbt_test(
        generated.project_dir,
        generated.resolved_models,
        target=target,
        profiles_dir=profiles_dir,
    )
    if completed.stdout:
        logger.info(completed.stdout)
    if completed.stderr:
        logger.info(completed.stderr)

    parsed_run = parse_run_results(generated.project_dir, generated.odcs)
    # Stitch generation-time logs onto the parsed Run so warn-counts include
    # any generation-time skips.
    parsed_run.logs = generated.generation_run.logs + parsed_run.logs
    parsed_run.timestampStart = generated.generation_run.timestampStart
    parsed_run.finish()
    return parsed_run
