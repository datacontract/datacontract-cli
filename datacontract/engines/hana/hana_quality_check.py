import re
import uuid
from typing import Any

from open_data_contract_standard.model import DataQuality, OpenDataContractStandard, SchemaObject

from datacontract.engines.data_contract_checks import _retention_value_to_seconds, to_sodacl_threshold
from datacontract.engines.hana.hana_schema_check import qualified_table_name, quote_identifier
from datacontract.model.run import Check, ResultEnum


def run_quality_checks(connection, schema_name: str, schema_object: SchemaObject) -> list[Check]:
    table_name = schema_object.physicalName or schema_object.name
    checks: list[Check] = []

    for prop in schema_object.properties or []:
        field_name = prop.physicalName or prop.name
        for index, quality in enumerate(prop.quality or []):
            check = _quality_check(connection, schema_name, table_name, field_name, quality, index)
            if check is not None:
                checks.append(check)

    for index, quality in enumerate(schema_object.quality or []):
        check = _quality_check(connection, schema_name, table_name, None, quality, index)
        if check is not None:
            checks.append(check)

    return checks


def run_sla_checks(
    connection, schema_name: str, data_contract: OpenDataContractStandard, schema_filter: str = "all"
) -> list[Check]:
    checks: list[Check] = []
    for sla in data_contract.slaProperties or []:
        if sla.property not in ("freshness", "retention"):
            continue
        resolved = _resolve_sla_element(data_contract, sla.element)
        if resolved is None:
            continue
        schema_object, field_name = resolved
        if schema_filter != "all" and schema_object.name != schema_filter:
            continue
        table_name = schema_object.physicalName or schema_object.name
        if sla.property == "freshness":
            check = _freshness_check(connection, schema_name, table_name, field_name, sla)
        else:
            check = _retention_check(connection, schema_name, table_name, field_name, sla)
        if check is not None:
            checks.append(check)
    return checks


def prepare_hana_query(query: str, schema_name: str, model_name: str, field_name: str | None = None) -> str | None:
    if query is None or query == "":
        return None

    qualified_model_name = qualified_table_name(schema_name, model_name)
    quoted_schema_name = quote_identifier(schema_name)
    query = re.sub(r'["\']?\$?\{model}["\']?', qualified_model_name, query)
    query = re.sub(r'["\']?\$?\{table}["\']?', qualified_model_name, query)
    query = re.sub(r'["\']?\$?\{object}["\']?', qualified_model_name, query)
    query = re.sub(r'["\']?\$?\{schema}["\']?', quoted_schema_name, query)

    if field_name is not None:
        quoted_field_name = quote_identifier(field_name)
        query = re.sub(r'["\']?\$?\{field}["\']?', quoted_field_name, query)
        query = re.sub(r'["\']?\$?\{column}["\']?', quoted_field_name, query)
        query = re.sub(r'["\']?\$?\{property}["\']?', quoted_field_name, query)

    return query


def _quality_check(
    connection, schema_name: str, table_name: str, field_name: str | None, quality: DataQuality, index: int
) -> Check | None:
    if quality.type == "custom" and quality.engine == "soda":
        return _check(
            check_type="quality_custom_soda",
            key=_quality_key(table_name, field_name, f"quality_custom_soda_{index}"),
            name=quality.description or "Custom SodaCL Check",
            model=table_name,
            field=field_name,
            implementation=quality.implementation,
            result=ResultEnum.warning,
            reason="SodaCL quality checks are not supported for HANA. Use type: sql instead.",
        )

    if quality.type == "sql":
        return _sql_quality_check(connection, schema_name, table_name, field_name, quality, index)

    if quality.metric == "rowCount":
        sql = f"SELECT COUNT(*) FROM {qualified_table_name(schema_name, table_name)}"
        return _metric_quality_check(
            connection,
            quality,
            check_type="row_count",
            key=f"{table_name}__row_count",
            name="Check row count",
            model=table_name,
            field=None,
            sql=sql,
        )

    if quality.metric == "duplicateValues":
        if field_name is not None:
            sql = (
                f"SELECT COUNT(*) - COUNT(DISTINCT {quote_identifier(field_name)}) "
                f"FROM {qualified_table_name(schema_name, table_name)}"
            )
            return _metric_quality_check(
                connection,
                quality,
                check_type="field_duplicate_values",
                key=f"{table_name}__{field_name}__field_duplicate_values",
                name=f"Check duplicate values for field {field_name}",
                model=table_name,
                field=field_name,
                sql=sql,
            )

        properties = _arguments(quality).get("properties")
        if not properties:
            return _warning_check(
                check_type="model_duplicate_values",
                key=f"{table_name}__model_duplicate_values",
                name="Check duplicate values for model",
                model=table_name,
                field=None,
                reason="duplicateValues requires arguments.properties at model level.",
            )
        quoted_properties = ", ".join(quote_identifier(prop) for prop in properties)
        sql = (
            f"SELECT COUNT(*) - COUNT(DISTINCT {quoted_properties}) "
            f"FROM {qualified_table_name(schema_name, table_name)}"
        )
        return _metric_quality_check(
            connection,
            quality,
            check_type="model_duplicate_values",
            key=f"{table_name}__model_duplicate_values",
            name="Check duplicate values for model",
            model=table_name,
            field=None,
            sql=sql,
        )

    if quality.metric == "nullValues" and field_name is not None:
        sql = (
            f"SELECT COUNT(*) FROM {qualified_table_name(schema_name, table_name)} "
            f"WHERE {quote_identifier(field_name)} IS NULL"
        )
        return _metric_quality_check(
            connection,
            quality,
            check_type="field_null_values",
            key=f"{table_name}__{field_name}__field_null_values",
            name=f"Check null values for field {field_name}",
            model=table_name,
            field=field_name,
            sql=sql,
        )

    if quality.metric == "invalidValues" and field_name is not None:
        valid_values = _arguments(quality).get("validValues")
        if not valid_values:
            return _warning_check(
                check_type="field_invalid_values",
                key=f"{table_name}__{field_name}__field_invalid_values",
                name=f"Check invalid values for field {field_name}",
                model=table_name,
                field=field_name,
                reason="invalidValues requires arguments.validValues at field level.",
            )
        placeholders = ", ".join("?" for _ in valid_values)
        sql = (
            f"SELECT COUNT(*) FROM {qualified_table_name(schema_name, table_name)} "
            f"WHERE {quote_identifier(field_name)} NOT IN ({placeholders})"
        )
        return _metric_quality_check(
            connection,
            quality,
            check_type="field_invalid_values",
            key=f"{table_name}__{field_name}__field_invalid_values",
            name=f"Check invalid values for field {field_name}",
            model=table_name,
            field=field_name,
            sql=sql,
            params=valid_values,
        )

    if quality.metric == "missingValues" and field_name is not None:
        missing_values = [value for value in (_arguments(quality).get("missingValues") or []) if value is not None]
        if missing_values:
            placeholders = ", ".join("?" for _ in missing_values)
            missing_predicate = f" OR {quote_identifier(field_name)} IN ({placeholders})"
        else:
            missing_predicate = ""
        sql = (
            f"SELECT COUNT(*) FROM {qualified_table_name(schema_name, table_name)} "
            f"WHERE {quote_identifier(field_name)} IS NULL{missing_predicate}"
        )
        return _metric_quality_check(
            connection,
            quality,
            check_type="field_missing_values",
            key=f"{table_name}__{field_name}__field_missing_values",
            name=f"Check missing values for field {field_name}",
            model=table_name,
            field=field_name,
            sql=sql,
            params=missing_values,
        )

    return None


def _sql_quality_check(
    connection, schema_name: str, table_name: str, field_name: str | None, quality: DataQuality, index: int
) -> Check | None:
    query = prepare_hana_query(quality.query, schema_name, table_name, field_name)
    if query is None:
        return None
    check_type = "field_quality_sql" if field_name is not None else "model_quality_sql"
    return _metric_quality_check(
        connection,
        quality,
        check_type=check_type,
        key=_quality_key(table_name, field_name, f"quality_sql_{index}"),
        name=quality.description or "Quality Check",
        model=table_name,
        field=field_name,
        sql=query,
    )


def _metric_quality_check(
    connection,
    quality: DataQuality,
    *,
    check_type: str,
    key: str,
    name: str,
    model: str,
    field: str | None,
    sql: str,
    params: list[Any] | None = None,
) -> Check | None:
    threshold = to_sodacl_threshold(quality)
    if threshold is None:
        return None

    try:
        value = _fetch_scalar(connection, sql, params or [])
    except Exception as e:
        return _check(
            check_type=check_type,
            key=key,
            name=name,
            model=model,
            field=field,
            implementation=sql,
            result=ResultEnum.error,
            reason=str(e),
        )

    passed = _evaluate_threshold(value, quality)
    return _check(
        check_type=check_type,
        key=key,
        name=name,
        model=model,
        field=field,
        implementation=sql,
        result=ResultEnum.passed if passed else ResultEnum.failed,
        reason=None if passed else f"Actual value {value} does not satisfy threshold {threshold}.",
        diagnostics={"value": value, "threshold": threshold},
    )


def _freshness_check(connection, schema_name: str, table_name: str, field_name: str, sla) -> Check | None:
    threshold = _freshness_value_to_seconds(sla.value, sla.unit)
    if threshold is None:
        return None
    sql = (
        f"SELECT SECONDS_BETWEEN(MAX({quote_identifier(field_name)}), CURRENT_TIMESTAMP) "
        f"FROM {qualified_table_name(schema_name, table_name)}"
    )
    return _servicelevel_check(
        connection,
        check_type="servicelevel_freshness",
        key="servicelevel_freshness",
        name=f"Freshness of {table_name}.{field_name} < {threshold}s",
        model=table_name,
        field=field_name,
        sql=sql,
        threshold=threshold,
    )


def _retention_check(connection, schema_name: str, table_name: str, field_name: str, sla) -> Check | None:
    threshold = _retention_value_to_seconds(sla.value, sla.unit)
    if threshold is None:
        return None
    sql = (
        f"SELECT SECONDS_BETWEEN(MIN({quote_identifier(field_name)}), CURRENT_TIMESTAMP) "
        f"FROM {qualified_table_name(schema_name, table_name)}"
    )
    return _servicelevel_check(
        connection,
        check_type="servicelevel_retention",
        key="servicelevel_retention",
        name=f"Retention of {table_name}.{field_name} < {threshold}s",
        model=table_name,
        field=field_name,
        sql=sql,
        threshold=threshold,
    )


def _servicelevel_check(
    connection,
    *,
    check_type: str,
    key: str,
    name: str,
    model: str,
    field: str,
    sql: str,
    threshold: int,
) -> Check:
    try:
        value = _fetch_scalar(connection, sql, [])
    except Exception as e:
        return _check(
            check_type=check_type,
            key=key,
            name=name,
            model=model,
            field=field,
            implementation=sql,
            result=ResultEnum.error,
            reason=str(e),
            category="servicelevel",
        )
    passed = value is not None and value < threshold
    return _check(
        check_type=check_type,
        key=key,
        name=name,
        model=model,
        field=field,
        implementation=sql,
        result=ResultEnum.passed if passed else ResultEnum.failed,
        reason=None if passed else f"Actual value {value} seconds is not less than {threshold} seconds.",
        diagnostics={"value": value, "threshold": threshold},
        category="servicelevel",
    )


def _evaluate_threshold(value: Any, quality: DataQuality) -> bool:
    if quality.mustBe is not None:
        return value == quality.mustBe
    if quality.mustNotBe is not None:
        return value != quality.mustNotBe
    if quality.mustBeGreaterThan is not None:
        return value > quality.mustBeGreaterThan
    if quality.mustBeGreaterOrEqualTo is not None:
        return value >= quality.mustBeGreaterOrEqualTo
    if quality.mustBeLessThan is not None:
        return value < quality.mustBeLessThan
    if quality.mustBeLessOrEqualTo is not None:
        return value <= quality.mustBeLessOrEqualTo
    if quality.mustBeBetween is not None:
        return quality.mustBeBetween[0] <= value <= quality.mustBeBetween[1]
    if quality.mustNotBeBetween is not None:
        return value < quality.mustNotBeBetween[0] or value > quality.mustNotBeBetween[1]
    return False


def _freshness_value_to_seconds(value, unit: str | None) -> int | None:
    if value is None:
        return None
    numeric_value = int(value)
    unit_lower = unit.lower() if unit else "d"
    if unit_lower in ("d", "day", "days"):
        return numeric_value * 24 * 60 * 60
    if unit_lower in ("h", "hr", "hour", "hours"):
        return numeric_value * 60 * 60
    if unit_lower in ("m", "min", "minute", "minutes"):
        return numeric_value * 60
    if unit_lower in ("s", "sec", "second", "seconds"):
        return numeric_value
    return None


def _resolve_sla_element(data_contract: OpenDataContractStandard, element: str | None):
    if element is None or element.count(".") != 1:
        return None
    model_name, field_name = element.split(".")
    for schema_object in data_contract.schema_ or []:
        if schema_object.name != model_name:
            continue
        for prop in schema_object.properties or []:
            if prop.name == field_name:
                return schema_object, prop.physicalName or prop.name
    return None


def _quality_key(table_name: str, field_name: str | None, suffix: str) -> str:
    if field_name is None:
        return f"{table_name}__{suffix}"
    return f"{table_name}__{field_name}__{suffix}"


def _arguments(quality: DataQuality) -> dict:
    return quality.arguments or {}


def _warning_check(*, check_type: str, key: str, name: str, model: str, field: str | None, reason: str) -> Check:
    return _check(
        check_type=check_type,
        key=key,
        name=name,
        model=model,
        field=field,
        implementation=None,
        result=ResultEnum.warning,
        reason=reason,
    )


def _check(
    *,
    check_type: str,
    key: str,
    name: str,
    model: str,
    field: str | None,
    implementation: str | None,
    result: ResultEnum,
    reason: str | None,
    diagnostics: dict | None = None,
    category: str = "quality",
) -> Check:
    return Check(
        id=str(uuid.uuid4()),
        key=key,
        category=category,
        type=check_type,
        name=name,
        model=model,
        field=field,
        engine="hana",
        language="sql",
        implementation=implementation,
        result=result,
        reason=reason,
        diagnostics=diagnostics,
    )


def _fetch_scalar(connection, sql: str, params: list[Any] | None = None):
    cursor = connection.cursor()
    try:
        cursor.execute(sql, params or [])
        row = cursor.fetchone()
        if row is None:
            return None
        if isinstance(row, dict):
            return next(iter(row.values()))
        return row[0]
    finally:
        if hasattr(cursor, "close"):
            cursor.close()
