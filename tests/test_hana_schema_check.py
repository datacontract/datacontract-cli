import sqlite3

import pytest
from open_data_contract_standard.model import DataQuality, SchemaObject, SchemaProperty

from datacontract.engines.hana.hana_schema_check import (
    qualified_table_name,
    quote_identifier,
    run_schema_checks,
)
from datacontract.model.run import ResultEnum


class FakeConnection:
    def __init__(self, responses=None):
        self.responses = responses or []
        self.executed = []

    def cursor(self):
        return FakeCursor(self)

    def response_for(self, sql, params):
        self.executed.append((sql, params))
        for matcher, response in self.responses:
            if matcher(sql, params):
                return response
        return []


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection
        self.response = []

    def execute(self, sql, params=None):
        self.response = self.connection.response_for(sql, params or [])

    def fetchall(self):
        return self.response

    def fetchone(self):
        return self.response[0] if self.response else None

    def close(self):
        pass


def has_sql(fragment):
    return lambda sql, params: fragment in " ".join(sql.split())


def has_params(*expected):
    return lambda sql, params: params == list(expected)


def catalog_response(rows, source="table"):
    table_rows = rows if source == "table" else []
    view_rows = rows if source == "view" else []
    return [
        (has_sql("FROM SYS.TABLE_COLUMNS"), table_rows),
        (has_sql("FROM SYS.VIEW_COLUMNS"), view_rows),
    ]


def column(name="ID", data_type="INTEGER", nullable="FALSE"):
    return (name, data_type, None, None, nullable, 1)


def check_by_type(checks, check_type):
    return next(check for check in checks if check.type == check_type)


class DataConnection(FakeConnection):
    """Execute data checks on real rows; substitute only HANA's catalog responses."""

    def __init__(self, source):
        super().__init__(
            catalog_response(
                [
                    column("ID", "INTEGER", "TRUE"),
                    column("LINE_NO", "INTEGER", "TRUE"),
                    column("STATUS", "NVARCHAR", "TRUE"),
                ],
                source=source,
            )
        )
        self.db = sqlite3.connect(":memory:")
        self.db.execute("ATTACH DATABASE ':memory:' AS SALES")
        self.table = "ORDERS_DATA" if source == "view" else "ORDERS"
        self.db.execute(f"CREATE TABLE SALES.{self.table} (ID INTEGER, LINE_NO INTEGER, STATUS TEXT)")
        if source == "view":
            self.db.execute("CREATE VIEW SALES.ORDERS AS SELECT * FROM ORDERS_DATA")

    def insert(self, rows):
        self.db.executemany(f"INSERT INTO SALES.{self.table} VALUES (?, ?, ?)", rows)

    def response_for(self, sql, params):
        if "SYS." in sql:
            return super().response_for(sql, params)
        self.executed.append((sql, params))
        return self.db.execute(sql, params).fetchall()

    def close(self):
        self.db.close()


@pytest.fixture(params=["table", "view"])
def hana_data(request):
    connection = DataConnection(request.param)
    try:
        yield connection
    finally:
        connection.close()


def test_model_exists_pass():
    connection = FakeConnection(catalog_response([column()]))
    schema = SchemaObject(name="ORDERS", properties=[])

    checks = run_schema_checks(connection, "SALES", schema)

    assert check_by_type(checks, "model_exists").result == ResultEnum.passed


def test_model_exists_fail():
    connection = FakeConnection(catalog_response([]))
    schema = SchemaObject(name="ORDERS", properties=[SchemaProperty(name="ID", logicalType="integer")])

    checks = run_schema_checks(connection, "SALES", schema)

    assert len(checks) == 1
    assert check_by_type(checks, "model_exists").result == ResultEnum.failed


def test_field_present_pass():
    connection = FakeConnection(catalog_response([column()]))
    schema = SchemaObject(name="ORDERS", properties=[SchemaProperty(name="ID")])

    checks = run_schema_checks(connection, "SALES", schema)

    assert check_by_type(checks, "field_is_present").result == ResultEnum.passed


def test_field_present_fail():
    connection = FakeConnection(catalog_response([column("OTHER")]))
    schema = SchemaObject(name="ORDERS", properties=[SchemaProperty(name="ID")])

    checks = run_schema_checks(connection, "SALES", schema)

    assert check_by_type(checks, "field_is_present").result == ResultEnum.failed


def test_field_type_match():
    connection = FakeConnection(catalog_response([column(data_type="INTEGER")]))
    schema = SchemaObject(name="ORDERS", properties=[SchemaProperty(name="ID", logicalType="integer")])

    checks = run_schema_checks(connection, "SALES", schema)

    assert check_by_type(checks, "field_type").result == ResultEnum.passed


def test_field_type_mismatch():
    connection = FakeConnection(catalog_response([column(data_type="NVARCHAR")]))
    schema = SchemaObject(name="ORDERS", properties=[SchemaProperty(name="ID", logicalType="integer")])

    checks = run_schema_checks(connection, "SALES", schema)
    check = check_by_type(checks, "field_type")

    assert check.result == ResultEnum.failed
    assert check.diagnostics == {"expected": "integer", "actual": "NVARCHAR"}


@pytest.mark.parametrize("values,missing", [([1, 2], 0), ([1, None], 1), ([], 0)])
def test_required_checks_values_in_nullable_columns(hana_data, values, missing):
    hana_data.insert([(value, None, None) for value in values])
    schema = SchemaObject(name="ORDERS", properties=[SchemaProperty(name="ID", required=True)])

    check = check_by_type(run_schema_checks(hana_data, "SALES", schema), "field_required")

    assert check.result == (ResultEnum.failed if missing else ResultEnum.passed)
    assert check.diagnostics["value"] == missing


@pytest.mark.parametrize("values,duplicates", [([1, None], 0), ([1, 1, 1, 2, 2], 2), ([None, None], 1), ([], 0)])
def test_unique_counts_duplicated_keys(hana_data, values, duplicates):
    hana_data.insert([(value, None, None) for value in values])
    schema = SchemaObject(name="ORDERS", properties=[SchemaProperty(name="ID", unique=True)])

    check = check_by_type(run_schema_checks(hana_data, "SALES", schema), "field_unique")

    assert check.result == (ResultEnum.failed if duplicates else ResultEnum.passed)
    assert check.diagnostics["value"] == duplicates


def test_field_min_length_and_max_length():
    connection = FakeConnection(
        catalog_response([column("NAME", "NVARCHAR")])
        + [
            (has_params(3), [(0,)]),
            (has_params(10), [(1,)]),
        ]
    )
    prop = SchemaProperty(name="NAME", logicalType="string", logicalTypeOptions={"minLength": 3, "maxLength": 10})
    schema = SchemaObject(name="ORDERS", properties=[prop])

    checks = run_schema_checks(connection, "SALES", schema)

    assert check_by_type(checks, "field_min_length").result == ResultEnum.passed
    assert check_by_type(checks, "field_max_length").result == ResultEnum.failed


def test_field_minimum_maximum_and_not_equal():
    connection = FakeConnection(
        catalog_response([column("AMOUNT", "DECIMAL")])
        + [
            (has_params(1), [(0,)]),
            (has_params(10), [(1,)]),
            (has_params(0), [(0,)]),
        ]
    )
    prop = SchemaProperty(
        name="AMOUNT",
        logicalType="decimal",
        logicalTypeOptions={"minimum": 1, "maximum": 10, "exclusiveMinimum": 0},
    )
    schema = SchemaObject(name="ORDERS", properties=[prop])

    checks = run_schema_checks(connection, "SALES", schema)

    assert check_by_type(checks, "field_minimum").result == ResultEnum.passed
    assert check_by_type(checks, "field_maximum").result == ResultEnum.failed
    assert check_by_type(checks, "field_not_equal").result == ResultEnum.passed


def test_field_enum_pass_and_fail():
    connection = FakeConnection(catalog_response([column("STATUS", "NVARCHAR")]) + [(has_sql("NOT IN"), [(1,)])])
    prop = SchemaProperty(name="STATUS", logicalType="string", logicalTypeOptions={"enum": ["PAID", "OPEN"]})
    schema = SchemaObject(name="ORDERS", properties=[prop])

    checks = run_schema_checks(connection, "SALES", schema)

    assert check_by_type(checks, "field_enum").result == ResultEnum.failed


def test_metadata_only_skips_enum_data_query():
    connection = FakeConnection(catalog_response([column("STATUS", "NVARCHAR")]))
    prop = SchemaProperty(name="STATUS", logicalType="string", logicalTypeOptions={"enum": ["PAID", "OPEN"]})

    checks = run_schema_checks(connection, "SALES", SchemaObject(name="ORDERS", properties=[prop]), metadata_only=True)

    assert check_by_type(checks, "field_enum").result == ResultEnum.skipped
    assert all("SYS.TABLE_COLUMNS" in sql for sql, _ in connection.executed)


@pytest.mark.parametrize("values,invalid", [(["OPEN", "O'Reilly"], 0), (["BAD"], 1), ([None], 0)])
def test_odcs_enum_entries_take_precedence_and_check_actual_values(hana_data, values, invalid):
    hana_data.insert([(None, None, value) for value in values])
    prop = SchemaProperty(
        name="status",
        physicalName="STATUS",
        logicalType="string",
        enum=[{"value": "OPEN", "label": "Open"}, {"value": "O'Reilly"}],
        logicalTypeOptions={"enum": ["BAD"]},
        customProperties=[{"property": "enum", "value": ["OTHER"]}],
    )

    checks = run_schema_checks(hana_data, "SALES", SchemaObject(name="ORDERS", properties=[prop]))

    check = check_by_type(checks, "field_enum")
    assert check.result == (ResultEnum.failed if invalid else ResultEnum.passed)
    assert check.diagnostics["value"] == invalid
    assert len([c for c in checks if c.type == "field_enum"]) == 1


@pytest.mark.parametrize("allowed", [[None], [None, "OPEN"]])
def test_enum_with_null_does_not_accept_arbitrary_non_null_values(hana_data, allowed):
    hana_data.insert([(None, None, "BAD"), (None, None, None)])
    prop = SchemaProperty(name="STATUS", enum=[{"value": value} for value in allowed])

    check = check_by_type(
        run_schema_checks(hana_data, "SALES", SchemaObject(name="ORDERS", properties=[prop])), "field_enum"
    )

    assert check.result == ResultEnum.failed
    assert check.diagnostics["value"] == 1


def test_numeric_enum_entries_preserve_their_values(hana_data):
    hana_data.insert([(1, None, None), (3, None, None)])
    prop = SchemaProperty(name="ID", logicalType="integer", enum=[{"value": 1}, {"value": 2}])

    check = check_by_type(
        run_schema_checks(hana_data, "SALES", SchemaObject(name="ORDERS", properties=[prop])), "field_enum"
    )

    assert check.result == ResultEnum.failed
    assert check.diagnostics["value"] == 1


def test_quality_valid_values_do_not_also_generate_a_schema_enum(hana_data):
    prop = SchemaProperty(
        name="STATUS",
        quality=[
            DataQuality(metric="invalidValues", arguments={"validValues": ["OPEN"]}, mustBe=0),
        ],
    )

    checks = run_schema_checks(hana_data, "SALES", SchemaObject(name="ORDERS", properties=[prop]))

    assert not any(c.type == "field_enum" for c in checks)


@pytest.mark.parametrize("dry_run", [False, True])
def test_primary_key_and_enum_checks_are_skipped_in_metadata_only(hana_data, dry_run):
    schema = SchemaObject(
        name="ORDERS",
        properties=[
            SchemaProperty(name="ID", primaryKey=True),
            SchemaProperty(name="LINE_NO", primaryKey=True),
            SchemaProperty(name="STATUS", required=True, enum=[{"value": "OPEN"}]),
        ],
    )

    checks = run_schema_checks(None if dry_run else hana_data, "SALES", schema, metadata_only=True, dry_run=dry_run)

    data_checks = [
        c
        for c in checks
        if c.type in {"field_primary_key_required", "primary_key_unique", "field_enum", "field_required"}
    ]
    assert len(data_checks) == 5
    assert all(
        c.result == ResultEnum.skipped and c.reason == "Row-value check disabled by --metadata-only"
        for c in data_checks
    )
    assert all("SYS." in sql for sql, _ in hana_data.executed)


def test_field_regex_uses_like_regexpr():
    connection = FakeConnection(catalog_response([column("EMAIL", "NVARCHAR")]) + [(has_sql("LIKE_REGEXPR"), [(0,)])])
    prop = SchemaProperty(name="EMAIL", logicalType="string", logicalTypeOptions={"pattern": ".*@example.com"})
    schema = SchemaObject(name="ORDERS", properties=[prop])

    checks = run_schema_checks(connection, "SALES", schema)

    assert check_by_type(checks, "field_regex").result == ResultEnum.passed
    assert "LIKE_REGEXPR" in connection.executed[-1][0]


@pytest.mark.parametrize("values,missing,duplicates", [([1, 2], 0, 0), ([1, 1], 0, 1), ([None, 1], 1, 0), ([], 0, 0)])
def test_primary_key_is_not_null_and_unique_in_the_data(hana_data, values, missing, duplicates):
    hana_data.insert([(value, None, None) for value in values])
    schema = SchemaObject(name="ORDERS", properties=[SchemaProperty(name="ID", primaryKey=True)])

    checks = run_schema_checks(hana_data, "SALES", schema)

    required = check_by_type(checks, "field_primary_key_required")
    unique = check_by_type(checks, "field_primary_key_unique")
    assert required.result == (ResultEnum.failed if missing else ResultEnum.passed)
    assert unique.result == (ResultEnum.failed if duplicates else ResultEnum.passed)
    assert required.diagnostics["value"] == missing
    assert unique.diagnostics["value"] == duplicates
    assert not any("SYS.CONSTRAINTS" in sql for sql, _ in hana_data.executed)


@pytest.mark.parametrize(
    "rows,missing,duplicates",
    [
        ([(1, 1, None), (1, 2, None), (2, 1, None)], 0, 0),
        ([(1, 1, None), (1, 1, None), (1, 1, None)], 0, 1),
        ([(None, 1, None)], 1, 0),
    ],
)
def test_composite_primary_key_checks_tuples_using_physical_names(hana_data, rows, missing, duplicates):
    hana_data.insert(rows)
    schema = SchemaObject(
        name="orders",
        physicalName="ORDERS",
        properties=[
            SchemaProperty(name="line", physicalName="LINE_NO", primaryKey=True, primaryKeyPosition=2),
            SchemaProperty(name="id", physicalName="ID", primaryKey=True, primaryKeyPosition=1),
        ],
    )

    checks = run_schema_checks(hana_data, "SALES", schema)

    required = [c for c in checks if c.type == "field_primary_key_required"]
    assert len(required) == 2
    assert sum(c.diagnostics["value"] for c in required) == missing
    unique = check_by_type(checks, "primary_key_unique")
    assert unique.result == (ResultEnum.failed if duplicates else ResultEnum.passed)
    assert unique.diagnostics["value"] == duplicates
    assert unique.key == "ORDERS__primary_key_unique"
    assert unique.field is None
    assert not any(c.type == "field_primary_key_unique" for c in checks)


def test_primary_key_reuses_explicit_required_and_unique_checks(hana_data):
    hana_data.insert([(1, None, None)])
    schema = SchemaObject(
        name="ORDERS", properties=[SchemaProperty(name="ID", required=True, unique=True, primaryKey=True)]
    )

    checks = run_schema_checks(hana_data, "SALES", schema)

    assert [c.type for c in checks] == ["model_exists", "field_is_present", "field_required", "field_unique"]
    assert all(c.result == ResultEnum.passed for c in checks)


def test_view_fallback():
    connection = FakeConnection(catalog_response([column()], source="view"))
    schema = SchemaObject(name="ORDERS", properties=[SchemaProperty(name="ID")])

    checks = run_schema_checks(connection, "SALES", schema)

    assert check_by_type(checks, "model_exists").result == ResultEnum.passed
    assert any("FROM SYS.VIEW_COLUMNS" in sql for sql, params in connection.executed)


def test_physical_name_resolution():
    connection = FakeConnection(catalog_response([column("ORDER_ID")]))
    schema = SchemaObject(
        name="orders",
        physicalName="ORDERS",
        properties=[SchemaProperty(name="order_id", physicalName="ORDER_ID")],
    )

    checks = run_schema_checks(connection, "SALES", schema)

    assert check_by_type(checks, "field_is_present").model == "ORDERS"
    assert check_by_type(checks, "field_is_present").field == "ORDER_ID"


def test_identifier_quoting_escapes_quotes():
    assert quote_identifier('A"B') == '"A""B"'
    assert qualified_table_name('S"1', 'T"1') == '"S""1"."T""1"'
