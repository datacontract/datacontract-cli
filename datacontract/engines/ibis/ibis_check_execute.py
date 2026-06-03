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
from datacontract.engines.checks.type_normalize import category_matches
from datacontract.engines.ibis.connections.connect import connect_ibis
from datacontract.engines.ibis.dtype_category import ibis_dtype_category
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import Check, ResultEnum, Run

logger = logging.getLogger(__name__)

_AGGREGATABLE = {MetricType.ROW_COUNT, MetricType.MISSING_COUNT, MetricType.INVALID_COUNT}


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
            _run_model(run, con, model, model_specs)
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


def _run_model(run: Run, con, model: str, specs: List[CheckSpec]):
    try:
        t = _resolve_table(con, model)
    except Exception as e:
        logger.warning("Could not read model '%s': %s", model, e)
        _fail_all(run, specs, ResultEnum.failed, f"Could not read model '{model}': {e}")
        return

    columns = {c.lower(): c for c in t.columns}
    schema = t.schema()

    agg_exprs = []  # list[(spec, named_expr)]
    for spec in specs:
        try:
            if spec.metric == MetricType.ROW_COUNT:
                agg_exprs.append((spec, t.count().name(spec.key)))
            elif spec.metric == MetricType.MISSING_COUNT:
                col = _resolve_col(columns, spec.field)
                agg_exprs.append((spec, _count_true(_missing_expr(t, col, spec.missing_values)).name(spec.key)))
            elif spec.metric == MetricType.INVALID_COUNT:
                col = _resolve_col(columns, spec.field)
                expr = _invalid_expr(t, col, schema[col], spec)
                if expr is None:
                    # No validity constraints => nothing can be invalid.
                    _evaluate(run, spec, 0)
                else:
                    agg_exprs.append((spec, _count_true(expr).name(spec.key)))
            elif spec.metric == MetricType.DUPLICATE_COUNT:
                _run_duplicate(run, t, columns, spec)
            elif spec.metric == MetricType.FIELD_PRESENT:
                _run_present(run, con, model, columns, spec)
            elif spec.metric == MetricType.FIELD_TYPE:
                _run_type(run, schema, columns, spec)
            elif spec.metric in (MetricType.FRESHNESS, MetricType.RETENTION):
                _run_freshness(run, t, columns, spec)
            elif spec.metric == MetricType.CUSTOM_SQL:
                _run_custom_sql(run, con, spec)
        except _ColumnNotFound as e:
            _set_result(run, spec.key, ResultEnum.failed, str(e))
        except Exception as e:
            logger.warning("Check '%s' errored: %s", spec.key, e)
            _set_result(run, spec.key, ResultEnum.failed, f"Error evaluating check: {e}")

    if agg_exprs:
        _run_aggregation(run, t, agg_exprs)


def _run_aggregation(run: Run, t, agg_exprs):
    import pandas as pd

    try:
        agg = t.aggregate([expr for _, expr in agg_exprs])
        df = agg.execute()
    except Exception as e:
        logger.warning("Aggregation query failed: %s", e)
        for spec, _ in agg_exprs:
            _set_result(run, spec.key, ResultEnum.failed, f"Error evaluating check: {e}")
        return

    row = df.iloc[0]
    for spec, _ in agg_exprs:
        val = row[spec.key]
        val = 0 if (val is None or pd.isna(val)) else int(val)
        _evaluate(run, spec, val)


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


def _valid_expr(t, col, dtype, spec: CheckSpec):
    """Boolean: a non-missing value satisfies all configured validity constraints."""
    conds = []
    if spec.valid_values is not None:
        conds.append(t[col].isin(spec.valid_values))
    if spec.valid_regex is not None:
        conds.append(_as_string(t[col], dtype).re_search(spec.valid_regex))
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


# ---------------------------------------------------------------------------
# dedicated check runners
# ---------------------------------------------------------------------------
def _run_duplicate(run: Run, t, columns, spec: CheckSpec):
    cols = [_resolve_col(columns, c) for c in (spec.columns or [spec.field])]
    grouped = t.group_by(cols).aggregate(_dup_n=t.count())
    dup_count = grouped.filter(grouped["_dup_n"] > 1).count().execute()
    dup_count = int(dup_count) if dup_count is not None else 0
    _evaluate(run, spec, dup_count)


def _run_present(run: Run, con, model: str, columns, spec: CheckSpec):
    present = set(columns.keys())
    if spec.uses_raw_view:
        try:
            raw = con.table(f"{model}__raw__")
            present = {c.lower() for c in raw.columns}
        except Exception:
            pass
    ok = spec.field.lower() in present
    _set_result(
        run,
        spec.key,
        ResultEnum.passed if ok else ResultEnum.failed,
        None if ok else f"Required column '{spec.field}' is missing",
    )


def _run_type(run: Run, schema, columns, spec: CheckSpec):
    actual_col = columns.get(spec.field.lower())
    if actual_col is None:
        _set_result(run, spec.key, ResultEnum.failed, f"Column '{spec.field}' is missing")
        return
    dtype = schema[actual_col]
    actual_category = ibis_dtype_category(dtype)
    if category_matches(spec.expected_category, actual_category):
        _set_result(run, spec.key, ResultEnum.passed, None)
    else:
        _set_result(
            run,
            spec.key,
            ResultEnum.failed,
            f"Expected type '{spec.expected_type_label}' ({spec.expected_category}) "
            f"but column is '{dtype}' ({actual_category})",
        )


def _run_freshness(run: Run, t, columns, spec: CheckSpec):
    import pandas as pd

    col = _resolve_col(columns, spec.field)
    raw = t[col].min().execute() if spec.metric == MetricType.RETENTION else t[col].max().execute()
    if raw is None or pd.isna(raw):
        _set_result(run, spec.key, ResultEnum.failed, f"No timestamp value found in '{spec.field}'")
        return
    ts = pd.Timestamp(raw)
    if ts.tzinfo is None:
        ts = ts.tz_localize("UTC")
    now = pd.Timestamp.now(tz="UTC")
    delta_seconds = (now - ts).total_seconds()
    ok = delta_seconds < spec.seconds
    label = "Retention" if spec.metric == MetricType.RETENTION else "Freshness"
    _set_result(
        run,
        spec.key,
        ResultEnum.passed if ok else ResultEnum.failed,
        None if ok else f"{label} is {int(delta_seconds)}s, which exceeds the threshold of {spec.seconds}s",
    )


def _run_custom_sql(run: Run, con, spec: CheckSpec):
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
            row = cursor.fetchone()
        finally:
            try:
                cursor.close()
            except Exception:
                pass
        return _py(row[0]) if row else None


# ---------------------------------------------------------------------------
# result helpers
# ---------------------------------------------------------------------------
def _evaluate(run: Run, spec: CheckSpec, value):
    if spec.threshold is None:
        _set_result(run, spec.key, ResultEnum.passed, None)
        return
    ok = spec.threshold.passes(value)
    target = spec.field or spec.model
    _set_result(
        run,
        spec.key,
        ResultEnum.passed if ok else ResultEnum.failed,
        None if ok else f"Actual {spec.metric.value}({target}) was {value}, expected {spec.threshold.describe()}",
    )


def _set_result(run: Run, key: str, result: ResultEnum, reason: Optional[str]):
    check = next((c for c in run.checks if c.key == key), None)
    if check is None:
        return
    check.result = result
    if reason is not None:
        check.reason = reason


def _fail_all(run: Run, specs: List[CheckSpec], result: ResultEnum, reason: str):
    for spec in specs:
        _set_result(run, spec.key, result, reason)


def _resolve_col(columns: dict, field: str) -> str:
    actual = columns.get(field.lower()) if field else None
    if actual is None:
        raise _ColumnNotFound(f"Column '{field}' not found")
    return actual


def _resolve_table(con, model: str):
    """Resolve a table by name, tolerating case differences across dialects."""
    try:
        return con.table(model)
    except Exception:
        try:
            available = con.list_tables()
        except Exception:
            raise
        match = next((name for name in available if name.lower() == model.lower()), None)
        if match is None:
            raise
        return con.table(match)


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
