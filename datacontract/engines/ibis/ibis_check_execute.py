"""Execute the engine-neutral check IR against a data source using ibis.

This replaces ``check_soda_execute``. For each model it batches the count-style
metrics (row_count, missing_count, invalid_count) into a single aggregation
query and runs dedicated queries for duplicates, schema/type, freshness/retention
and user SQL. Thresholds are evaluated in Python and the outcome written back
onto the pre-registered ``Check`` objects in the run.
"""

from __future__ import annotations

import logging
import re
import uuid
from collections import defaultdict
from functools import cache
from typing import List, Optional

from open_data_contract_standard.model import OpenDataContractStandard, SchemaProperty, Server

from datacontract.engines.checks.check_spec import CheckSpec, MetricType
from datacontract.engines.checks.physical_type_match import physical_type_matches
from datacontract.engines.checks.severity import failure_result
from datacontract.engines.checks.type_normalize import (
    format_mismatch_reason,
    normalize_type_name,
    schema_property_matches,
    schema_property_mismatch_reason,
    schema_property_mismatch_reasons,
)
from datacontract.engines.ibis.connections.connect import connect_ibis
from datacontract.engines.ibis.dtype_category import ibis_dtype_to_schema_property
from datacontract.engines.ibis.native_type import (
    fetch_native_types,
    sqlglot_dialect,
    supports_native_type_introspection,
)
from datacontract.engines.ibis.snowflake_structured_types import fetch_structured_types, has_nesting
from datacontract.imports.odcs_helper import property_from_type_string
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import Check, ResultEnum, Run
from datacontract.model.server import get_server_type

logger = logging.getLogger(__name__)

# Most server types have an install extra of the same name. These do not: they
# are read with duckdb, so naming the server type would send users to an extra
# that does not exist (`local`) or to an unrelated one (`api` installs the web
# server dependencies, not a test backend).
_INSTALL_EXTRAS = {"local": "duckdb", "api": "duckdb", "iceberg": "iceberg"}
_FULL_TYPE_STRING_SERVERS = {"athena", "trino", "databricks", "bigquery", "clickhouse", "hive"}


def install_extra_for(server_type: Optional[str]) -> str:
    return _INSTALL_EXTRAS.get(server_type, server_type)


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
                qualityId=spec.quality_id,
                tags=spec.tags,
                dimension=spec.dimension,
                qualityDefinition=spec.quality_definition,
                engine="datacontract-cli",
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
    model_filters: Optional[dict[str, str]] = None,
    config=None,
    untrusted_contract: bool = False,
):
    if data_contract is None:
        run.log_warn("Cannot run the checks, as the data contract is invalid")
        return

    # Checks the new engine cannot run (e.g. raw SodaCL) get their preset result.
    executable: List[CheckSpec] = []
    for spec in specs:
        if spec.metric == MetricType.UNSUPPORTED:
            set_result(run, spec.key, ResultEnum(spec.preset_result or "warning"), spec.preset_reason)
        else:
            executable.append(spec)

    if not executable:
        return

    run.log_info("Running checks with ibis")
    try:
        con = connect_ibis(
            run, data_contract, server, spark, duckdb_connection, schema_name, config, untrusted_contract
        )
    except DataContractException:
        raise
    except ImportError:
        server_type = get_server_type(server)
        reason = (
            f"The '{server_type}' backend is not installed. "
            f"Install it with: pip install 'datacontract-cli[{install_extra_for(server_type)}]'"
        )
        logger.exception("ibis backend import failed")
        run.log_error(reason)
        run.checks.append(
            Check(
                type="general",
                name="Data Contract Tests",
                result=ResultEnum.failed,
                reason=reason,
                engine="datacontract-cli",
            )
        )
        return
    except Exception as e:
        reason = _first_line(str(e)) or "Could not connect to the data source."
        logger.exception("ibis connection failed")
        run.log_error(f"Could not connect to the data source: {reason}")
        run.checks.append(
            Check(
                type="general",
                name="Data Contract Tests",
                result=ResultEnum.failed,
                reason=reason,
                engine="datacontract-cli",
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
            _run_model(
                run,
                con,
                model,
                model_specs,
                data_contract,
                server,
                include_failed_samples,
                row_filter=(model_filters or {}).get(model),
                schema_name=schema_name,
            )
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
    row_filter: Optional[str] = None,
    schema_name: str = "all",
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
        if native_types is None and supports_native_type_introspection(get_server_type(server)):
            # Each physical type check falls back to its logicalType, which can pass a
            # physicalType nothing compared, so the run has to say so.
            run.log_warn(
                f"Could not read the column types of '{model}' from the {get_server_type(server)} catalog; "
                "the physical type checks compare the logicalType instead"
            )

    # Snowflake collapses structured OBJECT/ARRAY nesting in the ibis dtype; read
    # the real nested types from SHOW COLUMNS so the nested checks can resolve them.
    structured_types = None
    if get_server_type(server) == "snowflake" and any(
        spec.metric in (MetricType.FIELD_TYPE, MetricType.FIELD_PHYSICAL_TYPE)
        or (spec.metric == MetricType.FIELD_PRESENT and _is_nested_path(spec.field))
        for spec in specs
    ):
        structured_types = fetch_structured_types(con, server, t.get_name())
    # The other catalogs report a nested column's whole native type in one string, e.g.
    # array(row(sku varchar)), which the nested physical type checks read their types from.
    native_trees = structured_types
    if native_types and get_server_type(server) in _FULL_TYPE_STRING_SERVERS:
        parsed = {column: property_from_type_string(column, native) for column, native in native_types.items()}
        native_trees = {column: prop for column, prop in parsed.items() if has_nesting(prop)}

    # Applied after the catalog reads above: those need the real table name, and
    # the schema/type checks compare declared types, which no row filter changes.
    # DUPLICATE_COUNT reads the rows of `unfiltered_t` whose key occurs in `t`,
    # see _duplicate_scope.
    unfiltered_t = None
    if row_filter:
        try:
            unfiltered_t = t
            t = _apply_row_filter(t, model, row_filter)
        except Exception as e:
            logger.warning("Could not apply row filter to model '%s': %s", model, e)
            # A predicate that does not compile is a configuration problem, not a
            # data violation, so the checks error rather than fail. Only the checks
            # that read rows are affected.
            _fail_all(
                run,
                [s for s in specs if s.requires_data_read],
                ResultEnum.error,
                f"Could not apply row filter '{row_filter}': {e}",
            )
            specs = [s for s in specs if not s.requires_data_read]
            if not specs:
                return

    # Read at most once, and only for a check that needs a denominator; the batched
    # aggregation reads its own row count within the same query.
    @cache
    def model_row_count() -> int:
        rc = t.count().execute()
        return 0 if rc is None else int(rc)

    agg_exprs = []  # list[(spec, named_expr)]
    for spec in specs:
        try:
            named = None  # set for count-style metrics that get batched
            if spec.metric == MetricType.ROW_COUNT:
                named = t.count().name(spec.key)
            elif spec.metric == MetricType.MISSING_COUNT:
                predicate = _row_predicate(t, columns, spec.field, lambda c: _missing_expr(c, spec.missing_values))
                named = _count_true(predicate).name(spec.key)
            elif spec.metric == MetricType.INVALID_COUNT:
                dtype = _resolve_dtype(schema, spec.field)
                if _has_array_constraints(spec) and not dtype.is_array():
                    # Silently dropping the constraint would report the check as
                    # passed, which is worse than saying it could not be run.
                    _set_impl(run, spec.key, _describe(spec), None)
                    set_result(
                        run,
                        spec.key,
                        ResultEnum.error,
                        f"Column {spec.field} is {dtype}, not an array, so the constraint cannot be measured.",
                    )
                    continue
                unconstrained = []

                def _invalid(c, _t=t, _dtype=dtype, _spec=spec, _flag=unconstrained):
                    import ibis

                    built = _invalid_expr(_t, c, _dtype, _spec)
                    if built is None:
                        _flag.append(True)
                        return ibis.literal(False)
                    return built

                expr = _row_predicate(t, columns, spec.field, _invalid)
                if unconstrained:
                    # No validity constraints => nothing can be invalid.
                    _set_impl(run, spec.key, "invalid_count = 0 (no validity constraints configured)", None)
                    _evaluate(run, spec, 0, row_count=model_row_count())
                else:
                    named = _count_true(expr).name(spec.key)
            elif spec.metric == MetricType.DUPLICATE_COUNT:
                _run_duplicate(run, t, unfiltered_t, columns, spec, model_row_count())
            elif spec.metric == MetricType.MISSING_REFERENCE_COUNT:
                _run_missing_reference(run, con, server, t, columns, spec, schema_name)
            elif spec.metric == MetricType.FIELD_PRESENT:
                _run_present(run, con, model, schema, spec, structured_types)
            elif spec.metric == MetricType.FIELD_TYPE:
                _run_type(run, schema, columns, spec, structured_types, native_types)
            elif spec.metric == MetricType.FIELD_PHYSICAL_TYPE:
                _run_physical_type(run, con, server, schema, native_types, spec, native_trees)
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
            set_result(run, spec.key, ResultEnum.failed, str(e) or f"Column '{spec.field}' not found")
        except Exception as e:
            logger.warning("Check '%s' errored: %s", spec.key, e)
            set_result(run, spec.key, ResultEnum.failed, f"Error evaluating check: {e}")

    if agg_exprs:
        _run_aggregation(run, t, agg_exprs)

    if include_failed_samples:
        _collect_failed_samples(run, t, unfiltered_t, columns, schema, model, specs, data_contract, server)


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
            set_result(run, spec.key, ResultEnum.failed, f"Error evaluating check: {e}")
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


def _collect_failed_samples(run, t, unfiltered_t, columns, schema, model, specs, data_contract, server):
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
            # DUPLICATE_COUNT samples come from the same rows the count was
            # measured against, or the two would disagree.
            if spec.metric == MetricType.DUPLICATE_COUNT:
                table = _duplicate_scope(t, unfiltered_t, columns, spec)
            else:
                table = t
            samples = _samples_for(table, columns, schema, spec, identifiers, sensitive)
        except Exception as e:  # pragma: no cover - sampling is best-effort
            logger.debug("Could not collect failed samples for '%s': %s", spec.key, e)
            continue
        if samples:
            check.failedSamples = samples


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
        if not _is_item_duplicate(spec):
            return _duplicate_samples(t, columns, sensitive, spec)
        predicate = _item_duplicate_predicate(t, columns, spec.field)
    elif spec.metric == MetricType.MISSING_COUNT:
        predicate = _row_predicate(t, columns, spec.field, lambda c: _missing_expr(c, spec.missing_values))
    else:  # INVALID_COUNT
        dtype = _resolve_dtype(schema, spec.field)
        unconstrained = []

        def _invalid(c, _flag=unconstrained):
            import ibis

            built = _invalid_expr(t, c, dtype, spec)
            if built is None:
                _flag.append(True)
                return ibis.literal(False)
            return built

        predicate = _row_predicate(t, columns, spec.field, _invalid)
        if unconstrained:
            return None

    # A nested path is not a column; show the one it starts from.
    root = spec.field.split("[]")[0].split(".")[0] if spec.field else None
    select_cols = _select_columns(columns, sensitive, [*identifiers, root])
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


def _missing_expr(col, missing_values):
    cond = col.isnull()
    if missing_values:
        non_null = [v for v in missing_values if v is not None]
        if non_null:
            cond = cond | col.isin(non_null)
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


def _exasol_regex_search(column, pattern: str):
    """``REGEXP_INSTR(column, pattern) > 0``: Exasol's regex match is the
    ``REGEXP_LIKE`` predicate, which ibis cannot compile ``re_search`` to."""
    import ibis

    @ibis.udf.scalar.builtin
    def regexp_instr(expression: str, pattern: str) -> int: ...

    return regexp_instr(column, pattern) > 0


def _regex_search_expr(t, column, pattern: str):
    """Unanchored regex/pattern match, portable across backends.

    Most ibis backends compile ``re_search`` to a native regex operator. SQL
    Server has none, so fall back to a PATINDEX-based LIKE match for the mssql
    backend; Exasol has one, but only as a predicate ibis does not know.
    """
    backend = _backend_name(t)
    if backend == "mssql":
        return _mssql_pattern_search(column, pattern)
    if backend == "exasol":
        return _exasol_regex_search(column, pattern)
    return column.re_search(pattern)


def _has_array_constraints(spec: CheckSpec) -> bool:
    """Whether the check measures the elements of an array."""
    return spec.valid_min_items is not None or spec.valid_max_items is not None or bool(spec.valid_unique_items)


def _valid_expr(t, col, dtype, spec: CheckSpec):
    """Boolean: a non-missing value satisfies all configured validity constraints."""
    conds = []
    if spec.valid_values is not None:
        conds.append(col.isin(spec.valid_values))
    if spec.valid_regex is not None:
        conds.append(_regex_search_expr(t, _as_string(col, dtype), spec.valid_regex))
    if spec.valid_min is not None:
        conds.append(col >= spec.valid_min)
    if spec.valid_max is not None:
        conds.append(col <= spec.valid_max)
    if spec.valid_min_length is not None:
        conds.append(_as_string(col, dtype).length() >= spec.valid_min_length)
    if spec.valid_max_length is not None:
        conds.append(_as_string(col, dtype).length() <= spec.valid_max_length)
    # Array constraints count the elements of the row's array. A column the
    # contract calls an array but the server does not cannot be measured that
    # way, so the constraint is left off rather than compiled into invalid SQL.
    if dtype is not None and dtype.is_array():
        if spec.valid_min_items is not None:
            conds.append(col.length() >= spec.valid_min_items)
        if spec.valid_max_items is not None:
            conds.append(col.length() <= spec.valid_max_items)
        if spec.valid_unique_items:
            conds.append(col.unique().length() == col.length())
    if not conds:
        return None
    expr = conds[0]
    for c in conds[1:]:
        expr = expr & c
    return expr


def _invalid_expr(t, col, dtype, spec: CheckSpec):
    """Reproduce soda's invalid_count: NOT missing AND (NOT valid OR in invalid_values)."""
    missing = _missing_expr(col, spec.missing_values)
    valid = _valid_expr(t, col, dtype, spec)
    invalid_terms = []
    if valid is not None:
        invalid_terms.append(~valid)
    if spec.invalid_values:
        invalid_terms.append(col.isin(spec.invalid_values))
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
    if spec.valid_min_items is not None:
        info["min_items"] = spec.valid_min_items
    if spec.valid_max_items is not None:
        info["max_items"] = spec.valid_max_items
    if spec.valid_unique_items:
        info["unique_items"] = True
    return info


# ---------------------------------------------------------------------------
# dedicated check runners
# ---------------------------------------------------------------------------
def _duplicate_scope(t, unfiltered_t, columns, spec: CheckSpec):
    """The rows a DUPLICATE_COUNT check reads.

    Without --filter (`unfiltered_t` is None), the whole table. With one, every
    row -- selected or not -- whose key occurs among the selected rows: that finds
    a key repeated within the window and one repeated across its edge, and skips
    keys the window does not contain, whose duplicates belong to another window.

    Rows with a NULL key are left out: as with SQL UNIQUE, NULLs are never
    duplicates of each other. An item-uniqueness check (`a[].b`) looks inside
    each row's own array, so it reads the filtered rows as they are.
    """
    if _is_item_duplicate(spec):
        return t
    fields = spec.columns or [spec.field]
    if unfiltered_t is None:
        return t.filter([_resolve_expr(t, columns, f).notnull() for f in fields])
    rows = unfiltered_t.filter([_resolve_expr(unfiltered_t, columns, f).notnull() for f in fields])
    window = t.select([_resolve_expr(t, columns, f).name(f"_key{i}") for i, f in enumerate(fields)]).distinct()
    return rows.semi_join(window, [_resolve_expr(rows, columns, f) == window[f"_key{i}"] for i, f in enumerate(fields)])


def _run_duplicate(run: Run, t, unfiltered_t, columns, spec: CheckSpec, row_count: int):
    """The threshold is compared against the duplicated key count; the rows those
    keys span are what is reported as failed."""
    import pandas as pd

    if _is_item_duplicate(spec):
        _run_item_duplicate(run, t, columns, spec, row_count)
        return

    t = _duplicate_scope(t, unfiltered_t, columns, spec)
    cols = [_resolve_expr(t, columns, c) for c in (spec.columns or [spec.field])]
    grouped = t.group_by(cols).aggregate(_dup_n=t.count())
    dup_groups = grouped.filter(grouped["_dup_n"] > 1)
    _record_sql(run, spec, dup_groups)
    totals = dup_groups.aggregate(
        _dup_keys=dup_groups["_dup_n"].count(), _dup_rows=dup_groups["_dup_n"].sum()
    ).execute()

    def _int(value) -> int:
        return 0 if (value is None or pd.isna(value)) else int(value)

    row = totals.iloc[0]
    dup_count = _int(row["_dup_keys"])
    _evaluate(run, spec, dup_count, row_count=row_count)
    extra = {"failed_rows": _int(row["_dup_rows"])}
    if len(cols) > 1:
        extra["columns"] = spec.columns
    _update_diagnostics(run, spec.key, extra)


def _run_missing_reference(run: Run, con, server, t, columns, spec: CheckSpec, schema_name: str):
    """Count the rows whose foreign key is not null and has no matching row in the referenced model."""
    try:
        referenced = _resolve_table(con, spec.referenced_model, _table_database(con, server)).view()
    except Exception as e:
        # With --schema-name, file sources only load the tested model, so the referenced one may be absent.
        reason = f"Could not read the referenced model '{spec.referenced_model}': {_first_line(str(e))}"
        if schema_name != "all":
            reason += (
                f". --schema-name {schema_name} reads only that schema from files; "
                "test without --schema-name to check this relationship."
            )
        set_result(run, spec.key, ResultEnum.warning, reason)
        return
    referenced_columns = {c.lower(): c for c in referenced.columns}
    keys = [_resolve_col(columns, c) for c in spec.columns]
    rows = t.filter([t[k].notnull() for k in keys])
    predicates = [
        rows[k] == referenced[_resolve_col(referenced_columns, r)] for k, r in zip(keys, spec.referenced_columns)
    ]
    expr = rows.anti_join(referenced, predicates).count()
    _record_sql(run, spec, expr)
    value = expr.execute()
    _evaluate(run, spec, 0 if value is None else int(value))


def _is_item_duplicate(spec: CheckSpec) -> bool:
    return any("[]" in c for c in (spec.columns or [spec.field]) if c)


def _item_duplicate_predicate(t, columns, field: str):
    """Parent rows whose array repeats a value in the item property ``field``."""
    if field.endswith("[]"):
        # the items of an array of plain values are the values themselves
        array_path, leaf = field[:-2], None
    else:
        array_path, _, leaf = field.rpartition("[].")

    def _repeats(array):
        values = array if leaf is None else array.map(lambda element: _struct_path(element, leaf))
        return values.unique().length() < values.length()

    return _row_predicate(t, columns, array_path, _repeats)


def _run_item_duplicate(run: Run, t, columns, spec: CheckSpec, row_count: int):
    """``unique`` on an array item property: no parent may repeat a value inside its own array.

    Counted in parent rows.
    """
    bad = t.filter(_item_duplicate_predicate(t, columns, spec.field))
    _record_sql(run, spec, bad)
    repeats = int(bad.count().execute())
    _evaluate(run, spec, repeats, row_count=row_count)
    _update_diagnostics(run, spec.key, {"failed_rows": repeats})


def _run_present(run: Run, con, model: str, schema, spec: CheckSpec, structured_types=None):
    target = f"{model}__raw__" if spec.uses_raw_view else model
    _set_impl(run, spec.key, f"column '{spec.field}' exists in {target}", "introspection")
    if spec.uses_raw_view:
        try:
            raw = _resolve_table(con, f"{model}__raw__")
            table = raw
        except Exception:
            table = _resolve_table(con, model)
        located = _locate(table.schema(), None, spec.field)
    else:
        # Reuse the already-resolved model schema to avoid an extra lookup that
        # can fail on case-sensitive backends (for example Oracle).
        located = _locate(schema, structured_types, spec.field)
    if located is _UNREADABLE:
        set_result(run, spec.key, ResultEnum.warning, _unreadable_reason(spec.field))
        return
    ok = located is not None
    _set_diagnostics(run, spec.key, _diag(metric="field_present", field=spec.field, present=ok))
    set_result(
        run,
        spec.key,
        ResultEnum.passed if ok else ResultEnum.failed,
        None if ok else f"Required column '{spec.field}' is missing",
    )


def _run_type(
    run: Run,
    schema,
    columns,
    spec: CheckSpec,
    structured_types: dict[str, SchemaProperty] | None = None,
    native_types: dict[str, str] | None = None,
):
    _set_impl(
        run,
        spec.key,
        f"type of '{spec.field}' is compatible with '{spec.expected_type_label}'",
        "introspection",
    )
    located = _locate(schema, structured_types, spec.field)
    if located is _UNREADABLE:
        set_result(run, spec.key, ResultEnum.warning, _unreadable_reason(spec.field))
        return
    if located is None:
        _set_diagnostics(run, spec.key, _diag(metric="field_type", field=spec.field, expected=spec.expected_type_label))
        set_result(run, spec.key, ResultEnum.failed, f"Column '{spec.field}' is missing")
        return
    actual_prop, actual_label = located
    native_type = native_types.get(spec.field.lower()) if native_types else None
    if native_type and actual_prop.physicalType is None and spec.expected_category == "vector":
        # ibis reports a vector as a plain array; the catalog's declared type carries the dimensions
        actual_prop = actual_prop.model_copy(update={"physicalType": native_type})
    _set_diagnostics(
        run,
        spec.key,
        _diag(
            metric="field_type",
            field=spec.field,
            expected=spec.expected_type_label,
            actual=actual_label,
        ),
    )
    if schema_property_matches(spec.expected_schema_property, actual_prop):
        set_result(run, spec.key, ResultEnum.passed, None)
    else:
        # a line that covers a map's key and value names the part that differs
        path = spec.field if has_nesting(spec.expected_schema_property) else ""
        reason = schema_property_mismatch_reason(spec.expected_schema_property, actual_prop, path)
        set_result(
            run,
            spec.key,
            ResultEnum.failed,
            reason or f"Expected type '{spec.expected_type_label}' but column is '{actual_label}'",
        )


def _run_physical_type(
    run: Run,
    con,
    server,
    schema,
    native_types,
    spec: CheckSpec,
    native_trees: dict[str, SchemaProperty] | None = None,
):
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
    located = _locate(schema, native_trees, spec.field)
    if located is _UNREADABLE:
        set_result(run, spec.key, ResultEnum.warning, _unreadable_reason(spec.field))
        return
    if located is None:
        _set_diagnostics(
            run, spec.key, _diag(metric="field_physical_type", field=spec.field, expected=spec.expected_physical_type)
        )
        set_result(run, spec.key, ResultEnum.failed, f"Column '{spec.field}' is missing")
        return
    actual_prop, _ = located

    # Snowflake's catalog reports a structured OBJECT/ARRAY as its bare token, dropping
    # the nested types; the tree recovered from SHOW COLUMNS renders the real native type.
    nested_path = _is_nested_path(spec.field)
    structured_prop = native_trees.get(spec.field.lower()) if native_trees and not nested_path else None
    if nested_path:
        actual_native = actual_prop.physicalType
    elif structured_prop is not None and has_nesting(structured_prop):
        actual_native = structured_prop.physicalType
    else:
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

    expected = spec.expected_schema_property
    if result is True and expected is not None and has_nesting(expected):
        # A map's key and value, and the items of an array's items, have no line of their own
        errors = schema_property_mismatch_reasons(expected, actual_prop, spec.field, sqlglot_dialect(con))
        if errors:
            _update_diagnostics(run, spec.key, {"errors": [error.message for error in errors]})
            verified = any(error.verifiable for error in errors)
            set_result(
                run,
                spec.key,
                ResultEnum.failed if verified else ResultEnum.warning,
                format_mismatch_reason(errors),
            )
            return
    if result is True:
        set_result(run, spec.key, ResultEnum.passed, None)
        return
    if result is False:
        set_result(run, spec.key, ResultEnum.failed, reason)
        return

    # Only the catalogs that report a nested column's whole type have a native type for a nested path.
    # The logicalType fallback would report `passed` for a physical type nothing
    # compared, so skip instead. An unreadable catalog falls back like the top level, which the run logs.
    if actual_native is None and nested_path and native_types is not None:
        set_result(
            run,
            spec.key,
            ResultEnum.warning,
            f"The native type of '{spec.field}' is not read for nested paths; skipping the physical type check",
        )
        return

    # result is None: the physical type could not be evaluated. Fall back to the
    # logicalType category check when the property declares one.
    fallback = spec.expected_schema_property
    if fallback is not None and fallback.logicalType is not None:
        if schema_property_matches(fallback, actual_prop):
            set_result(run, spec.key, ResultEnum.passed, None)
        else:
            mismatch = schema_property_mismatch_reason(fallback, actual_prop)
            actual_label = actual_native or located[1]
            set_result(
                run,
                spec.key,
                ResultEnum.failed,
                mismatch or f"Expected type '{fallback.logicalType}' but column is '{actual_label}'",
            )
        return

    set_result(run, spec.key, ResultEnum.warning, f"{reason}; skipping the physical type check")


def _run_freshness(run: Run, t, columns, spec: CheckSpec):
    import pandas as pd

    col = _resolve_expr(t, columns, spec.field)
    reduction = col.min() if spec.metric == MetricType.RETENTION else col.max()
    _record_sql(run, spec, t.aggregate(value=reduction))
    raw = reduction.execute()
    if raw is None or pd.isna(raw):
        _set_diagnostics(
            run, spec.key, _diag(metric=spec.metric.value, field=spec.field, threshold_seconds=spec.seconds)
        )
        set_result(run, spec.key, ResultEnum.failed, f"No timestamp value found in '{spec.field}'")
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
    set_result(
        run,
        spec.key,
        ResultEnum.passed if ok else ResultEnum.failed,
        None if ok else f"{label} is {int(delta_seconds)}s, which exceeds the threshold of {spec.seconds}s",
    )


def _run_custom_sql(run: Run, con, spec: CheckSpec):
    _set_impl(run, spec.key, spec.query, "sql")
    value = _run_scalar(con, spec.query, spec.dialect)
    _evaluate(run, spec, value)
    if spec.diagnostics:
        _update_diagnostics(run, spec.key, spec.diagnostics)


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
    if row_count is not None:
        diag["row_count"] = row_count
    # For "bad row" metrics, show how many of the total rows failed.
    if row_count is not None and is_bad_row:
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
        set_result(run, spec.key, ResultEnum.passed, None)
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
    set_result(run, spec.key, ResultEnum.passed if ok else _fail_result(spec), reason)


def _fail_result(spec: CheckSpec) -> ResultEnum:
    """The result to set when a check does not meet its threshold.

    Honors ODCS ``quality.severity``: a non-blocking severity makes the check a
    warning (which does not fail the run); the default is a hard failure.
    """
    return failure_result(spec.severity)


def set_result(run: Run, key: str, result: ResultEnum, reason: Optional[str]) -> None:
    """Set the result of the pre-registered check identified by ``key``."""
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
        set_result(run, spec.key, result, reason)


def _resolve_col(columns: dict, field: str) -> str:
    actual = columns.get(field.lower()) if field else None
    if actual is None:
        raise _ColumnNotFound(f"Column '{field}' not found")
    return actual


def _resolve_expr(t, columns: dict, field: str):
    if field is None:
        raise _ColumnNotFound("Column 'None' not found")
    if "." not in field:
        return t[_resolve_col(columns, field)]
    return _resolve_nested_expr(t, field, columns)


def _resolve_nested_expr(t, field: str, columns: dict):
    head, _, tail = field.partition(".")
    return _struct_path(t[_resolve_col(columns, head)], tail)


def _row_predicate(t, columns: dict, field: str, build):
    """A boolean over *parent* rows for ``build`` applied at ``field``.

    An array hop (``items[].sku``) becomes "some element satisfies build", so the
    row count never changes and an empty array is never a violation.
    """
    if field.endswith("[]"):
        # The items of an array of plain values: the row breaks the rule when one of its items does
        return _row_predicate(t, columns, field[:-2], lambda array: array.filter(build).length() > 0)
    head, marker, tail = field.partition("[].")
    if not marker:
        if "." not in field:
            return build(_resolve_expr(t, columns, field))
        column, _, path = field.partition(".")
        return _path_predicate(t[_resolve_col(columns, column)], path, build)
    return _resolve_expr(t, columns, head).filter(lambda i: _element_predicate(i, tail, build)).length() > 0


def _element_predicate(element, path: str, build):
    head, marker, tail = path.partition("[].")
    if not marker:
        first, _, rest = path.partition(".")
        value = _struct_path(element, first)
        return _path_predicate(value, rest, build) if rest else build(value)
    return _struct_path(element, head).filter(lambda i: _element_predicate(i, tail, build)).length() > 0


def _path_predicate(value, path: str, build):
    """``build`` at ``path`` inside the struct ``value``, false where a struct on the way is null.

    The fields of an absent optional object are not missing; the object's own
    ``required`` check covers its absence.
    """
    present = None
    for part in path.split("."):
        present = value.notnull() if present is None else present & value.notnull()
        value = value[_struct_field_name(value, part)]
    return present & build(value)


def _struct_path(value, path: str):
    for part in path.split("."):
        value = value[_struct_field_name(value, part)]
    return value


def _struct_field_name(value, name: str) -> str:
    """The struct's own spelling of ``name``, which a backend may report in another case."""
    try:
        names = value.type().names
    except Exception:
        return name
    if name in names:
        return name
    match = next((n for n in names if n.lower() == name.lower()), None)
    if match is None:
        # the handler names the full path
        raise _ColumnNotFound()
    return match


_UNREADABLE = "unreadable"


def _resolve_dtype(schema, field: str):
    dtype = _walk_dtype(schema, field)
    return None if dtype is _UNREADABLE else dtype


def _walk_dtype(schema, field: str):
    """The ibis dtype at ``field``; ``None`` when it does not exist, ``_UNREADABLE`` when it lies
    inside untyped data (json, or a map standing in for an untyped object)."""
    if field is None:
        return None
    dtype = None
    for index, part in enumerate(field.split(".")):
        name, hop, _ = part.partition("[]")
        if index == 0:
            fields = schema
        elif dtype.is_struct():
            fields = dtype.fields
        else:
            return _UNREADABLE if dtype.is_json() or dtype.is_map() else None
        # Backends that report uppercase names (Snowflake, Oracle, Databricks)
        # must still match a contract that spells the field in lower case.
        actual = name if name in fields else next((k for k in fields.keys() if k.lower() == name.lower()), None)
        if actual is None:
            return None
        dtype = fields[actual]
        if hop:
            # `items[]` names the element type, not the array's own type.
            if not dtype.is_array():
                return _UNREADABLE if dtype.is_json() else None
            dtype = dtype.value_type
    return dtype


def _locate(schema, structured_types: dict[str, SchemaProperty] | None, field: str):
    """The real type at ``field`` as ``(property, label)``, from the catalog's nested native types
    where there are some, else from ibis; ``None`` or ``_UNREADABLE`` as for ``_walk_dtype``."""
    parts = field.split(".")
    node = structured_types.get(parts[0].partition("[]")[0].lower()) if structured_types else None
    if node is None:
        dtype = _walk_dtype(schema, field)
        if dtype is None or dtype is _UNREADABLE:
            return dtype
        if field.endswith("[]") and dtype.is_json():
            # an array whose element type the backend does not report, e.g. Snowflake's ARRAY
            return _UNREADABLE
        return ibis_dtype_to_schema_property(dtype), str(dtype)
    for index, part in enumerate(parts):
        name, hop, _ = part.partition("[]")
        if index:
            if not node.properties:
                return _UNREADABLE if _untyped(node) else None
            node = next((child for child in node.properties if (child.name or "").lower() == name.lower()), None)
            if node is None:
                return None
        if hop:
            if node.items is None:
                return _UNREADABLE if _untyped(node) else None
            node = node.items
    return node, node.physicalType


def _is_nested_path(field: Optional[str]) -> bool:
    return bool(field) and ("." in field or "[]" in field)


def _untyped(prop: SchemaProperty) -> bool:
    return normalize_type_name(prop.logicalType) in ("object", "array", None)


def _unreadable_reason(field: str) -> str:
    return f"'{field}' lies inside untyped data whose structure cannot be read; skipping the check"


def _table_database(con, server: Optional[Server]) -> Optional[str]:
    """The schema to qualify the table with during introspection, or ``None``.

    Two backends need the contract's ``server.schema`` passed explicitly instead
    of relying on ibis's default:

    - **Oracle** logs in as one user but the tables may be owned by a different
      schema (``server.schema``). ibis defaults the owner to the login user, so
      an unqualified lookup raises ``TableNotFound``.
    - **SQL Server** (``mssql`` backend) has no ``schema`` kwarg on
      ``do_connect()`` either, so it has the same limitation as Oracle: an
      unqualified lookup falls back to the login's default schema.
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
    if getattr(con, "name", None) in ("oracle", "mssql"):
        return server.schema_
    # A duckdb database file is opened without a schema (`connect()` takes none),
    # so a table outside `main` has to be qualified at lookup.
    if get_server_type(server) == "duckdb":
        return server.schema_
    # Redshift rides the Postgres backend, so detect it by the contract's server
    # type rather than con.name.
    if get_server_type(server) == "redshift":
        return server.schema_
    return None


_SIMPLE_IDENTIFIER = re.compile(r"[A-Za-z_][A-Za-z0-9_]*$")


def _apply_row_filter(t, model: str, predicate: str):
    """Restrict a bound table to the rows matching a raw SQL predicate.

    The predicate is written in the backend's dialect and references columns
    unqualified. Wrapping the aliased relation via ``Table.sql`` keeps the
    result a regular table expression, so every downstream query (batched
    aggregation, duplicates, freshness, failed samples) compiles with the
    WHERE clause included and the recorded per-check SQL shows it.
    """
    alias = f"{model}_filtered" if _SIMPLE_IDENTIFIER.match(model) else "filtered_rows"
    # ibis quotes the alias it defines, Exasol upper-cases the unquoted reference to it.
    if _backend_name(t) == "exasol":
        alias = alias.upper()
    return t.alias(alias).sql(f"SELECT * FROM {alias} WHERE {predicate}")


def _resolve_table(con, model: str, database: Optional[str] = None):
    """Resolve a table by name, tolerating case differences."""
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
