"""Build the engine-neutral check IR from an ODCS data contract.

This is the test-path counterpart to the SodaCL builder in
``datacontract/export/sodacl_check_builder.py``: same enumeration of schema,
quality and service-level checks, same stable ``key``/``type`` strings, but it
emits :class:`CheckSpec` objects (consumed by the ibis engine) instead of SodaCL
YAML. The two paths share no code so the export format stays fully isolated.
"""

from __future__ import annotations

import logging
import re
from typing import List, Optional

import yaml
from open_data_contract_standard.model import (
    DataQuality,
    OpenDataContractStandard,
    SchemaObject,
    SchemaProperty,
    Server,
)

from datacontract.config.variables import UnresolvedVariableError, resolve_variables
from datacontract.engines.checks.check_spec import CheckSpec, MetricType, Op, Threshold
from datacontract.engines.checks.dimensions import default_dimension
from datacontract.engines.checks.sql_guard import dialect_for_server_type, is_read_only_query
from datacontract.engines.checks.type_normalize import normalize_type_name
from datacontract.engines.ibis.native_type import supports_native_type_introspection
from datacontract.model.enum_values import get_enum_values
from datacontract.model.server import get_server_type

logger = logging.getLogger(__name__)

_FILE_SERVER_TYPES = {"local", "s3", "gcs", "azure"}


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def _get_logical_type_option(prop: SchemaProperty, key: str):
    if prop.logicalTypeOptions is None:
        return None
    return prop.logicalTypeOptions.get(key)


def is_check_types(server: Optional[Server]) -> bool:
    """Type checks only make sense where the data source carries real types."""
    if server is None:
        return True
    return server.format not in ("json", "csv", "avro")


def to_schema_name(schema_object: SchemaObject, server_type: Optional[str]) -> str:
    # Kafka messages are loaded into a table named after the schema object (the logical
    # name), not after the topic the physicalName holds.
    if server_type == "kafka":
        return schema_object.name
    if schema_object.physicalName:
        return schema_object.physicalName
    return schema_object.name


def _scalar_element_type(prop: SchemaProperty, physical: bool) -> Optional[str]:
    """The declared element type of an array of scalars, or None for anything else."""
    if normalize_type_name(prop.logicalType or prop.physicalType) != "array" or prop.items is None:
        return None
    items = prop.items
    if items.properties or items.items is not None:
        return None
    label = (items.physicalType or items.logicalType) if physical else (items.logicalType or items.physicalType)
    if normalize_type_name(label) in ("object", "array"):
        return None
    return label


def _declared_type_label(prop: SchemaProperty, physical: bool) -> Optional[str]:
    """Render the declared type with its children, e.g. ``OBJECT(code VARCHAR(10), description VARCHAR)``."""
    label = (prop.physicalType or prop.logicalType) if physical else (prop.logicalType or prop.physicalType)
    base = normalize_type_name(label)
    if base == "array" and prop.items is not None:
        return f"{label}({_declared_type_label(prop.items, physical)})"
    if base == "object" and prop.properties:
        children = ", ".join(f"{child.name} {_declared_type_label(child, physical)}" for child in prop.properties)
        return f"{label}({children})"
    return label


def _nested_type_check(model: str, field: str, prop: SchemaProperty, physical: bool) -> CheckSpec:
    check_type = "field_nested_physical_type" if physical else "field_nested_type"
    element = _scalar_element_type(prop, physical)
    if element is not None:
        name = f"Check that items of array {field} have {'physical type' if physical else 'type'} {element}"
    else:
        name = f"Check that nested {'physical types' if physical else 'types'} of {field} are correct"
    return CheckSpec(
        key=f"{model}__{field}__{check_type}",
        category="schema",
        type=check_type,
        name=name,
        model=model,
        field=field,
        metric=MetricType.FIELD_NESTED_TYPE,
        expected_type_label=_declared_type_label(prop, physical),
        expected_schema_property=prop,
    )


def quality_definition_yaml(quality: DataQuality) -> str:
    """The quality rule as YAML, as the CLI parsed it: ODCS keys the model does not
    know are dropped, and comments with them."""
    return yaml.safe_dump(quality.model_dump(exclude_none=True), sort_keys=False)


_PERCENT_UNITS = {"percent", "percentage", "%"}


def is_percent_unit(quality: DataQuality) -> bool:
    """True when the quality threshold is expressed as a percentage of rows.

    ODCS carries this on ``quality.unit`` (e.g. ``unit: percent``). The default
    (rows / absolute count) returns False.
    """
    unit = getattr(quality, "unit", None)
    return unit is not None and str(unit).strip().lower() in _PERCENT_UNITS


def to_threshold(quality: DataQuality) -> Optional[Threshold]:
    if quality.mustBe is not None:
        return Threshold(Op.EQ, quality.mustBe)
    if quality.mustNotBe is not None:
        return Threshold(Op.NE, quality.mustNotBe)
    if quality.mustBeGreaterThan is not None:
        return Threshold(Op.GT, quality.mustBeGreaterThan)
    if quality.mustBeGreaterOrEqualTo is not None:
        return Threshold(Op.GE, quality.mustBeGreaterOrEqualTo)
    if quality.mustBeLessThan is not None:
        return Threshold(Op.LT, quality.mustBeLessThan)
    if quality.mustBeLessOrEqualTo is not None:
        return Threshold(Op.LE, quality.mustBeLessOrEqualTo)
    if quality.mustBeBetween is not None:
        if len(quality.mustBeBetween) != 2:
            logger.warning(f"Quality check has invalid mustBeBetween (need 2 values): {quality.mustBeBetween}")
            return None
        return Threshold(Op.BETWEEN, quality.mustBeBetween[0], quality.mustBeBetween[1])
    if quality.mustNotBeBetween is not None:
        if len(quality.mustNotBeBetween) != 2:
            logger.warning(f"Quality check has invalid mustNotBeBetween (need 2 values): {quality.mustNotBeBetween}")
            return None
        return Threshold(Op.NOT_BETWEEN, quality.mustNotBeBetween[0], quality.mustNotBeBetween[1])
    return None


def prepare_query(
    quality: DataQuality, model_name: str, field_name: Optional[str], server: Optional[Server]
) -> Optional[str]:
    """Substitute placeholders in a user SQL query.

    Identifiers are emitted unquoted: the query runs through ibis against the
    backend, which resolves unquoted names per its own casing rules (this is
    what soda effectively did for the common backends).
    """
    if not quality.query:
        return None

    query = quality.query
    query = re.sub(r'["\']?\$?\{model}["\']?', model_name, query)
    query = re.sub(r'["\']?\$?\{table}["\']?', model_name, query)
    query = re.sub(r'["\']?\$?\{object}["\']?', model_name, query)

    schema_replacement = server.schema_ if server and server.schema_ else model_name
    query = re.sub(r'["\']?\$?\{schema}["\']?', schema_replacement, query)

    for placeholder in ("dataset", "project", "catalog", "database"):
        replacement = getattr(server, placeholder, None) if server else None
        query = re.sub(rf'["\']?\$?\{{{placeholder}}}["\']?', replacement or model_name, query)

    if field_name is not None:
        query = re.sub(r'["\']?\$?\{field}["\']?', field_name, query)
        query = re.sub(r'["\']?\$?\{column}["\']?', field_name, query)
        query = re.sub(r'["\']?\$?\{property}["\']?', field_name, query)

    return query


# ---------------------------------------------------------------------------
# entry point
# ---------------------------------------------------------------------------
def create_checks(
    data_contract: OpenDataContractStandard, server: Optional[Server], schema_name: str = "all"
) -> List[CheckSpec]:
    checks: List[CheckSpec] = []
    if data_contract.schema_ is None:
        return checks
    for schema_obj in data_contract.schema_:
        if schema_name != "all" and schema_obj.name != schema_name:
            continue
        if _is_azure_blob_schema(schema_obj, server):
            # File-metadata checks are emitted by check_azure_blob_file
            continue
        checks.extend(_to_schema_checks(schema_obj, server))
    checks.extend(_to_servicelevel_checks(data_contract, server))
    checks = [c for c in checks if c is not None]
    # Schema and service level checks cannot declare an ODCS dimension, so fill
    # in the one they measure. A rule that declared its own keeps it.
    for check in checks:
        if check.dimension is None:
            check.dimension = default_dimension(check.type)
    return checks


def _is_azure_blob_schema(schema_object: SchemaObject, server: Optional[Server]) -> bool:
    return server is not None and server.type == "azure" and (schema_object.logicalType or "").lower() == "blob"


def _to_schema_checks(schema_object: SchemaObject, server: Optional[Server]) -> List[CheckSpec]:
    checks: List[CheckSpec] = []
    server_type = server.type if server and server.type else None
    model = to_schema_name(schema_object, server_type)
    properties = schema_object.properties or []
    check_types = is_check_types(server)
    uses_raw_view = (
        server is not None and server.type in _FILE_SERVER_TYPES and server.format in ("csv", "parquet", "json")
    )

    # A primary key is both not-null and unique. A composite key is unique as a
    # tuple, not column by column, so its members are checked together after
    # the loop instead of individually.
    primary_key_props = sorted(
        (prop for prop in properties if prop.primaryKey),
        key=lambda prop: prop.primaryKeyPosition if prop.primaryKeyPosition is not None else 0,
    )
    primary_key_is_composite = len(primary_key_props) > 1

    for prop in properties:
        # ODCS physicalName is the real column; mirror to_schema_name at field level.
        field = prop.physicalName or prop.name

        checks.append(
            CheckSpec(
                key=f"{model}__{field}__field_is_present",
                category="schema",
                type="field_is_present",
                name=f"Check that field '{field}' is present",
                model=model,
                field=field,
                metric=MetricType.FIELD_PRESENT,
                uses_raw_view=uses_raw_view,
            )
        )

        # The raw view cannot provide nested type checks
        declared_base = normalize_type_name(prop.logicalType or prop.physicalType)
        nested_checks_possible = (
            check_types
            and not uses_raw_view
            and declared_base in ("object", "array")
            and (bool(prop.properties) or prop.items is not None)
        )
        base_prop = (
            SchemaProperty(name=prop.name, logicalType=prop.logicalType, physicalType=prop.physicalType)
            if nested_checks_possible
            else prop
        )

        # A declared physicalType is checked against the column's real native
        # type in the platform catalog and takes precedence over logicalType,
        # but only on backends that expose a meaningful native type. Elsewhere
        # (file sources, etc.) fall through to the logicalType category check.
        if check_types and prop.physicalType is not None and supports_native_type_introspection(server_type):
            checks.append(
                CheckSpec(
                    key=f"{model}__{field}__field_physical_type",
                    category="schema",
                    type="field_physical_type",
                    name=f"Check that field {field} has physical type {prop.physicalType}",
                    model=model,
                    field=field,
                    metric=MetricType.FIELD_PHYSICAL_TYPE,
                    expected_category=prop.physicalType,
                    expected_type_label=prop.physicalType,
                    expected_physical_type=prop.physicalType,
                    # Carried for the logicalType fallback when the native type
                    # cannot be read or the physicalType is cross-dialect.
                    expected_schema_property=base_prop if prop.logicalType is not None else None,
                )
            )
            if nested_checks_possible:
                checks.append(_nested_type_check(model, field, prop, physical=True))
        elif check_types and prop.logicalType is not None:
            label = prop.logicalType or ""
            checks.append(
                CheckSpec(
                    key=f"{model}__{field}__field_type",
                    category="schema",
                    type="field_type",
                    name=f"Check that field {field} has type {label}",
                    model=model,
                    field=field,
                    metric=MetricType.FIELD_TYPE,
                    expected_category=label,
                    expected_type_label=label,
                    expected_schema_property=base_prop,
                )
            )
            if nested_checks_possible:
                checks.append(_nested_type_check(model, field, prop, physical=False))

        if prop.required:
            checks.append(
                _missing_count_check(
                    model,
                    field,
                    "field_required",
                    Threshold(Op.EQ, 0),
                    name=f"Check that field {field} has no missing values",
                    category="schema",
                )
            )
        if prop.unique:
            checks.append(
                _duplicate_count_check(
                    model,
                    field,
                    "field_unique",
                    Threshold(Op.EQ, 0),
                    name=f"Check that unique field {field} has no duplicate values",
                    category="schema",
                )
            )
        if prop.primaryKey:
            # Skip whatever `required` and `unique` have already emitted, so a
            # property declaring both does not produce two identical checks.
            if not prop.required:
                checks.append(
                    _missing_count_check(
                        model,
                        field,
                        "field_primary_key_required",
                        Threshold(Op.EQ, 0),
                        name=f"Check that primary key field {field} has no missing values",
                        category="schema",
                    )
                )
            if not primary_key_is_composite and not prop.unique:
                checks.append(
                    _duplicate_count_check(
                        model,
                        field,
                        "field_primary_key_unique",
                        Threshold(Op.EQ, 0),
                        name=f"Check that primary key field {field} has no duplicate values",
                        category="schema",
                    )
                )

        min_length = _get_logical_type_option(prop, "minLength")
        if min_length is not None:
            checks.append(
                _invalid_count_check(
                    model,
                    field,
                    "field_min_length",
                    name=f"Check that field {field} has a min length of {min_length}",
                    valid_min_length=min_length,
                )
            )

        max_length = _get_logical_type_option(prop, "maxLength")
        if max_length is not None:
            checks.append(
                _invalid_count_check(
                    model,
                    field,
                    "field_max_length",
                    name=f"Check that field {field} has a max length of {max_length}",
                    valid_max_length=max_length,
                )
            )

        minimum = _get_logical_type_option(prop, "minimum")
        if minimum is not None:
            checks.append(
                _invalid_count_check(
                    model,
                    field,
                    "field_minimum",
                    name=f"Check that field {field} has a minimum of {minimum}",
                    valid_min=minimum,
                )
            )

        maximum = _get_logical_type_option(prop, "maximum")
        if maximum is not None:
            checks.append(
                _invalid_count_check(
                    model,
                    field,
                    "field_maximum",
                    name=f"Check that field {field} has a maximum of {maximum}",
                    valid_max=maximum,
                )
            )

        exclusive_minimum = _get_logical_type_option(prop, "exclusiveMinimum")
        if exclusive_minimum is not None:
            checks.append(
                _invalid_count_check(
                    model,
                    field,
                    "field_minimum",
                    name=f"Check that field {field} has a minimum of {exclusive_minimum}",
                    valid_min=exclusive_minimum,
                )
            )
            checks.append(
                _invalid_count_check(
                    model,
                    field,
                    "field_not_equal",
                    name=f"Check that field {field} is not equal to {exclusive_minimum}",
                    invalid_values=[exclusive_minimum],
                )
            )

        exclusive_maximum = _get_logical_type_option(prop, "exclusiveMaximum")
        if exclusive_maximum is not None:
            checks.append(
                _invalid_count_check(
                    model,
                    field,
                    "field_maximum",
                    name=f"Check that field {field} has a maximum of {exclusive_maximum}",
                    valid_max=exclusive_maximum,
                )
            )
            checks.append(
                _invalid_count_check(
                    model,
                    field,
                    "field_not_equal",
                    name=f"Check that field {field} is not equal to {exclusive_maximum}",
                    invalid_values=[exclusive_maximum],
                )
            )

        # Array constraints. ODCS allows these only on an array property, and
        # they measure the elements of one row's array, not the rows.
        min_items = _get_logical_type_option(prop, "minItems")
        if min_items is not None:
            checks.append(
                _invalid_count_check(
                    model,
                    field,
                    "field_min_items",
                    name=f"Check that field {field} has at least {min_items} items",
                    valid_min_items=min_items,
                )
            )

        max_items = _get_logical_type_option(prop, "maxItems")
        if max_items is not None:
            checks.append(
                _invalid_count_check(
                    model,
                    field,
                    "field_max_items",
                    name=f"Check that field {field} has at most {max_items} items",
                    valid_max_items=max_items,
                )
            )

        if _get_logical_type_option(prop, "uniqueItems") is True:
            checks.append(
                _invalid_count_check(
                    model,
                    field,
                    "field_unique_items",
                    name=f"Check that field {field} has no duplicate items",
                    valid_unique_items=True,
                )
            )

        pattern = _get_logical_type_option(prop, "pattern")
        if pattern is not None:
            checks.append(
                _invalid_count_check(
                    model,
                    field,
                    "field_regex",
                    name=f"Check that field {field} matches regex pattern {pattern}",
                    valid_regex=pattern,
                )
            )

        enum_values = get_enum_values(prop, include_quality_rule=False)
        if enum_values:
            checks.append(
                _invalid_count_check(
                    model,
                    field,
                    "field_enum",
                    name=f"Check that field {field} only contains enum values {enum_values}",
                    valid_values=list(enum_values),
                )
            )

        if prop.quality:
            checks.extend(_quality_checks(model, field, prop.quality, server))

    if primary_key_is_composite:
        primary_key_fields = [prop.physicalName or prop.name for prop in primary_key_props]
        checks.append(
            CheckSpec(
                key=f"{model}__primary_key_unique",
                category="schema",
                type="primary_key_unique",
                name=f"Check that primary key ({', '.join(primary_key_fields)}) has no duplicate values",
                model=model,
                field=None,
                metric=MetricType.DUPLICATE_COUNT,
                threshold=Threshold(Op.EQ, 0),
                columns=primary_key_fields,
            )
        )

    if schema_object.quality:
        checks.extend(_quality_checks(model, None, schema_object.quality, server))

    return checks


# ---------------------------------------------------------------------------
# metric-check builders (preserve legacy keys / types)
# ---------------------------------------------------------------------------
def _missing_count_check(
    model,
    field,
    check_type,
    threshold,
    name,
    category="quality",
    missing_values=None,
    threshold_is_percent=False,
    severity=None,
    dimension=None,
) -> CheckSpec:
    return CheckSpec(
        key=f"{model}__{field}__{check_type}",
        category=category,
        type=check_type,
        name=name,
        model=model,
        field=field,
        metric=MetricType.MISSING_COUNT,
        threshold=threshold,
        threshold_is_percent=threshold_is_percent,
        severity=severity,
        dimension=dimension,
        missing_values=missing_values,
    )


def _duplicate_count_check(
    model, field, check_type, threshold, name, category="quality", severity=None, dimension=None
) -> CheckSpec:
    return CheckSpec(
        key=f"{model}__{field}__{check_type}",
        category=category,
        type=check_type,
        name=name,
        model=model,
        field=field,
        metric=MetricType.DUPLICATE_COUNT,
        threshold=threshold,
        severity=severity,
        dimension=dimension,
        columns=[field],
    )


def _invalid_count_check(
    model,
    field,
    check_type,
    name,
    threshold=None,
    category="schema",
    threshold_is_percent=False,
    severity=None,
    dimension=None,
    **kwargs,
) -> CheckSpec:
    return CheckSpec(
        key=f"{model}__{field}__{check_type}",
        category=category,
        type=check_type,
        name=name,
        model=model,
        field=field,
        metric=MetricType.INVALID_COUNT,
        threshold=threshold or Threshold(Op.EQ, 0),
        threshold_is_percent=threshold_is_percent,
        severity=severity,
        dimension=dimension,
        **kwargs,
    )


def _row_count_check(model, threshold: Threshold, severity=None, dimension=None) -> CheckSpec:
    return CheckSpec(
        key=f"{model}__row_count",
        category="quality",
        type="row_count",
        name=f"Check that model {model} has row_count {threshold.describe()}",
        model=model,
        field=None,
        metric=MetricType.ROW_COUNT,
        threshold=threshold,
        severity=severity,
        dimension=dimension,
    )


# ---------------------------------------------------------------------------
# quality list
# ---------------------------------------------------------------------------
def _quality_checks(
    model: str, field: Optional[str], quality_list: List[DataQuality], server: Optional[Server]
) -> List[CheckSpec]:
    checks: List[CheckSpec] = []
    for count, quality in enumerate(quality_list):
        rule_checks = _quality_rule_checks(model, field, quality, count, server)
        # Every check keeps a link back to the rule that declared it, so that
        # `test --quality-id` / `test --tag` can select it.
        for check in rule_checks:
            check.quality_id = quality.id
            check.tags = list(quality.tags) if quality.tags else None
            check.quality_definition = quality_definition_yaml(quality)
        checks.extend(rule_checks)
    return checks


def _quality_rule_checks(
    model: str, field: Optional[str], quality: DataQuality, count: int, server: Optional[Server]
) -> List[CheckSpec]:
    """The checks of a single ODCS quality rule (``count`` is its index in the list)."""
    if quality.type == "custom" and quality.engine == "soda" and quality.implementation:
        return [
            CheckSpec(
                key=f"{model}__quality_custom_{count}",
                category="quality",
                type="quality_custom_soda",
                name=quality.description or "Custom SodaCL Check",
                model=model,
                field=field,
                metric=MetricType.UNSUPPORTED,
                dimension=quality.dimension,
                preset_result="warning",
                preset_reason=(
                    "Raw SodaCL custom checks (quality.type: custom, engine: soda) are no longer "
                    "supported since soda-core was removed. Migrate this check to quality.type: sql."
                ),
            )
        ]
    if quality.type == "sql":
        if field is None:
            check_key = f"{model}__quality_sql_{count}"
            check_type = "model_quality_sql"
        else:
            check_key = f"{model}__{field}__quality_sql_{count}"
            check_type = "field_quality_sql"
        threshold = to_threshold(quality)
        query = prepare_query(quality, model, field, server)
        if query is None:
            logger.warning(f"Quality check {check_key} has no query")
            return []
        if threshold is None:
            logger.warning(f"Quality check {check_key} has no valid threshold")
            return []

        def not_executed(reason: str) -> List[CheckSpec]:
            return [
                CheckSpec(
                    key=check_key,
                    category="quality",
                    type=check_type,
                    name=quality.description or "Quality Check",
                    model=model,
                    field=field,
                    metric=MetricType.UNSUPPORTED,
                    dimension=quality.dimension,
                    severity=quality.severity,
                    preset_result="failed",
                    preset_reason=reason,
                )
            ]

        # ``${VAR}`` references (ODCS v3.2.0) resolve from the environment now that
        # the query is about to be used; the CLI's own ``${model}``-style placeholders
        # were substituted first, so they are not mistaken for variables. The
        # contract keeps the references.
        try:
            query = resolve_variables(query, source=f"the query of quality check '{check_key}'")
        except UnresolvedVariableError as e:
            return not_executed(f"{e} Set it in the environment or a .env file, or use ${{{e.name}:-default}}.")
        # The query is read as the dialect of the server it runs against, so
        # dialect-specific syntax is not mistaken for something that is not a query.
        parse_dialect = dialect_for_server_type(get_server_type(server))
        if not is_read_only_query(query, parse_dialect):
            return not_executed(
                f"A quality rule query must be a single read-only query, and this one could "
                f"not be read as one{f' ({parse_dialect} SQL)' if parse_dialect else ''}, "
                f"so it was not executed."
            )
        return [
            CheckSpec(
                key=check_key,
                category="quality",
                type=check_type,
                name=quality.description or "Quality Check",
                model=model,
                field=field,
                metric=MetricType.CUSTOM_SQL,
                threshold=threshold,
                query=query,
                severity=quality.severity,
                dimension=quality.dimension,
            )
        ]
    if quality.metric is not None:
        threshold = to_threshold(quality)
        if threshold is None:
            logger.warning(f"Quality metric {quality.metric} has no valid threshold")
            return []
        return _quality_metric_check(model, field, quality, threshold)
    return []


def _quality_metric_check(model, field, quality: DataQuality, threshold: Threshold) -> List[CheckSpec]:
    metric = quality.metric
    severity = quality.severity
    dimension = quality.dimension
    is_percent = is_percent_unit(quality)

    # Percent thresholds only make sense for the count-of-bad-rows metrics, where
    # the engine can divide by the model row count. Warn (and fall back to an
    # absolute comparison) rather than silently comparing a count to a percent.
    if is_percent and metric not in ("nullValues", "missingValues", "invalidValues"):
        logger.warning(f"Quality metric {metric} does not support unit: percent; comparing absolute count")
        is_percent = False

    if metric == "rowCount":
        return [_row_count_check(model, threshold, severity=severity, dimension=dimension)]
    if metric == "duplicateValues":
        if field is None:
            cols = quality.arguments.get("properties") if quality.arguments else None
            col_joined = ", ".join(cols or [])
            return [
                CheckSpec(
                    key=f"{model}__model_duplicate_values",
                    category="quality",
                    type="model_duplicate_values",
                    name=f"Check that model {model} has duplicate_count {threshold.describe()} for columns {col_joined}",
                    model=model,
                    field=None,
                    metric=MetricType.DUPLICATE_COUNT,
                    threshold=threshold,
                    columns=cols,
                    severity=severity,
                    dimension=dimension,
                )
            ]
        return [
            _duplicate_count_check(
                model,
                field,
                "field_duplicate_values",
                threshold,
                name=f"Check that field {field} has duplicate_count {threshold.describe()}",
                severity=severity,
                dimension=dimension,
            )
        ]
    if metric == "nullValues":
        if field is None:
            logger.warning("Quality check nullValues is only supported at field level")
            return []
        return [
            _missing_count_check(
                model,
                field,
                "field_null_values",
                threshold,
                name=f"Check that field {field} has missing_count {threshold.describe()}",
                threshold_is_percent=is_percent,
                severity=severity,
                dimension=dimension,
            )
        ]
    if metric == "invalidValues":
        if field is None:
            logger.warning("Quality check invalidValues is only supported at field level")
            return []
        args = quality.arguments or {}
        valid_values = args.get("validValues")
        pattern = args.get("pattern")
        if valid_values is None and pattern is None:
            logger.warning(
                f"Quality check invalidValues on field {field} has no validValues or pattern argument; skipping"
            )
            return []
        return [
            _invalid_count_check(
                model,
                field,
                "field_invalid_values",
                name=f"Check that field {field} has invalid_count {threshold.describe()}",
                threshold=threshold,
                category="quality",
                valid_values=valid_values,
                valid_regex=pattern,
                threshold_is_percent=is_percent,
                severity=severity,
                dimension=dimension,
            )
        ]
    if metric == "missingValues":
        if field is None:
            logger.warning("Quality check missingValues is only supported at field level")
            return []
        missing_values = quality.arguments.get("missingValues") if quality.arguments else None
        if missing_values is not None:
            missing_values = [v for v in missing_values if v is not None]
        return [
            _missing_count_check(
                model,
                field,
                "field_missing_values",
                threshold,
                name=f"Check that field {field} has missing_count {threshold.describe()}",
                missing_values=missing_values or None,
                threshold_is_percent=is_percent,
                severity=severity,
                dimension=dimension,
            )
        ]
    logger.warning(f"Quality check {metric} is not yet supported")
    return []


# ---------------------------------------------------------------------------
# service levels (freshness / retention)
# ---------------------------------------------------------------------------
def _get_schema_by_name(data_contract: OpenDataContractStandard, name: str) -> Optional[SchemaObject]:
    if data_contract.schema_ is None:
        return None
    return next((s for s in data_contract.schema_ if s.name == name), None)


def _to_servicelevel_checks(data_contract: OpenDataContractStandard, server: Optional[Server]) -> List[CheckSpec]:
    checks: List[CheckSpec] = []
    if data_contract.slaProperties is None:
        return checks
    for sla in data_contract.slaProperties:
        if sla.property == "freshness":
            check = _freshness_check(data_contract, sla, server)
            if check is not None:
                checks.append(check)
        elif sla.property == "retention":
            check = _retention_check(data_contract, sla, server)
            if check is not None:
                checks.append(check)
    return checks


def _split_element(element: Optional[str]) -> Optional[tuple[str, str]]:
    if element is None or "." not in element or element.count(".") > 1:
        return None
    model, field = element.split(".")
    return model, field


def _resolve_sla_element(
    data_contract: OpenDataContractStandard, element: Optional[str], server: Optional[Server]
) -> Optional[tuple[str, str]]:
    """The (model, field) a contract-language sla element points at, in warehouse terms."""
    parts = _split_element(element)
    if parts is None:
        logger.info(f"sla element {element!r} is not a single model.field, skipping")
        return None
    model, field = parts
    schema_object = _get_schema_by_name(data_contract, model)
    if schema_object is None:
        return None
    server_type = server.type if server and server.type else None
    prop = next((p for p in schema_object.properties or [] if p.name == field), None)
    if prop is not None and prop.physicalName:
        field = prop.physicalName
    return to_schema_name(schema_object, server_type), field


def _freshness_check(
    data_contract: OpenDataContractStandard, sla, server: Optional[Server] = None
) -> Optional[CheckSpec]:
    if sla.element is None or sla.value is None:
        return None
    resolved = _resolve_sla_element(data_contract, sla.element, server)
    if resolved is None:
        return None
    model, field = resolved

    unit = (sla.unit or "d").lower()
    if unit in ("d", "day", "days"):
        seconds = int(sla.value) * 86400
    elif unit in ("h", "hr", "hour", "hours"):
        seconds = int(sla.value) * 3600
    elif unit in ("m", "min", "minute", "minutes"):
        seconds = int(sla.value) * 60
    else:
        logger.info(f"Unsupported freshness unit {unit}")
        return None

    return CheckSpec(
        key=f"{model}__{field}__servicelevel_freshness",
        category="servicelevel",
        type="servicelevel_freshness",
        name=f"Freshness of {model}.{field} < {sla.value}{unit[0]}",
        model=model,
        field=field,
        metric=MetricType.FRESHNESS,
        quality_id=sla.id,
        seconds=seconds,
    )


def _retention_check(
    data_contract: OpenDataContractStandard, sla, server: Optional[Server] = None
) -> Optional[CheckSpec]:
    if sla.element is None or sla.value is None:
        return None
    resolved = _resolve_sla_element(data_contract, sla.element, server)
    if resolved is None:
        return None
    model, field = resolved
    seconds = _retention_value_to_seconds(sla.value, sla.unit)
    if seconds is None:
        return None
    return CheckSpec(
        key=f"{model}__{field}__servicelevel_retention",
        category="servicelevel",
        type="servicelevel_retention",
        name=f"Retention of {model}.{field} < {seconds}s",
        model=model,
        field=field,
        metric=MetricType.RETENTION,
        quality_id=sla.id,
        seconds=seconds,
    )


def _retention_value_to_seconds(value, unit: Optional[str]) -> Optional[int]:
    if value is None:
        return None
    if isinstance(value, (int, float)):
        n = int(value)
        u = (unit or "d").lower()
        if u in ("y", "yr", "year", "years"):
            return n * 365 * 86400
        if u in ("m", "mo", "month", "months"):
            return n * 30 * 86400
        if u in ("d", "day", "days"):
            return n * 86400
        if u in ("h", "hr", "hour", "hours"):
            return n * 3600
        if u in ("min", "minute", "minutes"):
            return n * 60
        if u in ("s", "sec", "second", "seconds"):
            return n
        logger.info(f"Unsupported retention unit: {unit}")
        return None
    if isinstance(value, str):
        return _parse_iso8601_to_seconds(value)
    return None


# P followed by number-unit combinations (e.g. P1Y2M3W4DT5H6M7S), every component optional, but at least one required
_ISO8601_DURATION = re.compile(
    r"P(?=\d|T\d)"
    r"(?:(\d+(?:\.\d+)?)Y)?"
    r"(?:(\d+(?:\.\d+)?)M)?"
    r"(?:(\d+(?:\.\d+)?)W)?"
    r"(?:(\d+(?:\.\d+)?)D)?"
    r"(?:T(?=\d)"
    r"(?:(\d+(?:\.\d+)?)H)?"
    r"(?:(\d+(?:\.\d+)?)M)?"
    r"(?:(\d+(?:\.\d+)?)S)?)?"
)
_COMPONENT_SECONDS = (365 * 86400, 30 * 86400, 7 * 86400, 86400, 3600, 60, 1)


def _parse_iso8601_to_seconds(duration: str) -> Optional[int]:
    if not duration:
        return None
    match = _ISO8601_DURATION.fullmatch(duration.upper())
    if match is None:
        logger.info(f"Unsupported retention period: {duration}")
        return None
    return round(sum(float(amount) * seconds for amount, seconds in zip(match.groups(), _COMPONENT_SECONDS) if amount))
