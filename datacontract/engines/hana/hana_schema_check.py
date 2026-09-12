import uuid
from dataclasses import dataclass
from typing import Any

from open_data_contract_standard.model import SchemaObject, SchemaProperty

from datacontract.engines.hana.hana_type_mapping import types_match
from datacontract.model.run import Check, ResultEnum


@dataclass
class ColumnMetadata:
    name: str
    data_type_name: str
    length: int | None
    scale: int | None
    is_nullable: str | None
    position: int | None
    source: str


def quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def qualified_table_name(schema: str, table: str) -> str:
    return f"{quote_identifier(schema)}.{quote_identifier(table)}"


def run_schema_checks(connection, schema_name: str, schema_object: SchemaObject) -> list[Check]:
    table_name = _schema_name(schema_object)
    checks: list[Check] = []
    column_metadata = _get_column_metadata(connection, schema_name, table_name)

    model_exists_check = _result_check(
        check_type="model_exists",
        key=f"{table_name}__model_exists",
        name=f"Check that model {table_name} exists",
        model=table_name,
        field=None,
        implementation="Catalog lookup in SYS.TABLE_COLUMNS and SYS.VIEW_COLUMNS",
        result=ResultEnum.passed if column_metadata else ResultEnum.failed,
        reason=None if column_metadata else f"Model {schema_name}.{table_name} does not exist.",
    )
    checks.append(model_exists_check)
    if not column_metadata:
        return checks

    columns_by_name = {column.name: column for column in column_metadata}
    source = column_metadata[0].source

    for prop in schema_object.properties or []:
        field_name = _property_name(prop)
        column = columns_by_name.get(field_name)
        field_present_check = _result_check(
            check_type="field_is_present",
            key=f"{table_name}__{field_name}__field_is_present",
            name=f"Check that field {field_name} is present",
            model=table_name,
            field=field_name,
            implementation="Catalog lookup in SYS.TABLE_COLUMNS and SYS.VIEW_COLUMNS",
            result=ResultEnum.passed if column else ResultEnum.failed,
            reason=None if column else f"Field {field_name} is missing in {schema_name}.{table_name}.",
        )
        checks.append(field_present_check)
        if column is None:
            continue

        expected_type = prop.physicalType or prop.logicalType
        if expected_type:
            checks.append(_field_type_check(table_name, field_name, expected_type, column))

        if prop.required:
            checks.append(_field_required_check(table_name, field_name, column))

        if prop.unique:
            checks.append(
                _zero_violations_check(
                    connection,
                    check_type="field_unique",
                    table_schema=schema_name,
                    table_name=table_name,
                    field_name=field_name,
                    sql=(
                        f"SELECT COUNT(*) - COUNT(DISTINCT {quote_identifier(field_name)}) "
                        f"FROM {qualified_table_name(schema_name, table_name)}"
                    ),
                    params=None,
                    name=f"Check that unique field {field_name} has no duplicate values",
                    failure_reason="Found {value} duplicate values.",
                )
            )

        if prop.primaryKey:
            checks.append(_primary_key_check(connection, schema_name, table_name, field_name, source))

        checks.extend(_logical_type_option_checks(connection, schema_name, table_name, field_name, prop))

    return checks


def _schema_name(schema_object: SchemaObject) -> str:
    return schema_object.physicalName or schema_object.name


def _property_name(prop: SchemaProperty) -> str:
    return prop.physicalName or prop.name


def _logical_type_option_checks(
    connection, schema_name: str, table_name: str, field_name: str, prop: SchemaProperty
) -> list[Check]:
    checks: list[Check] = []
    options = prop.logicalTypeOptions or {}

    min_length = options.get("minLength")
    if min_length is not None:
        checks.append(
            _zero_violations_check(
                connection,
                check_type="field_min_length",
                table_schema=schema_name,
                table_name=table_name,
                field_name=field_name,
                sql=(
                    f"SELECT COUNT(*) FROM {qualified_table_name(schema_name, table_name)} "
                    f"WHERE LENGTH({quote_identifier(field_name)}) < ?"
                ),
                params=[min_length],
                name=f"Check that field {field_name} has a min length of {min_length}",
                failure_reason=f"Found {{value}} values shorter than {min_length}.",
            )
        )

    max_length = options.get("maxLength")
    if max_length is not None:
        checks.append(
            _zero_violations_check(
                connection,
                check_type="field_max_length",
                table_schema=schema_name,
                table_name=table_name,
                field_name=field_name,
                sql=(
                    f"SELECT COUNT(*) FROM {qualified_table_name(schema_name, table_name)} "
                    f"WHERE LENGTH({quote_identifier(field_name)}) > ?"
                ),
                params=[max_length],
                name=f"Check that field {field_name} has a max length of {max_length}",
                failure_reason=f"Found {{value}} values longer than {max_length}.",
            )
        )

    minimum = options.get("minimum")
    if minimum is not None:
        checks.append(_minimum_check(connection, schema_name, table_name, field_name, minimum))

    maximum = options.get("maximum")
    if maximum is not None:
        checks.append(_maximum_check(connection, schema_name, table_name, field_name, maximum))

    exclusive_minimum = options.get("exclusiveMinimum")
    if exclusive_minimum is not None:
        checks.append(_minimum_check(connection, schema_name, table_name, field_name, exclusive_minimum))
        checks.append(_not_equal_check(connection, schema_name, table_name, field_name, exclusive_minimum))

    exclusive_maximum = options.get("exclusiveMaximum")
    if exclusive_maximum is not None:
        checks.append(_maximum_check(connection, schema_name, table_name, field_name, exclusive_maximum))
        checks.append(_not_equal_check(connection, schema_name, table_name, field_name, exclusive_maximum))

    enum_values = options.get("enum")
    if enum_values is not None and len(enum_values) > 0:
        placeholders = ", ".join("?" for _ in enum_values)
        checks.append(
            _zero_violations_check(
                connection,
                check_type="field_enum",
                table_schema=schema_name,
                table_name=table_name,
                field_name=field_name,
                sql=(
                    f"SELECT COUNT(*) FROM {qualified_table_name(schema_name, table_name)} "
                    f"WHERE {quote_identifier(field_name)} NOT IN ({placeholders})"
                ),
                params=enum_values,
                name=f"Check that field {field_name} only contains enum values {enum_values}",
                failure_reason="Found {value} values outside the enum.",
            )
        )

    pattern = options.get("pattern")
    if pattern is not None:
        checks.append(
            _zero_violations_check(
                connection,
                check_type="field_regex",
                table_schema=schema_name,
                table_name=table_name,
                field_name=field_name,
                sql=(
                    f"SELECT COUNT(*) FROM {qualified_table_name(schema_name, table_name)} "
                    f"WHERE {quote_identifier(field_name)} NOT LIKE_REGEXPR ?"
                ),
                params=[pattern],
                name=f"Check that field {field_name} matches regex {pattern}",
                failure_reason="Found {value} values that do not match the regex.",
            )
        )

    return checks


def _minimum_check(connection, schema_name: str, table_name: str, field_name: str, minimum: Any) -> Check:
    return _zero_violations_check(
        connection,
        check_type="field_minimum",
        table_schema=schema_name,
        table_name=table_name,
        field_name=field_name,
        sql=(
            f"SELECT COUNT(*) FROM {qualified_table_name(schema_name, table_name)} "
            f"WHERE {quote_identifier(field_name)} < ?"
        ),
        params=[minimum],
        name=f"Check that field {field_name} has a minimum of {minimum}",
        failure_reason=f"Found {{value}} values below {minimum}.",
    )


def _maximum_check(connection, schema_name: str, table_name: str, field_name: str, maximum: Any) -> Check:
    return _zero_violations_check(
        connection,
        check_type="field_maximum",
        table_schema=schema_name,
        table_name=table_name,
        field_name=field_name,
        sql=(
            f"SELECT COUNT(*) FROM {qualified_table_name(schema_name, table_name)} "
            f"WHERE {quote_identifier(field_name)} > ?"
        ),
        params=[maximum],
        name=f"Check that field {field_name} has a maximum of {maximum}",
        failure_reason=f"Found {{value}} values above {maximum}.",
    )


def _not_equal_check(connection, schema_name: str, table_name: str, field_name: str, value: Any) -> Check:
    return _zero_violations_check(
        connection,
        check_type="field_not_equal",
        table_schema=schema_name,
        table_name=table_name,
        field_name=field_name,
        sql=(
            f"SELECT COUNT(*) FROM {qualified_table_name(schema_name, table_name)} "
            f"WHERE {quote_identifier(field_name)} = ?"
        ),
        params=[value],
        name=f"Check that field {field_name} is not equal to {value}",
        failure_reason=f"Found {{value}} values equal to {value}.",
    )


def _field_type_check(table_name: str, field_name: str, expected_type: str, column: ColumnMetadata) -> Check:
    actual_type = column.data_type_name
    result = ResultEnum.passed if types_match(actual_type, expected_type) else ResultEnum.failed
    return _result_check(
        check_type="field_type",
        key=f"{table_name}__{field_name}__field_type",
        name=f"Check that field {field_name} has type {expected_type}",
        model=table_name,
        field=field_name,
        implementation="Catalog DATA_TYPE_NAME comparison",
        result=result,
        reason=None if result == ResultEnum.passed else f"Expected {expected_type}, got {actual_type}.",
        diagnostics={"expected": expected_type, "actual": actual_type},
    )


def _field_required_check(table_name: str, field_name: str, column: ColumnMetadata) -> Check:
    nullable = str(column.is_nullable).upper()
    result = ResultEnum.passed if nullable == "FALSE" else ResultEnum.failed
    return _result_check(
        check_type="field_required",
        key=f"{table_name}__{field_name}__field_required",
        name=f"Check that field {field_name} is not nullable",
        model=table_name,
        field=field_name,
        implementation="Catalog IS_NULLABLE comparison",
        result=result,
        reason=None if result == ResultEnum.passed else f"Field {field_name} is nullable in the catalog.",
        diagnostics={"isNullable": column.is_nullable},
    )


def _primary_key_check(connection, schema_name: str, table_name: str, field_name: str, source: str) -> Check:
    sql = """
SELECT COLUMN_NAME
FROM SYS.CONSTRAINTS
WHERE SCHEMA_NAME = ? AND TABLE_NAME = ? AND IS_PRIMARY_KEY = 'TRUE'
"""
    if source == "view":
        return _result_check(
            check_type="field_primary_key",
            key=f"{table_name}__{field_name}__field_primary_key",
            name=f"Check that field {field_name} is a primary key",
            model=table_name,
            field=field_name,
            implementation=sql.strip(),
            result=ResultEnum.warning,
            reason="Primary key metadata not available for views.",
        )

    rows = _fetch_all(connection, sql, [schema_name, table_name])
    primary_key_columns = {_row_value(row, 0, "COLUMN_NAME") for row in rows}
    result = ResultEnum.passed if field_name in primary_key_columns else ResultEnum.failed
    return _result_check(
        check_type="field_primary_key",
        key=f"{table_name}__{field_name}__field_primary_key",
        name=f"Check that field {field_name} is a primary key",
        model=table_name,
        field=field_name,
        implementation=sql.strip(),
        result=result,
        reason=None if result == ResultEnum.passed else f"Field {field_name} is not part of the primary key.",
        diagnostics={"primaryKeyColumns": sorted(primary_key_columns)},
    )


def _zero_violations_check(
    connection,
    *,
    check_type: str,
    table_schema: str,
    table_name: str,
    field_name: str,
    sql: str,
    params: list[Any] | None,
    name: str,
    failure_reason: str,
) -> Check:
    try:
        value = _fetch_scalar(connection, sql, params)
    except Exception as e:
        return _result_check(
            check_type=check_type,
            key=f"{table_name}__{field_name}__{check_type}",
            name=name,
            model=table_name,
            field=field_name,
            implementation=sql,
            result=ResultEnum.error,
            reason=str(e),
        )

    result = ResultEnum.passed if value == 0 else ResultEnum.failed
    return _result_check(
        check_type=check_type,
        key=f"{table_name}__{field_name}__{check_type}",
        name=name,
        model=table_name,
        field=field_name,
        implementation=sql,
        result=result,
        reason=None if result == ResultEnum.passed else failure_reason.format(value=value),
        diagnostics={"value": value, "schema": table_schema},
    )


def _get_column_metadata(connection, schema_name: str, table_name: str) -> list[ColumnMetadata]:
    table_sql = """
SELECT COLUMN_NAME, DATA_TYPE_NAME, LENGTH, SCALE, IS_NULLABLE, POSITION
FROM SYS.TABLE_COLUMNS
WHERE SCHEMA_NAME = ? AND TABLE_NAME = ?
ORDER BY POSITION
"""
    table_rows = _fetch_all(connection, table_sql, [schema_name, table_name])
    if table_rows:
        return [_column_metadata_from_row(row, "table") for row in table_rows]

    view_sql = """
SELECT COLUMN_NAME, DATA_TYPE_NAME, LENGTH, SCALE, IS_NULLABLE, POSITION
FROM SYS.VIEW_COLUMNS
WHERE SCHEMA_NAME = ? AND VIEW_NAME = ?
ORDER BY POSITION
"""
    view_rows = _fetch_all(connection, view_sql, [schema_name, table_name])
    return [_column_metadata_from_row(row, "view") for row in view_rows]


def _column_metadata_from_row(row, source: str) -> ColumnMetadata:
    return ColumnMetadata(
        name=_row_value(row, 0, "COLUMN_NAME"),
        data_type_name=_row_value(row, 1, "DATA_TYPE_NAME"),
        length=_row_value(row, 2, "LENGTH"),
        scale=_row_value(row, 3, "SCALE"),
        is_nullable=_row_value(row, 4, "IS_NULLABLE"),
        position=_row_value(row, 5, "POSITION"),
        source=source,
    )


def _fetch_scalar(connection, sql: str, params: list[Any] | None = None):
    cursor = connection.cursor()
    try:
        cursor.execute(sql, params or [])
        row = cursor.fetchone()
        if row is None:
            return None
        return _row_value(row, 0, None)
    finally:
        _close_cursor(cursor)


def _fetch_all(connection, sql: str, params: list[Any] | None = None):
    cursor = connection.cursor()
    try:
        cursor.execute(sql, params or [])
        return cursor.fetchall()
    finally:
        _close_cursor(cursor)


def _row_value(row, index: int, key: str | None):
    if isinstance(row, dict):
        if key is None:
            return next(iter(row.values()))
        return row[key]
    return row[index]


def _close_cursor(cursor) -> None:
    if hasattr(cursor, "close"):
        cursor.close()


def _result_check(
    *,
    check_type: str,
    key: str,
    name: str,
    model: str,
    field: str | None,
    implementation: str,
    result: ResultEnum,
    reason: str | None,
    diagnostics: dict | None = None,
) -> Check:
    return Check(
        id=str(uuid.uuid4()),
        key=key,
        category="schema",
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
