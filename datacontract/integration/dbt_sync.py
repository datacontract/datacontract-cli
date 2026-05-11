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

from datacontract.integration.dbt_test_mapping import _get_logical_type_option, field_to_data_tests
from datacontract.lint.resolve import resolve_data_contract
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import Check, ResultEnum, Run

logger = logging.getLogger(__name__)

OUTPUT_TAG = "datacontract_cli"


def _load_dbt_project_config(project_dir: Path) -> dict:
    try:
        with (project_dir / "dbt_project.yml").open("r", encoding="utf-8") as f:
            cfg = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError):
        cfg = {}
    return cfg if isinstance(cfg, dict) else {}


def _read_dbt_project_paths(project_dir: Path) -> Tuple[List[Path], List[Path]]:
    """Return (model_paths, test_paths) absolute, honoring `dbt_project.yml`."""
    dbt_project_config = _load_dbt_project_config(project_dir)
    raw_models = (
        dbt_project_config.get("model-paths") if isinstance(dbt_project_config.get("model-paths"), list) else None
    )
    raw_tests = dbt_project_config.get("test-paths") if isinstance(dbt_project_config.get("test-paths"), list) else None
    model_paths = [(project_dir / p).resolve() for p in (raw_models or ["models"]) if isinstance(p, str)]
    test_paths = [(project_dir / p).resolve() for p in (raw_tests or ["tests"]) if isinstance(p, str)]

    # use dbt defaults as fallback
    if not model_paths:
        model_paths = [(project_dir / "models").resolve()]
    if not test_paths:
        test_paths = [(project_dir / "tests").resolve()]
    return model_paths, test_paths


def _resolved_generated_dirs(project_dir: Path) -> Tuple[Path, Path]:
    """Absolute (generated_models_dir, generated_tests_dir) for the configured project."""
    model_paths, test_paths = _read_dbt_project_paths(project_dir)
    return model_paths[0] / OUTPUT_TAG, test_paths[0] / OUTPUT_TAG


def _resolved_target_dir(project_dir: Path) -> Path:
    """Absolute path of dbt's artifact directory (default `target/`); honors `target-path`."""
    configured_target = _load_dbt_project_config(project_dir).get("target-path")
    return (project_dir / (configured_target if isinstance(configured_target, str) else "target")).resolve()


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


def check_dbt_on_path() -> str:
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
) -> dict[str, str]:
    """Map `schema.name` → dbt model name. Raise if any schema is unresolvable under the strategy."""
    mapping: dict[str, str] = {}
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
    missing_physical: List[str] = []
    for schema_obj in schemas:
        if not schema_obj.name:
            continue
        if strategy == ModelResolution.name:
            mapping[schema_obj.name] = schema_obj.name
        elif strategy == ModelResolution.physicalName:
            if schema_obj.physicalName:
                mapping[schema_obj.name] = schema_obj.physicalName
            else:
                missing_physical.append(schema_obj.name)
    if missing_physical:
        listing = ", ".join(f"`{n}`" for n in missing_physical)
        raise DataContractException(
            type="dbt_sync",
            name="resolve model",
            reason=(
                f"`--model-resolution physicalName` was requested but the following schema(s) "
                f"have no `physicalName` set: {listing}. Either set `physicalName` in the contract, "
                "or use `--model-resolution name`."
            ),
            engine="dbt-sync",
        )
    return mapping


# ---------------------------------------------------------------------------
# Output filesystem management
# ---------------------------------------------------------------------------


def wipe_output_dirs(project_dir: Path) -> None:
    for target in _resolved_generated_dirs(project_dir):
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


# ---------------------------------------------------------------------------
# Singular SQL test generation
# ---------------------------------------------------------------------------


@dataclass
class SingularTest:
    filename: str
    sql: str
    description: Optional[str]


# ---------------------------------------------------------------------------
# Schema → outputs
# ---------------------------------------------------------------------------


def _sql_literal(value: Any) -> str:
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, str):
        return "'" + value.replace("'", "''") + "'"
    return str(value)


def _bound_violation_predicate(quality: DataQuality) -> Optional[str]:
    """Build a SQL predicate over `metric_value` that is TRUE iff any bound on `quality` is violated.

    Bounds present on the quality are combined with `OR` (any violated bound fails the test).
    Returns None if the quality has no bound (the contract author forgot to set `mustBe*`).
    """
    parts: List[str] = []
    if quality.mustBe is not None:
        parts.append(f"metric_value <> {_sql_literal(quality.mustBe)}")
    if quality.mustNotBe is not None:
        parts.append(f"metric_value = {_sql_literal(quality.mustNotBe)}")
    if quality.mustBeGreaterThan is not None:
        parts.append(f"metric_value <= {_sql_literal(quality.mustBeGreaterThan)}")
    if quality.mustBeGreaterOrEqualTo is not None:
        parts.append(f"metric_value < {_sql_literal(quality.mustBeGreaterOrEqualTo)}")
    if quality.mustBeLessThan is not None:
        parts.append(f"metric_value >= {_sql_literal(quality.mustBeLessThan)}")
    if quality.mustBeLessOrEqualTo is not None:
        parts.append(f"metric_value > {_sql_literal(quality.mustBeLessOrEqualTo)}")
    if quality.mustBeBetween is not None and len(quality.mustBeBetween) == 2:
        lo, hi = quality.mustBeBetween
        parts.append(f"metric_value < {_sql_literal(lo)}")
        parts.append(f"metric_value > {_sql_literal(hi)}")
    if quality.mustNotBeBetween is not None and len(quality.mustNotBeBetween) == 2:
        lo, hi = quality.mustNotBeBetween
        parts.append(f"(metric_value >= {_sql_literal(lo)} AND metric_value <= {_sql_literal(hi)})")
    if not parts:
        return None
    return "metric_value IS NULL OR " + " OR ".join(parts)


def _singular_tests_for_qualities(
    qualities: Optional[list],
    contract_id: str,
    model: str,
    run: Run,
    *,
    label_prefix: str = "",
) -> List[SingularTest]:
    """Generate singular tests for ODCS quality entries that have an associated `query` and bound."""
    out: List[SingularTest] = []
    for idx, quality in enumerate(qualities or [], start=1):
        if not quality.query:
            continue
        predicate = _bound_violation_predicate(quality)
        test_label = f"{label_prefix}{_quality_label(quality, idx)}" if label_prefix else _quality_label(quality, idx)
        if predicate is None:
            run.log_warn(
                f"Skipping singular SQL test `{test_label}` on `{model}`: quality has a `query` but no `mustBe*` bound."
            )
            continue
        severity = _normalize_severity(quality.severity)
        filename = f"{_slugify(contract_id)}__{_slugify(model)}__{_slugify(test_label)}"
        out.append(
            SingularTest(
                filename=f"{filename}.sql",
                sql=_build_singular_sql(quality.query, predicate, severity, contract_id, model),
                description=quality.description,
            )
        )
    return out


def _build_singular_sql(query: str, violation_predicate: str, severity: str, contract_id: str, model: str) -> str:
    # The ODCS query is expected to yield a single-column scalar metric. We alias that
    # column to `metric_value` via the CTE column list, then return rows only when the
    # bound is violated — dbt singular-test semantics (rows returned = test failed).
    return (
        f"-- AUTO-GENERATED by `datacontract dbt sync`. Do not edit.\n"
        f"-- Source contract: {contract_id} (model: {model})\n"
        f"{{{{ config(severity='{severity}', tags=['{OUTPUT_TAG}']) }}}}\n"
        f"WITH _dc_metric (metric_value) AS (\n"
        f"{query.rstrip()}\n"
        f")\n"
        f"SELECT metric_value FROM _dc_metric WHERE {violation_predicate}\n"
    )


def _row_count_singular_test(quality: DataQuality, contract_id: str, model: str) -> Optional[SingularTest]:
    """Singular SQL test for a table-level `rowCount` quality without an explicit `query`."""
    predicate = _bound_violation_predicate(quality)
    if predicate is None:
        return None
    severity = _normalize_severity(quality.severity)
    label = _quality_label(quality, 1)
    filename = f"{_slugify(contract_id)}__{_slugify(model)}__{_slugify(label)}.sql"
    sql = _build_singular_sql(
        f"SELECT COUNT(*) FROM {{{{ ref('{model}') }}}}",
        predicate,
        severity,
        contract_id,
        model,
    )
    return SingularTest(filename=filename, sql=sql, description=quality.description)


# ---------------------------------------------------------------------------
# Field-level bound singular SQL (length / regex / numeric range)
#
# We emit these as singular SQL so generated dbt projects don't need
# `dbt_expectations` in their `packages.yml`. Each test returns rows that
# violate the bound (dbt singular-test convention).
# ---------------------------------------------------------------------------


def _quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def _regex_violation_jinja(column: str, pattern: str) -> str:
    """Adapter-portable 'col does NOT match pattern' fragment.

    Dispatches on `target.type` because regex syntax is one of the least-portable
    parts of SQL: BigQuery uses `REGEXP_CONTAINS`, Snowflake/Oracle use
    `REGEXP_LIKE`, and Postgres / DuckDB / Redshift use the POSIX `~` operator.
    """
    escaped = pattern.replace("'", "''")
    return (
        "{% if target.type == 'bigquery' %}"
        f"NOT REGEXP_CONTAINS(CAST({column} AS STRING), '{escaped}')"
        "{% elif target.type == 'snowflake' %}"
        f"NOT REGEXP_LIKE(CAST({column} AS VARCHAR), '{escaped}')"
        "{% else %}"
        f"CAST({column} AS VARCHAR) !~ '{escaped}'"
        "{% endif %}"
    )


def _field_bound_predicates(prop: SchemaProperty) -> List[Tuple[str, str]]:
    """For `prop`, yield `(label_suffix, sql_predicate)` for each declared bound.

    `sql_predicate` is TRUE only for rows that violate the bound. Length checks
    fire when the value is non-null but its length is out of range; numeric
    range checks fire when the value is non-null and outside the range; regex
    fires when the value does not match. NULLs are filtered upstream with
    `WHERE col IS NOT NULL`.
    """
    column = _quote_identifier(prop.name)
    pairs: List[Tuple[str, str]] = []

    min_length = _get_logical_type_option(prop, "minLength")
    max_length = _get_logical_type_option(prop, "maxLength")
    if min_length is not None or max_length is not None:
        parts: List[str] = []
        if min_length is not None:
            parts.append(f"LENGTH({column}) < {min_length}")
        if max_length is not None:
            parts.append(f"LENGTH({column}) > {max_length}")
        pairs.append(("length", " OR ".join(parts)))

    pattern = _get_logical_type_option(prop, "pattern")
    if pattern is not None:
        pairs.append(("pattern", _regex_violation_jinja(column, pattern)))

    minimum = _get_logical_type_option(prop, "minimum")
    maximum = _get_logical_type_option(prop, "maximum")
    exclusive_minimum = _get_logical_type_option(prop, "exclusiveMinimum")
    exclusive_maximum = _get_logical_type_option(prop, "exclusiveMaximum")
    range_parts: List[str] = []
    if minimum is not None:
        range_parts.append(f"{column} < {_sql_literal(minimum)}")
    if maximum is not None:
        range_parts.append(f"{column} > {_sql_literal(maximum)}")
    if exclusive_minimum is not None:
        range_parts.append(f"{column} <= {_sql_literal(exclusive_minimum)}")
    if exclusive_maximum is not None:
        range_parts.append(f"{column} >= {_sql_literal(exclusive_maximum)}")
    if range_parts:
        pairs.append(("range", " OR ".join(range_parts)))

    return pairs


def _build_row_violation_sql(
    *,
    model: str,
    column_null_filter: str,
    violation_predicate: str,
    severity: str,
    contract_id: str,
    label: str,
) -> str:
    return (
        f"-- AUTO-GENERATED by `datacontract dbt sync`. Do not edit.\n"
        f"-- Source contract: {contract_id} (model: {model}, check: {label})\n"
        f"{{{{ config(severity='{severity}', tags=['{OUTPUT_TAG}']) }}}}\n"
        f"SELECT *\n"
        f"FROM {{{{ ref('{model}') }}}}\n"
        f"WHERE {column_null_filter} IS NOT NULL\n"
        f"  AND ({violation_predicate})\n"
    )


def _field_singular_tests(prop: SchemaProperty, contract_id: str, model: str) -> List[SingularTest]:
    """Singular SQL tests for `logicalTypeOptions` bounds on `prop` (length / regex / range)."""
    column = _quote_identifier(prop.name)
    out: List[SingularTest] = []
    for suffix, predicate in _field_bound_predicates(prop):
        label = f"{prop.name}__{suffix}"
        filename = f"{_slugify(contract_id)}__{_slugify(model)}__{_slugify(label)}.sql"
        sql = _build_row_violation_sql(
            model=model,
            column_null_filter=column,
            violation_predicate=predicate,
            severity="warn",
            contract_id=contract_id,
            label=label,
        )
        out.append(SingularTest(filename=filename, sql=sql, description=None))
    return out


def _model_data_tests(
    schema_obj: SchemaObject, run: Run, contract_id: str, model: str
) -> Tuple[list, List[SingularTest]]:
    """Model-level outputs: composite-PK YAML test + table-level rowCount as singular SQL.

    Returns ``(yaml_tests, singular_tests)``. Row-count qualities without a
    ``query`` field are emitted as singular SQL (rather than dbt_expectations
    YAML) so generated projects stay free of external macro dependencies.
    """
    yaml_tests: list = []
    singular_tests: List[SingularTest] = []
    pk_cols = [p.name for p in (schema_obj.properties or []) if p.primaryKey]
    if len(pk_cols) > 1:
        yaml_tests.append(
            _attach_test_config(
                {"dbt_utils.unique_combination_of_columns": {"combination_of_columns": pk_cols}},
                severity="warn",
            )
        )
    for q in schema_obj.quality or []:
        if q.query:
            continue  # singular SQL handles it via _singular_tests_for_qualities
        if q.metric and q.metric.lower() == "rowcount":
            test = _row_count_singular_test(q, contract_id, model)
            if test is None:
                run.log_warn(f"Skipping unsupported row-count quality on `{schema_obj.name}`")
                continue
            singular_tests.append(test)
        else:
            run.log_warn(f"Skipping unsupported quality on `{schema_obj.name}`: metric={q.metric!r}")
    return yaml_tests, singular_tests


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

    contract_id = odcs.id or "contract"
    model_yaml_tests, model_singulars = _model_data_tests(schema_obj, run, contract_id, model_name)
    if model_yaml_tests:
        model_dict["data_tests"] = model_yaml_tests

    columns: list = []
    for prop in schema_obj.properties or []:
        columns.append(_column_dict(prop, odcs, single_pk_name, run))
    if columns:
        model_dict["columns"] = columns

    singulars: List[SingularTest] = list(model_singulars)
    # Field-level bounds (length / regex / numeric range) → singular SQL
    for prop in schema_obj.properties or []:
        singulars.extend(_field_singular_tests(prop, contract_id, model_name))
    # Existing `quality.query` singular tests (one CTE per scalar metric)
    for prop in schema_obj.properties or []:
        singulars.extend(
            _singular_tests_for_qualities(prop.quality, contract_id, model_name, run, label_prefix=f"{prop.name}__")
        )
    singulars.extend(_singular_tests_for_qualities(schema_obj.quality, contract_id, model_name, run))
    _disambiguate_singular_filenames(singulars)

    return model_dict, singulars


def _disambiguate_singular_filenames(singular_tests: List[SingularTest]) -> None:
    """In-place rename so two qualities whose labels slugify identically don't overwrite each other."""
    used: set[str] = set()
    for test in singular_tests:
        if test.filename not in used:
            used.add(test.filename)
            continue
        stem = Path(test.filename).stem
        n = 2
        while f"{stem}__{n}.sql" in used:
            n += 1
        new_filename = f"{stem}__{n}.sql"
        test.filename = new_filename
        used.add(new_filename)


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

    generated_models_dir, generated_tests_dir = _resolved_generated_dirs(project_dir)
    yaml_path = generated_models_dir / f"{_slugify(contract_id)}__{_slugify(model_name)}.yml"
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
        sql_path = generated_tests_dir / s.filename
        sql_path.parent.mkdir(parents=True, exist_ok=True)
        with sql_path.open("w", encoding="utf-8") as f:
            f.write(s.sql)
        sql_paths.append(sql_path)

    return yaml_path, sql_paths


# ---------------------------------------------------------------------------
# Subprocess + result parsing
# ---------------------------------------------------------------------------


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

    Walks every directory listed under ``model-paths`` in ``dbt_project.yml`` recursively,
    parses every ``*.yml`` / ``*.yaml`` (skipping our generated dir), and collects any
    ``models[].name`` entry that overlaps with the contract's resolved models.
    Returns a mapping ``model_name -> [files...]``.
    """
    hits: dict[str, list[Path]] = {}
    model_paths, _ = _read_dbt_project_paths(project_dir)
    generated_models_dir, _ = _resolved_generated_dirs(project_dir)

    for models_root in model_paths:
        if not models_root.is_dir():
            continue
        for pattern in ("*.yml", "*.yaml"):
            for yml_path in models_root.rglob(pattern):
                if generated_models_dir in yml_path.resolve().parents:
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
    *,
    target: Optional[str],
    profiles_dir: Optional[Path],
) -> subprocess.CompletedProcess:
    args = ["dbt", "test", "--select", f"tag:{OUTPUT_TAG}", "--project-dir", str(project_dir)]
    if target:
        args.extend(["--target", target])
    if profiles_dir:
        # Resolve to absolute — we cwd into project_dir below, so a relative
        # `--profiles-dir` from the user's shell would otherwise miss.
        args.extend(["--profiles-dir", str(Path(profiles_dir).resolve())])

    # Drop any prior run_results.json so we don't mistake a stale file for fresh output
    # if dbt fails before regenerating it.
    run_results_path = _resolved_target_dir(project_dir) / "run_results.json"
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

    ansi_control_chars = re.compile(r"\x1b\[[0-9;]*[mGKHF]")
    output = ansi_control_chars.sub("", (result.stderr or "") + (result.stdout or ""))
    if result.returncode != 0 and not run_results_path.is_file():
        raise DataContractException(
            type="dbt_sync",
            name="dbt test",
            reason=f"`dbt test` failed (exit code {result.returncode}):\n{output}",
            engine="dbt-sync",
        )
    return result


def _load_manifest(project_dir: Path) -> dict:
    manifest_path = _resolved_target_dir(project_dir) / "manifest.json"
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

    run_results_path = _resolved_target_dir(project_dir) / "run_results.json"
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

    target_names = set(name_map.values())
    collisions = detect_user_model_collisions(project_dir, target_names)
    if collisions:
        raise DataContractException(
            type="dbt_sync",
            name="duplicate model entry",
            reason=_format_collision_message(collisions, project_dir),
            engine="dbt-sync",
        )

    # Wipe before the empty-name_map short-circuit so stale `tag:datacontract_cli`
    # artifacts from a prior run don't survive into the next `dbt test`.
    wipe_output_dirs(project_dir)

    if not name_map:
        run.log_info("No quality to sync (contract has no schemas with names).")

    yaml_test_paths: List[Path] = []
    sql_test_paths: List[Path] = []
    resolved_models: List[str] = []

    schemas_by_name = {s.name: s for s in (odcs.schema_ or []) if s.name}
    for schema_name_key, model_name in name_map.items():
        schema_obj = schemas_by_name[schema_name_key]
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
