"""Execute the engine-neutral check IR against a data source using ibis.

This replaces ``check_soda_execute``. For each model it batches the count-style
metrics (row_count, missing_count, invalid_count) into a single aggregation
query and runs dedicated queries for duplicates, schema/type, freshness/retention
and user SQL. Thresholds are evaluated in Python and the outcome written back
onto the pre-registered ``Check`` objects in the run.
"""

from __future__ import annotations

import logging
import uuid
from collections import defaultdict
from typing import List, Optional

from open_data_contract_standard.model import OpenDataContractStandard, Server

from datacontract.engines.checks.check_spec import CheckSpec, MetricType
from datacontract.engines.checks.physical_type_match import physical_type_matches
from datacontract.engines.checks.type_normalize import schema_property_matches, schema_property_mismatch_reason
from datacontract.engines.ibis.connections.connect import connect_ibis
from datacontract.engines.ibis.dtype_category import ibis_dtype_to_schema_property
from datacontract.engines.ibis.native_type import fetch_native_types, sqlglot_dialect
from datacontract.engines.ibis.snowflake_structured_types import fetch_structured_types
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import Check, ResultEnum, Run
from datacontract.model.server import get_server_type

logger = logging.getLogger(__name__)


class _ColumnNotFound(Exception):
    pass


# ---------------------------------------------------------------------------
# Check stubs (created up-front so run.checks ordering & filtering is stable)
# ---------------------------------------------------------------------------
def build_check_stubs(specs: List[CheckSpec]) -> List[Check]:
    stubs: List[Check] = []
    for spec in specs:
        stubs.append(
            Check(
                id=str(uuid.uuid4()),
                key=spec.key,
                category=spec.category,
                type=spec.type,
                name=spec.name,
                model=spec.model,
                field=spec.field,
                engine="ibis",
                implementation=_describe(spec),
            )
        )
    return stubs


def _describe(spec: CheckSpec) -> str:
    if spec.metric == MetricType.CUSTOM_SQL:
        return spec.query or ""
    if spec.metric == MetricType.FIELD_TYPE:
        return f"type({spec.field}) == {spec.expected_type_label}"
    if spec.metric == MetricType.FIELD_PHYSICAL_TYPE:
        return f"physical_type({spec.field}) == {spec.expected_physical_type}"
    if spec.metric == MetricType.FIELD_PRESENT:
        return f"present({spec.field})"
    if spec.threshold is not None:
        target = spec.field or spec.model
        return f"{spec.metric.value}({target}) {spec.threshold.describe()}"
    return spec.metric.value


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
def execute_ibis_checks(
    run: Run,
    data_contract: OpenDataContractStandard,
    server: Server,
    specs: List[CheckSpec],
    spark=None,
    duckdb_connection=None,
    schema_name: str = "all",
    include_failed_samples: bool = False,
):
    if data_contract is None:
        run.log_warn("Cannot run engine ibis, as data contract is invalid")
        return

    # Checks the new engine cannot run (e.g. raw SodaCL) get their preset result.
    executable: List[CheckSpec] = []
    for spec in specs:
        if spec.metric == MetricType.UNSUPPORTED:
            _set_result(run, spec.key, ResultEnum(spec.preset_result or "warning"), spec.preset_reason)
        else:
            executable.append(spec)

    if not executable:
        return

    run.log_info("Running engine ibis")
    try:
        con = connect_ibis(run, data_contract, server, spark, duckdb_connection, schema_name)
    except DataContractException:
        raise
    except ImportError:
        server_type = get_server_type(server)
        reason = (
            f"The '{server_type}' backend is not installed. "
            f"Install it with: pip install 'datacontract-cli[{server_type}]'"
        )
        logger.exception("ibis backend import failed")
        run.log_error(reason)
        run.checks.append(
            Check(
                type="general",
                name="Data Contract Tests",
                result=ResultEnum.failed,
                reason=reason,
                engine="ibis",
            )
        )
        return
    except Exception as e:
        reason = _first_line(str(e)) or "Engine ibis could not connect to the data source."
        logger.exception("ibis connection failed")
        run.log_error(f"Engine ibis could not connect: {reason}")
        run.checks.append(
            Check(
                type="general",
                name="Data Contract Tests",
                result=ResultEnum.failed,
                reason=reason,
                engine="ibis",
            )
        )
        return

    if con is None:
        # Unsupported server type/format already logged a warning check.
        return

    by_model: dict[str, List[CheckSpec]] = defaultdict(list)
    for spec in executable:
        by_model[spec.model].append(spec)

    try:
        for model, model_specs in by_model.items():
            _run_model(run, con, model, model_specs, data_contract, server, include_failed_samples)
    finally:
        _maybe_disconnect(con, spark, duckdb_connection)


def _maybe_disconnect(con, spark, duckdb_connection):
    """Dispose the connection, but only if the engine created/owns it.

    Never tear down a caller-provided resource: a Spark session (the pyspark
    backend wraps a shared, externally-owned session) or an externally-supplied
    DuckDB connection. Doing so would break the caller / subsequent runs.
    """
    backend = getattr(con, "name", "")
    if backend == "pyspark":
        return
    if backend == "duckdb" and duckdb_connection is not None:
        return
    if spark is not None:
        return
    try:
        con.disconnect()
    except Exception:
        pass


def _run_model(
    run: Run,
    con,
    model: str,
    specs: List[CheckSpec],
    data_contract: Optional[OpenDataContractStandard] = None,
    server: Optional[Server] = None,
    include_failed_samples: bool = False,
):
    try:
        t = _resolve_table(con, model, _table_database(con, server))
    except Exception as e:
        logger.warning("Could not read model '%s': %s", model, e)
        _fail_all(run, specs, ResultEnum.failed, f"Could not read model '{model}': {e}")
        return

    columns = {c.lower(): c for c in t.columns}
    schema = t.schema()

    # Physical type checks read the real declared native types from the catalog;
    # fetch once per model, and only when such a check exists.
    native_types = None
    if any(spec.metric == MetricType.FIELD_PHYSICAL_TYPE for spec in specs):
        native_types = fetch_native_types(con, server, model)

    # Snowflake collapses structured OBJECT/ARRAY nesting in the ibis dtype; read
    # the real nested types from SHOW COLUMNS so field_type checks can recurse.
    structured_types = None
    if get_server_type(server) == "snowflake" and any(spec.metric == MetricType.FIELD_TYPE for spec in specs):
        structured_types = fetch_structured_types(con, server, t.get_name())

    agg_exprs = []  # list[(spec, named_expr)]
    for spec in specs:
        try:
            named = None  # set for count-style metrics that get batched
            if spec.metric == MetricType.ROW_COUNT:
                named = t.count().name(spec.key)
            elif spec.metric == MetricType.MISSING_COUNT:
                col = _resolve_col(columns, spec.field)
                named = _count_true(_missing_expr(t, col, spec.missing_values)).name(spec.key)
            elif spec.metric == MetricType.INVALID_COUNT:
                col = _resolve_col(columns, spec.field)
                expr = _invalid_expr(t, col, schema[col], spec)
                if expr is None:
                    # No validity constraints => nothing can be invalid.
                    _set_impl(run, spec.key, "invalid_count = 0 (no validity constraints configured)", None)
                    _evaluate(run, spec, 0)
                else:
                    named = _count_true(expr).name(spec.key)
            elif spec.metric == MetricType.DUPLICATE_COUNT:
                _run_duplicate(run, t, columns, spec)
            elif spec.metric == MetricType.FIELD_PRESENT:
                _run_present(run, con, model, columns, spec)
            elif spec.metric == MetricType.FIELD_TYPE:
                _run_type(run, schema, columns, spec, structured_types)
            elif spec.metric == MetricType.FIELD_PHYSICAL_TYPE:
                _run_physical_type(run, con, server, schema, columns, native_types, spec)
            elif spec.metric in (MetricType.FRESHNESS, MetricType.RETENTION):
                _run_freshness(run, t, columns, spec)
            elif spec.metric == MetricType.CUSTOM_SQL:
                _run_custom_sql(run, con, spec)

            if named is not None:
                # Record the representative per-check SQL (these are executed
                # together as one batched aggregation, see _run_aggregation).
                _record_sql(run, spec, t.aggregate([named]))
                agg_exprs.append((spec, named))
        except _ColumnNotFound as e:
            _set_result(run, spec.key, ResultEnum.failed, str(e))
        except Exception as e:
            logger.warning("Check '%s' errored: %s", spec.key, e)
            _set_result(run, spec.key, ResultEnum.failed, f"Error evaluating check: {e}")

    if agg_exprs:
        _run_aggregation(run, t, agg_exprs)

    if include_failed_samples:
        _collect_failed_samples(run, t, columns, schema, model, specs, data_contract, server)


def _run_aggregation(run: Run, t, agg_exprs):
    import pandas as pd

    # Add the total row count so "bad row" metrics can report a failed fraction.
    row_count_key = "__dc_row_count__"
    exprs = [expr for _, expr in agg_exprs]
    exprs.append(t.count().name(row_count_key))
    try:
        df = t.aggregate(exprs).execute()
    except Exception as e:
        logger.warning("Aggregation query failed: %s", e)
        for spec, _ in agg_exprs:
            _set_result(run, spec.key, ResultEnum.failed, f"Error evaluating check: {e}")
        return

    row = df.iloc[0]
    rc = row[row_count_key]
    total = 0 if (rc is None or pd.isna(rc)) else int(rc)
    for spec, _ in agg_exprs:
        val = row[spec.key]
        val = 0 if (val is None or pd.isna(val)) else int(val)
        _evaluate(run, spec, val, row_count=total)


# ---------------------------------------------------------------------------
# failed-row samples (opt-in via --include-failed-samples)
# ---------------------------------------------------------------------------
_FAILED_SAMPLE_LIMIT = 5

# ODCS property classifications whose values are omitted from samples.
_SENSITIVE_CLASSIFICATIONS = {
    "pii",
    "personal",
    "personal_data",
    "confidential",
    "restricted",
    "sensitive",
    "secret",
}

_SAMPLEABLE_METRICS = (MetricType.MISSING_COUNT, MetricType.INVALID_COUNT, MetricType.DUPLICATE_COUNT)


def _collect_failed_samples(run, t, columns, schema, model, specs, data_contract, server):
    """Second pass: for failed/warned bad-row checks, fetch a few offending rows.

    Reuses the same predicates the counts were built from. Columns are limited to
    the contract's identifier (unique / primary-key) fields plus the offending
    column, and sensitive columns (by ODCS classification) are dropped.
    """
    identifiers, sensitive = _sample_field_meta(data_contract, server, model)
    for spec in specs:
        if spec.metric not in _SAMPLEABLE_METRICS:
            continue
        check = next((c for c in run.checks if c.key == spec.key), None)
        if check is None or check.result not in (ResultEnum.failed, ResultEnum.warning):
            continue
        try:
            samples = _samples_for(t, columns, schema, spec, identifiers, sensitive)
        except Exception as e:  # pragma: no cover - sampling is best-effort
            logger.debug("Could not collect failed samples for '%s': %s", spec.key, e)
            continue
        if samples:
            check.failed_samples = samples


def _sample_field_meta(data_contract, server, model):
    """(identifier columns, sensitive columns) for a model, from the ODCS schema."""
    identifiers: List[str] = []
    sensitive: set = set()
    if data_contract is None:
        return identifiers, sensitive
    from datacontract.engines.checks.create_checks import to_schema_name

    server_type = server.type if server and server.type else None
    for schema_obj in data_contract.schema_ or []:
        if to_schema_name(schema_obj, server_type) != model:
            continue
        for prop in schema_obj.properties or []:
            fname = prop.physicalName or prop.name
            if prop.unique or prop.primaryKey:
                identifiers.append(fname)
            classification = (getattr(prop, "classification", None) or "").strip().lower()
            if classification in _SENSITIVE_CLASSIFICATIONS:
                sensitive.add(fname.lower())
        break
    return identifiers, sensitive


def _select_columns(columns, sensitive, wanted):
    """Resolve wanted contract field names to actual table columns, in order,
    de-duplicated, dropping sensitive ones and any not present in the table."""
    selected: List[str] = []
    seen: set = set()
    for name in wanted:
        if name is None:
            continue
        key = name.lower()
        if key in sensitive or key in seen:
            continue
        actual = columns.get(key)
        if actual is None:
            continue
        seen.add(key)
        selected.append(actual)
    return selected


def _samples_for(t, columns, schema, spec: CheckSpec, identifiers, sensitive):
    if spec.metric == MetricType.DUPLICATE_COUNT:
        return _duplicate_samples(t, columns, sensitive, spec)

    col = _resolve_col(columns, spec.field)
    if spec.metric == MetricType.MISSING_COUNT:
        predicate = _missing_expr(t, col, spec.missing_values)
    else:  # INVALID_COUNT
        predicate = _invalid_expr(t, col, schema[col], spec)
        if predicate is None:
            return None

    select_cols = _select_columns(columns, sensitive, [*identifiers, spec.field])
    rows = t.filter(predicate)
    rows = rows.select(select_cols) if select_cols else rows
    return _df_to_records(rows.limit(_FAILED_SAMPLE_LIMIT).execute())


def _duplicate_samples(t, columns, sensitive, spec: CheckSpec):
    """The duplicated key values and how often each occurs."""
    key_fields = spec.columns or ([spec.field] if spec.field else [])
    key_cols = [_resolve_col(columns, c) for c in key_fields]
    grouped = t.group_by(key_cols).aggregate(duplicate_count=t.count())
    dups = grouped.filter(grouped["duplicate_count"] > 1)
    df = dups.limit(_FAILED_SAMPLE_LIMIT).execute()
    drop = [c for c in key_cols if c.lower() in sensitive]
    if drop and df is not None and not df.empty:
        df = df.drop(columns=drop)
    return _df_to_records(df)


def _df_to_records(df):
    if df is None or df.empty:
        return None
    return [{col: _json_safe(row[col]) for col in df.columns} for _, row in df.iterrows()]


def _json_safe(value):
    import pandas as pd

    try:
        if value is None or pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass  # arrays / structs are not NA-checkable; fall through to coercion
    v = _py(value)
    if v is None or isinstance(v, (str, int, float, bool)):
        return v
    return str(v)


# ---------------------------------------------------------------------------
# expression builders
# ---------------------------------------------------------------------------
def _count_true(bool_expr):
    """Count rows where a boolean expression is true, portably across dialects.

    Uses ``CASE WHEN cond THEN 1 ELSE 0 END`` summed, rather than ``SUM(bool)``:
    engines without a native boolean type (e.g. Oracle) reject summing a bare
    predicate.
    """
    return bool_expr.ifelse(1, 0).sum()


def _missing_expr(t, col, missing_values):
    cond = t[col].isnull()
    if missing_values:
        non_null = [v for v in missing_values if v is not None]
        if non_null:
            cond = cond | t[col].isin(non_null)
    return cond


def _as_string(column, dtype):
    """Return the column as a string expression, avoiding a redundant CAST.

    Some engines (e.g. Oracle) reject ``CAST(x AS VARCHAR2)`` without a length,
    so never cast a column that is already a string.
    """
    try:
        if dtype is not None and dtype.is_string():
            return column
    except AttributeError:
        pass
    return column.cast("string")


def _backend_name(t) -> str:
    """Backend name (e.g. ``mssql``, ``duckdb``) behind a bound table, or ``""``."""
    try:
        return getattr(t.get_backend(), "name", "") or ""
    except Exception:
        return ""


# Regex metacharacters with no T-SQL LIKE/PATINDEX equivalent. Inside a bracket
# class (``[...]``) these are literal and allowed; encountered outside one they
# signal a real regex we cannot translate to a LIKE pattern.
_MSSQL_UNSUPPORTED_REGEX_CHARS = set(".^$*+?(){}|\\")


def _mssql_like_pattern(pattern: str) -> str:
    """Validate that a contract ``pattern`` is expressible as a T-SQL LIKE pattern.

    SQL Server has no native regex operator, so the mssql backend cannot compile
    ``re_search`` ("Compilation rule for RegexSearch operation is not defined").
    PATINDEX instead matches LIKE wildcards (``%``, ``_``, ``[...]`` classes).
    Patterns built from literals and ``[...]`` classes (the common case, e.g.
    ``[0-9][0-9][0-9][0-9][0-9]``) map directly. Patterns using real regex syntax
    (anchors, quantifiers, groups, ``.``) cannot be expressed and raise here,
    rather than silently matching the wrong rows.
    """
    in_class = False
    for ch in pattern:
        if in_class:
            if ch == "]":
                in_class = False
            continue
        if ch == "[":
            in_class = True
            continue
        if ch in _MSSQL_UNSUPPORTED_REGEX_CHARS:
            raise ValueError(
                f"SQL Server does not support general regular expressions for pattern checks. "
                f"The pattern {pattern!r} uses regex syntax ({ch!r}) that cannot be translated "
                f"to a T-SQL LIKE/PATINDEX pattern. Only LIKE-compatible patterns (literals, "
                f"'%', '_', and [...] character classes) are supported on SQL Server."
            )
    return pattern


def _mssql_pattern_search(column, pattern: str):
    """``PATINDEX(pattern, column) > 0`` for the mssql backend (unanchored match).

    Mirrors the former soda-core SQL Server behaviour, where ``valid regex`` was
    compiled to ``PATINDEX('<pattern>', expr) > 0``. The pattern is passed as a
    bound literal, so it is escaped rather than string-interpolated.
    """
    import ibis

    like = _mssql_like_pattern(pattern)

    @ibis.udf.scalar.builtin
    def patindex(pattern: str, expression: str) -> int:  # -> PATINDEX(pattern, expression)
        ...

    return patindex(like, column) > 0


def _regex_search_expr(t, column, pattern: str):
    """Unanchored regex/pattern match, portable across backends.

    Most ibis backends compile ``re_search`` to a native regex operator. SQL
    Server has none, so fall back to a PATINDEX-based LIKE match for the mssql
    backend.
    """
    if _backend_name(t) == "mssql":
        return _mssql_pattern_search(column, pattern)
    return column.re_search(pattern)


def _valid_expr(t, col, dtype, spec: CheckSpec):
    """Boolean: a non-missing value satisfies all configured validity constraints."""
    conds = []
    if spec.valid_values is not None:
        conds.append(t[col].isin(spec.valid_values))
    if spec.valid_regex is not None:
        conds.append(_regex_search_expr(t, _as_string(t[col], dtype), spec.valid_regex))
    if spec.valid_min is not None:
        conds.append(t[col] >= spec.valid_min)
    if spec.valid_max is not None:
        conds.append(t[col] <= spec.valid_max)
    if spec.valid_min_length is not None:
        conds.append(_as_string(t[col], dtype).length() >= spec.valid_min_length)
    if spec.valid_max_length is not None:
        conds.append(_as_string(t[col], dtype).length() <= spec.valid_max_length)
    if not conds:
        return None
    expr = conds[0]
    for c in conds[1:]:
        expr = expr & c
    return expr


def _invalid_expr(t, col, dtype, spec: CheckSpec):
    """Reproduce soda's invalid_count: NOT missing AND (NOT valid OR in invalid_values)."""
    missing = _missing_expr(t, col, spec.missing_values)
    valid = _valid_expr(t, col, dtype, spec)
    invalid_terms = []
    if valid is not None:
        invalid_terms.append(~valid)
    if spec.invalid_values:
        invalid_terms.append(t[col].isin(spec.invalid_values))
    if not invalid_terms:
        return None
    invalid_any = invalid_terms[0]
    for term in invalid_terms[1:]:
        invalid_any = invalid_any | term
    return (~missing) & invalid_any


def _constraint_info(spec: CheckSpec) -> dict:
    """The validity rule(s) an invalid_count check enforces, with their parameters.

    Explains *what* made rows invalid (e.g. a max length of 20, an allowed set of
    values). Derived from the check spec, so it costs no query. The check model
    splits each schema rule into its own single-rule check, so this is normally a
    single entry; several are still handled for forward-compatibility.
    """
    info: dict = {}
    if spec.valid_values is not None:
        info["valid_values"] = spec.valid_values
    if spec.invalid_values:
        info["invalid_values"] = spec.invalid_values
    if spec.valid_regex is not None:
        info["pattern"] = spec.valid_regex
    if spec.valid_min is not None:
        info["minimum"] = spec.valid_min
    if spec.valid_max is not None:
        info["maximum"] = spec.valid_max
    if spec.valid_min_length is not None:
        info["min_length"] = spec.valid_min_length
    if spec.valid_max_length is not None:
        info["max_length"] = spec.valid_max_length
    return info


# ---------------------------------------------------------------------------
# dedicated check runners
# ---------------------------------------------------------------------------
def _run_duplicate(run: Run, t, columns, spec: CheckSpec):
    cols = [_resolve_col(columns, c) for c in (spec.columns or [spec.field])]
    grouped = t.group_by(cols).aggregate(_dup_n=t.count())
    dup_groups = grouped.filter(grouped["_dup_n"] > 1)
    _record_sql(run, spec, dup_groups)
    dup_count = dup_groups.count().execute()
    dup_count = int(dup_count) if dup_count is not None else 0
    _evaluate(run, spec, dup_count)
    if len(cols) > 1:
        _update_diagnostics(run, spec.key, {"columns": cols})


def _run_present(run: Run, con, model: str, columns, spec: CheckSpec):
    target = f"{model}__raw__" if spec.uses_raw_view else model
    _set_impl(run, spec.key, f"column '{spec.field}' exists in {target}", "introspection")
    present = set(columns.keys())
    if spec.uses_raw_view:
        try:
            raw = con.table(f"{model}__raw__")
            present = {c.lower() for c in raw.columns}
        except Exception:
            pass
    ok = spec.field.lower() in present
    _set_diagnostics(run, spec.key, _diag(metric="field_present", field=spec.field, present=ok))
    _set_result(
        run,
        spec.key,
        ResultEnum.passed if ok else ResultEnum.failed,
        None if ok else f"Required column '{spec.field}' is missing",
    )


def _run_type(run: Run, schema, columns, spec: CheckSpec, structured_types=None):
    _set_impl(
        run,
        spec.key,
        f"type of '{spec.field}' is compatible with '{spec.expected_type_label}'",
        "introspection",
    )
    actual_col = columns.get(spec.field.lower())
    if actual_col is None:
        _set_diagnostics(run, spec.key, _diag(metric="field_type", field=spec.field, expected=spec.expected_type_label))
        _set_result(run, spec.key, ResultEnum.failed, f"Column '{spec.field}' is missing")
        return
    dtype = schema[actual_col]
    # Snowflake structured types come back collapsed from ibis; prefer the nested
    # tree recovered from SHOW COLUMNS when available.
    structured_prop = structured_types.get(spec.field.lower()) if structured_types else None
    actual_prop = structured_prop or ibis_dtype_to_schema_property(dtype)
    _set_diagnostics(
        run,
        spec.key,
        _diag(metric="field_type", field=spec.field, expected=spec.expected_type_label, actual=str(dtype)),
    )
    if schema_property_matches(spec.expected_schema_property, actual_prop):
        _set_result(run, spec.key, ResultEnum.passed, None)
    else:
        reason = schema_property_mismatch_reason(spec.expected_schema_property, actual_prop)
        _set_result(
            run,
            spec.key,
            ResultEnum.failed,
            reason or f"Expected type '{spec.expected_type_label}' but column is '{dtype}'",
        )


def _run_physical_type(run: Run, con, server, schema, columns, native_types, spec: CheckSpec):
    """Compare a column's real native type against the contract's physicalType.

    When the native type cannot be read for this backend, or the declared
    physicalType cannot be interpreted in the server's dialect, fall back to the
    coarse logicalType category check if the property declares one, and only warn
    (skip) when there is nothing left to compare against.
    """
    _set_impl(
        run,
        spec.key,
        f"physical type of '{spec.field}' is '{spec.expected_physical_type}'",
        "introspection",
    )
    actual_col = columns.get(spec.field.lower())
    if actual_col is None:
        _set_diagnostics(
            run, spec.key, _diag(metric="field_physical_type", field=spec.field, expected=spec.expected_physical_type)
        )
        _set_result(run, spec.key, ResultEnum.failed, f"Column '{spec.field}' is missing")
        return

    actual_native = native_types.get(spec.field.lower()) if native_types else None
    _set_diagnostics(
        run,
        spec.key,
        _diag(
            metric="field_physical_type",
            field=spec.field,
            expected=spec.expected_physical_type,
            actual=actual_native,
        ),
    )

    result, reason = (None, "")
    if actual_native is not None:
        result, reason = physical_type_matches(spec.expected_physical_type, actual_native, sqlglot_dialect(con))
    else:
        reason = f"Could not read the native type of '{spec.field}' from the {get_server_type(server)} catalog"

    if result is True:
        _set_result(run, spec.key, ResultEnum.passed, None)
        return
    if result is False:
        _set_result(run, spec.key, ResultEnum.failed, reason)
        return

    # result is None: the physical type could not be evaluated. Fall back to the
    # logicalType category check when the property declares one.
    fallback = spec.expected_schema_property
    if fallback is not None and fallback.logicalType is not None:
        actual_prop = ibis_dtype_to_schema_property(schema[actual_col])
        if schema_property_matches(fallback, actual_prop):
            _set_result(run, spec.key, ResultEnum.passed, None)
        else:
            mismatch = schema_property_mismatch_reason(fallback, actual_prop)
            _set_result(
                run,
                spec.key,
                ResultEnum.failed,
                mismatch or f"Expected type '{fallback.logicalType}' but column is '{schema[actual_col]}'",
            )
        return

    _set_result(run, spec.key, ResultEnum.warning, f"{reason}; skipping the physical type check")


def _run_freshness(run: Run, t, columns, spec: CheckSpec):
    import pandas as pd

    col = _resolve_col(columns, spec.field)
    reduction = t[col].min() if spec.metric == MetricType.RETENTION else t[col].max()
    _record_sql(run, spec, t.aggregate(value=reduction))
    raw = reduction.execute()
    if raw is None or pd.isna(raw):
        _set_diagnostics(
            run, spec.key, _diag(metric=spec.metric.value, field=spec.field, threshold_seconds=spec.seconds)
        )
        _set_result(run, spec.key, ResultEnum.failed, f"No timestamp value found in '{spec.field}'")
        return
    ts = pd.Timestamp(raw)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    now = pd.Timestamp.now(tz="UTC")
    delta_seconds = (now - ts).total_seconds()
    ok = delta_seconds < spec.seconds
    is_retention = spec.metric == MetricType.RETENTION
    label = "Retention" if is_retention else "Freshness"
    ts_key = "oldest_timestamp" if is_retention else "latest_timestamp"
    _set_diagnostics(
        run,
        spec.key,
        _diag(
            metric=spec.metric.value,
            field=spec.field,
            age_seconds=int(delta_seconds),
            threshold_seconds=spec.seconds,
            **{ts_key: ts.isoformat()},
        ),
    )
    _set_result(
        run,
        spec.key,
        ResultEnum.passed if ok else ResultEnum.failed,
        None if ok else f"{label} is {int(delta_seconds)}s, which exceeds the threshold of {spec.seconds}s",
    )


def _run_custom_sql(run: Run, con, spec: CheckSpec):
    _set_impl(run, spec.key, spec.query, "sql")
    value = _run_scalar(con, spec.query, spec.dialect)
    _evaluate(run, spec, value)


def _run_scalar(con, query: str, dialect: Optional[str]):
    try:
        expr = con.sql(query, dialect=dialect) if dialect else con.sql(query)
        df = expr.execute()
        if df.empty:
            return None
        return _py(df.iloc[0, 0])
    except Exception as primary_error:
        logger.debug("con.sql failed (%s); falling back to raw_sql", primary_error)
        cursor = con.raw_sql(query)
        try:
            if hasattr(cursor, "fetchone"):
                row = cursor.fetchone()
            else:
                # Some backends (e.g. BigQuery) return an iterable result set
                # (RowIterator) instead of a DBAPI cursor.
                row = next(iter(cursor), None)
        finally:
            # On DuckDB, raw_sql returns the shared connection itself; closing it
            # would tear down the connection and break every subsequent check.
            if cursor is not getattr(con, "con", None):
                try:
                    cursor.close()
                except Exception:
                    pass
        return _py(row[0]) if row else None


# ---------------------------------------------------------------------------
# result helpers
# ---------------------------------------------------------------------------
def _evaluate(run: Run, spec: CheckSpec, value, row_count: Optional[int] = None):
    is_bad_row = spec.metric in (MetricType.MISSING_COUNT, MetricType.INVALID_COUNT)
    # A percent threshold (ODCS quality.unit: percent) compares the failed
    # fraction (0-100) against the threshold value instead of the absolute
    # count. It needs the model row count, so it only applies to bad-row metrics.
    is_percent = bool(spec.threshold_is_percent) and is_bad_row
    percent = (round(value / row_count * 100, 6) if row_count else 0.0) if is_percent else None
    compare_value = percent if is_percent else value

    diag = _diag(
        metric=spec.metric.value,
        field=spec.field,
        value=value,
        unit="percent" if is_percent else None,
        severity=spec.severity,
        threshold=spec.threshold.describe() if spec.threshold is not None else None,
    )
    # For "bad row" metrics, show how many of the total rows failed.
    if row_count is not None and is_bad_row:
        diag["row_count"] = row_count
        diag["failed_fraction"] = round(value / row_count, 6) if row_count else 0.0
    if percent is not None:
        diag["percent"] = percent
    # For invalid_count, explain which validity rule was enforced.
    if spec.metric == MetricType.INVALID_COUNT:
        constraint = _constraint_info(spec)
        if constraint:
            diag["constraint"] = constraint
    elif spec.metric == MetricType.MISSING_COUNT and spec.missing_values:
        diag["missing_values"] = spec.missing_values
    _set_diagnostics(run, spec.key, diag)

    if spec.threshold is None:
        _set_result(run, spec.key, ResultEnum.passed, None)
        return
    ok = spec.threshold.passes(compare_value)
    target = spec.field or spec.model
    if ok:
        reason = None
    elif is_percent:
        reason = (
            f"Actual {spec.metric.value}({target}) was {percent}% ({value} of {row_count} rows), "
            f"expected {spec.threshold.describe()}%"
        )
    else:
        reason = f"Actual {spec.metric.value}({target}) was {value}, expected {spec.threshold.describe()}"
    _set_result(run, spec.key, ResultEnum.passed if ok else _fail_result(spec), reason)


# Severities (ODCS quality.severity) that downgrade a failing check to a warning
# instead of a hard failure. Anything else (including None) fails the run.
_WARNING_SEVERITIES = {"info", "warning", "warn", "low", "minor", "trivial"}


def _fail_result(spec: CheckSpec) -> ResultEnum:
    """The result to set when a check does not meet its threshold.

    Honors ODCS ``quality.severity``: a non-blocking severity makes the check a
    warning (which does not fail the run); the default is a hard failure.
    """
    severity = (spec.severity or "").strip().lower()
    if severity in _WARNING_SEVERITIES:
        return ResultEnum.warning
    return ResultEnum.failed


def _set_result(run: Run, key: str, result: ResultEnum, reason: Optional[str]):
    check = next((c for c in run.checks if c.key == key), None)
    if check is None:
        return
    check.result = result
    if reason is not None:
        check.reason = reason


def _diag(**kwargs) -> dict:
    """Build a diagnostics dict, dropping keys whose value is None.

    None entries are dropped because they would otherwise serialize as ``null``
    in the JSON output (``exclude_none`` only prunes top-level model fields, not
    nested dict contents).
    """
    return {k: v for k, v in kwargs.items() if v is not None}


def _set_diagnostics(run: Run, key: str, diagnostics: dict) -> None:
    """Attach structured diagnostics (the measured value, threshold, etc.) to a check."""
    check = next((c for c in run.checks if c.key == key), None)
    if check is not None:
        check.diagnostics = diagnostics


def _update_diagnostics(run: Run, key: str, extra: dict) -> None:
    """Merge extra entries into a check's existing diagnostics dict."""
    check = next((c for c in run.checks if c.key == key), None)
    if check is None:
        return
    if check.diagnostics is None:
        check.diagnostics = {}
    check.diagnostics.update(extra)


def _set_impl(run: Run, key: str, implementation: Optional[str], language: Optional[str]):
    """Record what a check actually runs: the compiled SQL (language='sql'),
    a schema-introspection note (language='introspection'), etc."""
    check = next((c for c in run.checks if c.key == key), None)
    if check is None:
        return
    check.implementation = implementation
    check.language = language


def _record_sql(run: Run, spec: CheckSpec, expr) -> None:
    """Compile a (bound) ibis expression to backend-dialect SQL and store it."""
    sql = _to_sql(expr)
    if sql:
        _set_impl(run, spec.key, sql, "sql")


def _to_sql(expr) -> Optional[str]:
    import ibis

    try:
        return str(ibis.to_sql(expr))
    except Exception as e:  # pragma: no cover - SQL rendering is best-effort
        logger.debug("Could not render SQL for check: %s", e)
        return None


def _fail_all(run: Run, specs: List[CheckSpec], result: ResultEnum, reason: str):
    for spec in specs:
        _set_result(run, spec.key, result, reason)


def _resolve_col(columns: dict, field: str) -> str:
    actual = columns.get(field.lower()) if field else None
    if actual is None:
        raise _ColumnNotFound(f"Column '{field}' not found")
    return actual


def _table_database(con, server: Optional[Server]) -> Optional[str]:
    """The schema to qualify the table with during introspection, or ``None``.

    Two backends need the contract's ``server.schema`` passed explicitly instead
    of relying on ibis's default:

    - **Oracle** logs in as one user but the tables may be owned by a different
      schema (``server.schema``). ibis defaults the owner to the login user, so
      an unqualified lookup raises ``TableNotFound``.
    - **Redshift** has no dedicated ibis backend and goes through the Postgres
      backend (``con.name == "postgres"``). When no schema is passed, ibis's
      Postgres introspection resolves the active schema with ``SELECT
      current_schema`` (no parentheses) — valid on PostgreSQL but rejected by
      Redshift with ``column "current_schema" does not exist``, since Redshift
      only supports the parenthesized ``current_schema()``. Passing the schema
      explicitly skips that query.

    Other backends pin the schema at connect time and need no qualifier.
    """
    if server is None or not server.schema_:
        return None
    if getattr(con, "name", None) == "oracle":
        return server.schema_
    # Redshift rides the Postgres backend, so detect it by the contract's server
    # type rather than con.name.
    if get_server_type(server) == "redshift":
        return server.schema_
    return None


def _resolve_table(con, model: str, database: Optional[str] = None):
    """Resolve a table by name, tolerating case differences across dialects."""
    if getattr(con, "name", None) == "pyspark":
        return _pyspark_table_unconvertible_as_unknown(con, model)
    kwargs = {"database": database} if database else {}
    try:
        return con.table(model, **kwargs)
    except Exception:
        try:
            available = con.list_tables(**kwargs)
        except Exception:
            raise
        match = next((name for name in available if name.lower() == model.lower()), None)
        if match is None:
            raise
        return con.table(match, **kwargs)


def _pyspark_table_unconvertible_as_unknown(con, name: str):
    """Reflect a pyspark table, typing any column whose Spark type Ibis cannot
    convert (e.g. Databricks `VariantType`) as `Unknown`.
    """
    import ibis
    import ibis.expr.datatypes as dt
    import ibis.expr.operations as ops
    from ibis.backends.pyspark.datatypes import PySparkType

    fields, unknown_columns = {}, []
    for field in con._session.table(name).schema.fields:
        try:
            fields[field.name] = PySparkType.to_ibis(field.dataType)
        except Exception:
            fields[field.name] = dt.unknown
            unknown_columns.append(f"{field.name} ({field.dataType.simpleString()})")
    if not unknown_columns:
        # Nothing unconvertible, resolve the table normally
        return con.table(name)
    logger.warning(
        f"Model '{name}': column(s) {', '.join(unknown_columns)} have a type ibis cannot represent. "
        f"Type checks for these columns will fail."
    )
    return ops.DatabaseTable(name, schema=ibis.schema(fields), source=con).to_expr()


def _py(value):
    if value is None:
        return None
    if hasattr(value, "item"):
        try:
            return value.item()
        except Exception:
            pass
    return value


def _first_line(text: str) -> str:
    for line in (text or "").strip().splitlines():
        line = line.strip()
        if line:
            return line
    return ""
