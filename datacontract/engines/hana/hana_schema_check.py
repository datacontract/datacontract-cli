import uuid
from dataclasses import dataclass
from typing import Any

from open_data_contract_standard.model import SchemaObject, SchemaProperty

from datacontract.engines.checks.dimensions import default_dimension
from datacontract.engines.hana.hana_check_selection import SELECT_ALL, CheckSelection
from datacontract.engines.hana.hana_type_mapping import types_match
from datacontract.model.enum_values import get_enum_values
from datacontract.model.run import Check, ResultEnum

DRY_RUN_REASON = "Dry run: check not executed"
METADATA_ONLY_REASON = "Row-value check disabled by --metadata-only"


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


def table_reference(schema: str, table: str, row_filter: str | None = None) -> str:
    """The FROM clause of a data query, restricted to the rows ``--filter`` selects.

    The predicate is written in HANA's dialect and references columns unqualified,
    so wrapping the table in a derived table keeps every check that reads rows
    (counts, duplicates, freshness) on the same subset, and the SQL recorded on
    the check shows the WHERE clause. Catalog reads never go through here: they
    describe the table itself, which no row filter changes.
    """
    qualified = qualified_table_name(schema, table)
    if not row_filter:
        return qualified
    return f"(SELECT * FROM {qualified} WHERE {row_filter})"


def duplicate_count_query(schema: str, table: str, fields: list[str], row_filter: str | None = None) -> str:
    """Count duplicated keys, including a NULL key only if it occurs more than once."""
    columns = ", ".join(quote_identifier(field) for field in fields)
    return (
        f"SELECT COUNT(*) FROM (SELECT {columns} FROM {table_reference(schema, table, row_filter)} "
        f"GROUP BY {columns} HAVING COUNT(*) > 1) AS duplicate_groups"
    )


def selects(selection: CheckSelection, check_type: str) -> bool:
    """Whether the run asked for a built-in check of this type.

    Built-in checks carry no ODCS quality rule, so only ``--dimension`` can
    select them: ``--quality-id`` and ``--tag`` exclude them entirely.
    """
    return selection.selects_builtin(default_dimension(check_type))


def run_schema_checks(
    connection,
    schema_name: str,
    schema_object: SchemaObject,
    *,
    dry_run: bool = False,
    metadata_only: bool = False,
    row_filter: str | None = None,
    selection: CheckSelection = SELECT_ALL,
) -> list[Check]:
    """Build the native check list, optionally planning it or reading only the catalog."""
    table_name = _schema_name(schema_object)
    checks: list[Check] = []
    column_metadata = [] if dry_run else _get_column_metadata(connection, schema_name, table_name)
    skip_reason = METADATA_ONLY_REASON if metadata_only else DRY_RUN_REASON if dry_run else None

    if selects(selection, "model_exists"):
        checks.append(
            _result_check(
                check_type="model_exists",
                key=f"{table_name}__model_exists",
                name=f"Check that model {table_name} exists",
                model=table_name,
                field=None,
                implementation="Catalog lookup in SYS.TABLE_COLUMNS and SYS.VIEW_COLUMNS",
                result=ResultEnum.passed if column_metadata else ResultEnum.failed,
                reason=None if column_metadata else f"Model {schema_name}.{table_name} does not exist.",
                dry_run=dry_run,
            )
        )
    # A model that is not there has nothing to check, whether or not the filters
    # above kept the check that says so.
    if not column_metadata and not dry_run:
        return checks

    columns_by_name = {column.name: column for column in column_metadata}
    primary_key_props = sorted(
        (prop for prop in schema_object.properties or [] if prop.primaryKey),
        key=lambda prop: prop.primaryKeyPosition if prop.primaryKeyPosition is not None else 0,
    )
    primary_key_fields = [_property_name(prop) for prop in primary_key_props]

    for prop in schema_object.properties or []:
        field_name = _property_name(prop)
        column = columns_by_name.get(field_name)
        if selects(selection, "field_is_present"):
            checks.append(
                _result_check(
                    check_type="field_is_present",
                    key=f"{table_name}__{field_name}__field_is_present",
                    name=f"Check that field {field_name} is present",
                    model=table_name,
                    field=field_name,
                    implementation="Catalog lookup in SYS.TABLE_COLUMNS and SYS.VIEW_COLUMNS",
                    result=ResultEnum.passed if column else ResultEnum.failed,
                    reason=None if column else f"Field {field_name} is missing in {schema_name}.{table_name}.",
                    dry_run=dry_run,
                )
            )
        if column is None and not dry_run:
            continue

        expected_type = prop.physicalType or prop.logicalType
        if expected_type and selects(selection, "field_type"):
            checks.append(_field_type_check(table_name, field_name, expected_type, column))

        if prop.required or prop.primaryKey:
            check_type = "field_required" if prop.required else "field_primary_key_required"
            if selects(selection, check_type):
                checks.append(
                    _zero_violations_check(
                        connection,
                        check_type=check_type,
                        table_schema=schema_name,
                        table_name=table_name,
                        field_name=field_name,
                        sql=(
                            f"SELECT COUNT(*) FROM {table_reference(schema_name, table_name, row_filter)} "
                            f"WHERE {quote_identifier(field_name)} IS NULL"
                        ),
                        params=None,
                        name=f"Check that field {field_name} has no missing values",
                        failure_reason="Found {value} missing values.",
                        skip_reason=skip_reason,
                    )
                )

        if prop.unique or (prop.primaryKey and len(primary_key_fields) == 1):
            check_type = "field_unique" if prop.unique else "field_primary_key_unique"
            if selects(selection, check_type):
                checks.append(
                    _zero_violations_check(
                        connection,
                        check_type=check_type,
                        table_schema=schema_name,
                        table_name=table_name,
                        field_name=field_name,
                        sql=duplicate_count_query(schema_name, table_name, [field_name], row_filter),
                        params=None,
                        name=f"Check that unique field {field_name} has no duplicate values",
                        failure_reason="Found {value} duplicate values.",
                        skip_reason=skip_reason,
                    )
                )

        checks.extend(
            _logical_type_option_checks(
                connection,
                schema_name,
                table_name,
                field_name,
                prop,
                skip_reason,
                row_filter=row_filter,
                selection=selection,
            )
        )

    if (
        len(primary_key_fields) > 1
        and (dry_run or all(field in columns_by_name for field in primary_key_fields))
        and selects(selection, "primary_key_unique")
    ):
        checks.append(
            _zero_violations_check(
                connection,
                check_type="primary_key_unique",
                table_schema=schema_name,
                table_name=table_name,
                field_name=None,
                sql=duplicate_count_query(schema_name, table_name, primary_key_fields, row_filter),
                params=None,
                name=f"Check that primary key ({', '.join(primary_key_fields)}) has no duplicate values",
                failure_reason="Found {value} duplicate primary keys.",
                skip_reason=skip_reason,
            )
        )

    return checks


def _schema_name(schema_object: SchemaObject) -> str:
    return schema_object.physicalName or schema_object.name


def _property_name(prop: SchemaProperty) -> str:
    return prop.physicalName or prop.name


def _logical_type_option_checks(
    connection,
    schema_name: str,
    table_name: str,
    field_name: str,
    prop: SchemaProperty,
    skip_reason: str | None = None,
    *,
    row_filter: str | None = None,
    selection: CheckSelection = SELECT_ALL,
) -> list[Check]:
    checks: list[Check] = []
    options = prop.logicalTypeOptions or {}

    min_length = options.get("minLength")
    if min_length is not None and selects(selection, "field_min_length"):
        checks.append(
            _zero_violations_check(
                connection,
                check_type="field_min_length",
                table_schema=schema_name,
                table_name=table_name,
                field_name=field_name,
                sql=(
                    f"SELECT COUNT(*) FROM {table_reference(schema_name, table_name, row_filter)} "
                    f"WHERE LENGTH({quote_identifier(field_name)}) < ?"
                ),
                params=[min_length],
                name=f"Check that field {field_name} has a min length of {min_length}",
                failure_reason=f"Found {{value}} values shorter than {min_length}.",
                skip_reason=skip_reason,
            )
        )

    max_length = options.get("maxLength")
    if max_length is not None and selects(selection, "field_max_length"):
        checks.append(
            _zero_violations_check(
                connection,
                check_type="field_max_length",
                table_schema=schema_name,
                table_name=table_name,
                field_name=field_name,
                sql=(
                    f"SELECT COUNT(*) FROM {table_reference(schema_name, table_name, row_filter)} "
                    f"WHERE LENGTH({quote_identifier(field_name)}) > ?"
                ),
                params=[max_length],
                name=f"Check that field {field_name} has a max length of {max_length}",
                failure_reason=f"Found {{value}} values longer than {max_length}.",
                skip_reason=skip_reason,
            )
        )

    minimum = options.get("minimum")
    if minimum is not None and selects(selection, "field_minimum"):
        checks.append(_minimum_check(connection, schema_name, table_name, field_name, minimum, skip_reason, row_filter))

    maximum = options.get("maximum")
    if maximum is not None and selects(selection, "field_maximum"):
        checks.append(_maximum_check(connection, schema_name, table_name, field_name, maximum, skip_reason, row_filter))

    exclusive_minimum = options.get("exclusiveMinimum")
    if exclusive_minimum is not None:
        if selects(selection, "field_minimum"):
            checks.append(
                _minimum_check(
                    connection, schema_name, table_name, field_name, exclusive_minimum, skip_reason, row_filter
                )
            )
        if selects(selection, "field_not_equal"):
            checks.append(
                _not_equal_check(
                    connection, schema_name, table_name, field_name, exclusive_minimum, skip_reason, row_filter
                )
            )

    exclusive_maximum = options.get("exclusiveMaximum")
    if exclusive_maximum is not None:
        if selects(selection, "field_maximum"):
            checks.append(
                _maximum_check(
                    connection, schema_name, table_name, field_name, exclusive_maximum, skip_reason, row_filter
                )
            )
        if selects(selection, "field_not_equal"):
            checks.append(
                _not_equal_check(
                    connection, schema_name, table_name, field_name, exclusive_maximum, skip_reason, row_filter
                )
            )

    enum_values = get_enum_values(prop, include_quality_rule=False)
    if enum_values is not None and len(enum_values) > 0 and selects(selection, "field_enum"):
        # NULL inside NOT IN would make even non-enum values evaluate to UNKNOWN.
        # Required checks handle missing values independently of the allowed set.
        non_null_values = [value for value in enum_values if value is not None]
        placeholders = ", ".join("?" for _ in non_null_values)
        predicate = (
            f"{quote_identifier(field_name)} NOT IN ({placeholders})"
            if non_null_values
            else f"{quote_identifier(field_name)} IS NOT NULL"
        )
        checks.append(
            _zero_violations_check(
                connection,
                check_type="field_enum",
                table_schema=schema_name,
                table_name=table_name,
                field_name=field_name,
                sql=(f"SELECT COUNT(*) FROM {table_reference(schema_name, table_name, row_filter)} WHERE {predicate}"),
                params=non_null_values,
                name=f"Check that field {field_name} only contains enum values {enum_values}",
                failure_reason="Found {value} values outside the enum.",
                skip_reason=skip_reason,
            )
        )

    pattern = options.get("pattern")
    if pattern is not None and selects(selection, "field_regex"):
        checks.append(
            _zero_violations_check(
                connection,
                check_type="field_regex",
                table_schema=schema_name,
                table_name=table_name,
                field_name=field_name,
                sql=(
                    f"SELECT COUNT(*) FROM {table_reference(schema_name, table_name, row_filter)} "
                    f"WHERE {quote_identifier(field_name)} NOT LIKE_REGEXPR ?"
                ),
                params=[pattern],
                name=f"Check that field {field_name} matches regex {pattern}",
                failure_reason="Found {value} values that do not match the regex.",
                skip_reason=skip_reason,
            )
        )

    return checks


def _minimum_check(
    connection,
    schema_name: str,
    table_name: str,
    field_name: str,
    minimum: Any,
    skip_reason: str | None = None,
    row_filter: str | None = None,
) -> Check:
    return _zero_violations_check(
        connection,
        check_type="field_minimum",
        table_schema=schema_name,
        table_name=table_name,
        field_name=field_name,
        sql=(
            f"SELECT COUNT(*) FROM {table_reference(schema_name, table_name, row_filter)} "
            f"WHERE {quote_identifier(field_name)} < ?"
        ),
        params=[minimum],
        name=f"Check that field {field_name} has a minimum of {minimum}",
        failure_reason=f"Found {{value}} values below {minimum}.",
        skip_reason=skip_reason,
    )


def _maximum_check(
    connection,
    schema_name: str,
    table_name: str,
    field_name: str,
    maximum: Any,
    skip_reason: str | None = None,
    row_filter: str | None = None,
) -> Check:
    return _zero_violations_check(
        connection,
        check_type="field_maximum",
        table_schema=schema_name,
        table_name=table_name,
        field_name=field_name,
        sql=(
            f"SELECT COUNT(*) FROM {table_reference(schema_name, table_name, row_filter)} "
            f"WHERE {quote_identifier(field_name)} > ?"
        ),
        params=[maximum],
        name=f"Check that field {field_name} has a maximum of {maximum}",
        failure_reason=f"Found {{value}} values above {maximum}.",
        skip_reason=skip_reason,
    )


def _not_equal_check(
    connection,
    schema_name: str,
    table_name: str,
    field_name: str,
    value: Any,
    skip_reason: str | None = None,
    row_filter: str | None = None,
) -> Check:
    return _zero_violations_check(
        connection,
        check_type="field_not_equal",
        table_schema=schema_name,
        table_name=table_name,
        field_name=field_name,
        sql=(
            f"SELECT COUNT(*) FROM {table_reference(schema_name, table_name, row_filter)} "
            f"WHERE {quote_identifier(field_name)} = ?"
        ),
        params=[value],
        name=f"Check that field {field_name} is not equal to {value}",
        failure_reason=f"Found {{value}} values equal to {value}.",
        skip_reason=skip_reason,
    )


def _field_type_check(table_name: str, field_name: str, expected_type: str, column: ColumnMetadata | None) -> Check:
    # A dry run has no catalog metadata. Missing columns in real runs are handled above.
    actual_type = column.data_type_name if column else None
    result = (
        ResultEnum.passed
        if column is not None and types_match(column.data_type_name, expected_type)
        else ResultEnum.failed
    )
    return _result_check(
        check_type="field_type",
        key=f"{table_name}__{field_name}__field_type",
        name=f"Check that field {field_name} has type {expected_type}",
        model=table_name,
        field=field_name,
        implementation="Catalog DATA_TYPE_NAME comparison",
        result=result,
        reason=None if result == ResultEnum.passed else f"Expected {expected_type}, got {actual_type}.",
        diagnostics={"expected": expected_type, "actual": actual_type} if column else None,
        dry_run=column is None,
    )


def _zero_violations_check(
    connection,
    *,
    check_type: str,
    table_schema: str,
    table_name: str,
    field_name: str | None,
    sql: str,
    params: list[Any] | None,
    name: str,
    failure_reason: str,
    skip_reason: str | None = None,
) -> Check:
    key = f"{table_name}__{field_name}__{check_type}" if field_name is not None else f"{table_name}__{check_type}"
    if skip_reason:
        return _result_check(
            check_type=check_type,
            key=key,
            name=name,
            model=table_name,
            field=field_name,
            implementation=sql,
            result=ResultEnum.skipped,
            reason=skip_reason,
        )
    try:
        value = _fetch_scalar(connection, sql, params)
    except Exception as e:
        return _result_check(
            check_type=check_type,
            key=key,
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
        key=key,
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
    dry_run: bool = False,
) -> Check:
    return Check(
        id=str(uuid.uuid4()),
        key=key,
        category="schema",
        type=check_type,
        name=name,
        model=model,
        field=field,
        dimension=default_dimension(check_type),
        engine="hana",
        language="sql",
        implementation=implementation,
        result=ResultEnum.skipped if dry_run else result,
        reason=DRY_RUN_REASON if dry_run else reason,
        diagnostics=None if dry_run else diagnostics,
    )
