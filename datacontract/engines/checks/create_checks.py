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

from open_data_contract_standard.model import (
    DataQuality,
    OpenDataContractStandard,
    SchemaObject,
    SchemaProperty,
    Server,
)

from datacontract.engines.checks.check_spec import CheckSpec, MetricType, Op, Threshold
from datacontract.engines.checks.type_normalize import normalize_type_name
from datacontract.model.server import get_server_type

logger = logging.getLogger(__name__)

_FILE_SERVER_TYPES = {"local", "s3", "gcs", "azure"}
_VERIFIED_NESTED_SQL_SERVER_TYPES = {"dataframe", "databricks"}
_SUPPORTED_NESTED_STRUCT_SERVER_TYPES = {"dataframe", "databricks"}
_SUPPORTED_NESTED_ARRAY_SERVER_TYPES = {"dataframe", "databricks"}


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
    # Kafka uses the Spark SQL view name (the logical name), not the topic (physicalName).
    if server_type == "kafka":
        return schema_object.name
    if schema_object.physicalName:
        return schema_object.physicalName
    return schema_object.name


def expected_type_category(prop: SchemaProperty) -> tuple[str, str]:
    """Return (normalized category, human label) for a property's declared type."""
    label = prop.physicalType or prop.logicalType
    return normalize_type_name(label), (label or "")


def _property_type(prop: SchemaProperty) -> str:
    return normalize_type_name(prop.physicalType or prop.logicalType)


def _iter_property_paths(
    model: str,
    properties: list[SchemaProperty] | None,
    server_type: str | None,
    prefix: str | None = None,
    nested: bool = False,
):
    for prop in properties or []:
        field = prop.physicalName or prop.name
        field_path = f"{prefix}.{field}" if prefix else field
        yield model, field_path, prop, nested

        prop_type = _property_type(prop)
        if (
            server_type in _SUPPORTED_NESTED_STRUCT_SERVER_TYPES
            and prop_type in {"object", "record", "struct"}
            and prop.properties
        ):
            yield from _iter_property_paths(model, prop.properties, server_type, field_path, True)
        elif (
            server_type in _SUPPORTED_NESTED_ARRAY_SERVER_TYPES
            and prop_type == "array"
            and prop.items
            and prop.items.properties
        ):
            nested_model = f"{model}__{field}"
            yield from _iter_property_paths(nested_model, prop.items.properties, server_type, None, True)


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
        checks.extend(_to_schema_checks(schema_obj, server))
    checks.extend(_to_servicelevel_checks(data_contract, server))
    return [c for c in checks if c is not None]


def _to_schema_checks(schema_object: SchemaObject, server: Optional[Server]) -> List[CheckSpec]:
    checks: List[CheckSpec] = []
    server_type = get_server_type(server) if server is not None else None
    model = to_schema_name(schema_object, server_type)
    properties = schema_object.properties or []
    check_types = is_check_types(server)
    uses_raw_view = (
        server is not None and server_type in _FILE_SERVER_TYPES and server.format in ("csv", "parquet", "json")
    )

    for item_model, field, prop, is_nested in _iter_property_paths(model, properties, server_type):
        # ODCS physicalName is the real column; mirror to_schema_name at field level.

        checks.append(
            CheckSpec(
                key=f"{item_model}__{field}__field_is_present",
                category="schema",
                type="field_is_present",
                name=f"Check that field '{field}' is present",
                model=item_model,
                field=field,
                metric=MetricType.FIELD_PRESENT,
                uses_raw_view=uses_raw_view,
            )
        )

        if check_types and (prop.physicalType is not None or prop.logicalType is not None):
            category, label = expected_type_category(prop)
            checks.append(
                CheckSpec(
                    key=f"{item_model}__{field}__field_type",
                    category="schema",
                    type="field_type",
                    name=f"Check that field {field} has type {label}",
                    model=item_model,
                    field=field,
                    metric=MetricType.FIELD_TYPE,
                    expected_category=category,
                    expected_type_label=label,
                )
            )

        if prop.required:
            checks.append(
                _missing_count_check(
                    item_model,
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
                    item_model,
                    field,
                    "field_unique",
                    Threshold(Op.EQ, 0),
                    name=f"Check that unique field {field} has no duplicate values",
                    category="schema",
                )
            )

        min_length = _get_logical_type_option(prop, "minLength")
        if min_length is not None:
            checks.append(
                _invalid_count_check(
                    item_model,
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
                    item_model,
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
                    item_model,
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
                    item_model,
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
                    item_model,
                    field,
                    "field_minimum",
                    name=f"Check that field {field} has a minimum of {exclusive_minimum}",
                    valid_min=exclusive_minimum,
                )
            )
            checks.append(
                _invalid_count_check(
                    item_model,
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
                    item_model,
                    field,
                    "field_maximum",
                    name=f"Check that field {field} has a maximum of {exclusive_maximum}",
                    valid_max=exclusive_maximum,
                )
            )
            checks.append(
                _invalid_count_check(
                    item_model,
                    field,
                    "field_not_equal",
                    name=f"Check that field {field} is not equal to {exclusive_maximum}",
                    invalid_values=[exclusive_maximum],
                )
            )

        pattern = _get_logical_type_option(prop, "pattern")
        if pattern is not None:
            checks.append(
                _invalid_count_check(
                    item_model,
                    field,
                    "field_regex",
                    name=f"Check that field {field} matches regex pattern {pattern}",
                    valid_regex=pattern,
                )
            )

        enum_values = _get_logical_type_option(prop, "enum")
        if enum_values:
            checks.append(
                _invalid_count_check(
                    item_model,
                    field,
                    "field_enum",
                    name=f"Check that field {field} only contains enum values {enum_values}",
                    valid_values=list(enum_values),
                )
            )

        if prop.quality:
            checks.extend(_quality_checks(item_model, field, prop.quality, server, is_nested=is_nested))

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
        missing_values=missing_values,
    )


def _duplicate_count_check(model, field, check_type, threshold, name, category="quality", severity=None) -> CheckSpec:
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
        **kwargs,
    )


def _row_count_check(model, threshold: Threshold, severity=None) -> CheckSpec:
    return CheckSpec(
        key=f"{model}__row_count",
        category="schema",
        type="row_count",
        name=f"Check that model {model} has row_count {threshold.describe()}",
        model=model,
        field=None,
        metric=MetricType.ROW_COUNT,
        threshold=threshold,
        severity=severity,
    )


# ---------------------------------------------------------------------------
# quality list
# ---------------------------------------------------------------------------
def _quality_checks(
    model: str, field: Optional[str], quality_list: List[DataQuality], server: Optional[Server], is_nested: bool = False
) -> List[CheckSpec]:
    checks: List[CheckSpec] = []
    count = 0
    for quality in quality_list:
        if quality.type == "custom" and quality.engine == "soda" and quality.implementation:
            checks.append(
                CheckSpec(
                    key=f"{model}__quality_custom_{count}",
                    category="quality",
                    type="quality_custom_soda",
                    name=quality.description or "Custom SodaCL Check",
                    model=model,
                    field=field,
                    metric=MetricType.UNSUPPORTED,
                    preset_result="warning",
                    preset_reason=(
                        "Raw SodaCL custom checks (quality.type: custom, engine: soda) are no longer "
                        "supported since soda-core was removed. Migrate this check to quality.type: sql."
                    ),
                )
            )
        elif quality.type == "sql":
            server_type = get_server_type(server) if server is not None else None
            if is_nested and server_type not in _VERIFIED_NESTED_SQL_SERVER_TYPES:
                if field is None:
                    check_key = f"{model}__quality_sql_{count}"
                    check_type = "model_quality_sql"
                else:
                    check_key = f"{model}__{field}__quality_sql_{count}"
                    check_type = "field_quality_sql"
                checks.append(
                    CheckSpec(
                        key=check_key,
                        category="quality",
                        type=check_type,
                        name=quality.description or "Quality Check",
                        model=model,
                        field=field,
                        metric=MetricType.UNSUPPORTED,
                        preset_result="warning",
                        preset_reason=(
                            "Nested SQL quality checks are only verified for Spark (dataframe) and Databricks."
                        ),
                    )
                )
                count += 1
                continue
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
                count += 1
                continue
            if threshold is None:
                logger.warning(f"Quality check {check_key} has no valid threshold")
                count += 1
                continue
            checks.append(
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
                    dialect=getattr(quality, "dialect", None),
                    severity=quality.severity,
                )
            )
        elif quality.metric is not None:
            threshold = to_threshold(quality)
            if threshold is None:
                logger.warning(f"Quality metric {quality.metric} has no valid threshold")
                count += 1
                continue
            checks.extend(_quality_metric_check(model, field, quality, threshold))
        count += 1
    return checks


def _quality_metric_check(model, field, quality: DataQuality, threshold: Threshold) -> List[CheckSpec]:
    metric = quality.metric
    severity = quality.severity
    is_percent = is_percent_unit(quality)

    # Percent thresholds only make sense for the count-of-bad-rows metrics, where
    # the engine can divide by the model row count. Warn (and fall back to an
    # absolute comparison) rather than silently comparing a count to a percent.
    if is_percent and metric not in ("nullValues", "missingValues", "invalidValues"):
        logger.warning(f"Quality metric {metric} does not support unit: percent; comparing absolute count")
        is_percent = False

    if metric == "rowCount":
        return [_row_count_check(model, threshold, severity=severity)]
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
            )
        ]
    if metric == "invalidValues":
        if field is None:
            logger.warning("Quality check invalidValues is only supported at field level")
            return []
        valid_values = quality.arguments.get("validValues") if quality.arguments else None
        return [
            _invalid_count_check(
                model,
                field,
                "field_invalid_values",
                name=f"Check that field {field} has invalid_count {threshold.describe()}",
                threshold=threshold,
                category="quality",
                valid_values=valid_values,
                threshold_is_percent=is_percent,
                severity=severity,
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
            check = _freshness_check(data_contract, sla)
            if check is not None:
                checks.append(check)
        elif sla.property == "retention":
            check = _retention_check(data_contract, sla)
            if check is not None:
                checks.append(check)
    return checks


def _split_element(element: Optional[str]) -> Optional[tuple[str, str]]:
    if element is None or "." not in element or element.count(".") > 1:
        return None
    model, field = element.split(".")
    return model, field


def _freshness_check(data_contract: OpenDataContractStandard, sla) -> Optional[CheckSpec]:
    if sla.element is None or sla.value is None:
        return None
    parts = _split_element(sla.element)
    if parts is None:
        logger.info("freshness element is not a single model.field, skipping")
        return None
    model, field = parts
    if _get_schema_by_name(data_contract, model) is None:
        return None

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
        key="servicelevel_freshness",
        category="servicelevel",
        type="servicelevel_freshness",
        name=f"Freshness of {model}.{field} < {sla.value}{unit[0]}",
        model=model,
        field=field,
        metric=MetricType.FRESHNESS,
        seconds=seconds,
    )


def _retention_check(data_contract: OpenDataContractStandard, sla) -> Optional[CheckSpec]:
    if sla.element is None or sla.value is None:
        return None
    parts = _split_element(sla.element)
    if parts is None:
        logger.info("retention element is not a single model.field, skipping")
        return None
    model, field = parts
    if _get_schema_by_name(data_contract, model) is None:
        return None
    seconds = _retention_value_to_seconds(sla.value, sla.unit)
    if seconds is None:
        return None
    return CheckSpec(
        key="servicelevel_retention",
        category="servicelevel",
        type="servicelevel_retention",
        name=f"Retention of {model}.{field} < {seconds}s",
        model=model,
        field=field,
        metric=MetricType.RETENTION,
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


def _parse_iso8601_to_seconds(duration: str) -> Optional[int]:
    if not duration:
        return None
    duration = duration.upper()
    for pat, mult in (
        (r"P(\d+)Y", 365 * 86400),
        (r"P(\d+)M", 30 * 86400),
        (r"P(\d+)D", 86400),
        (r"PT(\d+)H", 3600),
        (r"PT(\d+)M", 60),
        (r"PT(\d+)S", 1),
    ):
        m = re.match(pat, duration)
        if m:
            return int(m.group(1)) * mult
    return None
