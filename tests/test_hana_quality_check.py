import sqlite3

import pytest
from open_data_contract_standard.model import (
    DataQuality,
    OpenDataContractStandard,
    SchemaObject,
    SchemaProperty,
    ServiceLevelAgreementProperty,
)

from datacontract.engines.hana.hana_quality_check import (
    prepare_hana_query,
    run_quality_checks,
    run_sla_checks,
)
from datacontract.model.run import ResultEnum


class FakeConnection:
    def __init__(self, response=(0,)):
        self.response = response
        self.executed = []

    def cursor(self):
        return FakeCursor(self)


class FakeCursor:
    def __init__(self, connection):
        self.connection = connection

    def execute(self, sql, params=None):
        self.connection.executed.append((sql, params or []))

    def fetchone(self):
        return self.connection.response

    def close(self):
        pass


def check_by_type(checks, check_type):
    return next(check for check in checks if check.type == check_type)


def test_sql_quality_pass():
    connection = FakeConnection((5,))
    schema = SchemaObject(
        name="ORDERS",
        quality=[DataQuality(type="sql", query="SELECT COUNT(*) FROM {model}", mustBe=5)],
    )

    checks = run_quality_checks(connection, "SALES", schema)

    assert check_by_type(checks, "model_quality_sql").result == ResultEnum.passed
    assert connection.executed[0][0] == 'SELECT COUNT(*) FROM "SALES"."ORDERS"'


def test_sql_quality_fail():
    connection = FakeConnection((4,))
    schema = SchemaObject(
        name="ORDERS",
        quality=[DataQuality(type="sql", query="SELECT COUNT(*) FROM {model}", mustBe=5)],
    )

    checks = run_quality_checks(connection, "SALES", schema)

    assert check_by_type(checks, "model_quality_sql").result == ResultEnum.failed


@pytest.mark.parametrize("query", ["DELETE FROM {model}", "SELECT 1 FROM {model}; DROP TABLE ORDERS"])
def test_sql_quality_refuses_writes_and_multiple_statements(query):
    connection = FakeConnection((0,))
    schema = SchemaObject(name="ORDERS", quality=[DataQuality(type="sql", query=query, mustBe=0)])

    checks = run_quality_checks(connection, "SALES", schema)

    check = check_by_type(checks, "model_quality_sql")
    assert check.result == ResultEnum.failed
    assert "read-only query" in check.reason
    assert connection.executed == []


def test_sql_quality_threshold_operators():
    cases = [
        (DataQuality(type="sql", query="SELECT 5 FROM {model}", mustNotBe=4), 5, ResultEnum.passed),
        (DataQuality(type="sql", query="SELECT 5 FROM {model}", mustBeGreaterThan=4), 5, ResultEnum.passed),
        (DataQuality(type="sql", query="SELECT 5 FROM {model}", mustBeGreaterOrEqualTo=5), 5, ResultEnum.passed),
        (DataQuality(type="sql", query="SELECT 5 FROM {model}", mustBeLessThan=6), 5, ResultEnum.passed),
        (DataQuality(type="sql", query="SELECT 5 FROM {model}", mustBeLessOrEqualTo=5), 5, ResultEnum.passed),
        (DataQuality(type="sql", query="SELECT 5 FROM {model}", mustBeBetween=[1, 5]), 5, ResultEnum.passed),
        (DataQuality(type="sql", query="SELECT 5 FROM {model}", mustNotBeBetween=[6, 9]), 5, ResultEnum.passed),
        (DataQuality(type="sql", query="SELECT 5 FROM {model}", mustBeGreaterThan=5), 5, ResultEnum.failed),
    ]

    for quality, value, expected in cases:
        connection = FakeConnection((value,))
        schema = SchemaObject(name="ORDERS", quality=[quality])

        checks = run_quality_checks(connection, "SALES", schema)

        assert check_by_type(checks, "model_quality_sql").result == expected


def test_row_count():
    connection = FakeConnection((10,))
    schema = SchemaObject(name="ORDERS", quality=[DataQuality(metric="rowCount", mustBe=10)])

    checks = run_quality_checks(connection, "SALES", schema)

    assert check_by_type(checks, "row_count").result == ResultEnum.passed
    assert connection.executed[0][0] == 'SELECT COUNT(*) FROM "SALES"."ORDERS"'


@pytest.mark.parametrize(
    "values,duplicates", [(["A", None], 0), (["A", "A", "A", "B", "B"], 2), ([None, None], 1), ([], 0)]
)
def test_duplicate_values_field_counts_keys(percent_connection, values, duplicates):
    percent_connection.executemany("INSERT INTO SALES.ORDERS VALUES (?)", [(value,) for value in values])
    prop = SchemaProperty(name="STATUS", quality=[DataQuality(metric="duplicateValues", mustBe=duplicates)])
    schema = SchemaObject(name="ORDERS", properties=[prop])

    checks = run_quality_checks(percent_connection, "SALES", schema)

    assert check_by_type(checks, "field_duplicate_values").result == ResultEnum.passed
    assert check_by_type(checks, "field_duplicate_values").diagnostics["value"] == duplicates


def test_duplicate_values_model_counts_tuples_with_physical_names(percent_connection):
    percent_connection.execute("ALTER TABLE SALES.ORDERS ADD COLUMN LINE_NO INTEGER")
    percent_connection.executemany(
        "INSERT INTO SALES.ORDERS VALUES (?, ?)",
        [
            ("A", 1),
            ("A", 1),
            ("A", 1),
            ("A", 2),
            ("B", 1),
            (None, None),
            (None, None),
        ],
    )
    quality = DataQuality(metric="duplicateValues", arguments={"properties": ["status", "line"]}, mustBe=2)
    schema = SchemaObject(
        name="orders",
        physicalName="ORDERS",
        quality=[quality],
        properties=[
            SchemaProperty(name="status", physicalName="STATUS"),
            SchemaProperty(name="line", physicalName="LINE_NO"),
        ],
    )

    checks = run_quality_checks(percent_connection, "SALES", schema)

    check = check_by_type(checks, "model_duplicate_values")
    assert check.result == ResultEnum.passed
    assert check.diagnostics["value"] == 2


@pytest.mark.parametrize(
    "severity,expected",
    [
        ("warning", ResultEnum.warning),
        ("WARN", ResultEnum.warning),
        (" info ", ResultEnum.warning),
        ("low", ResultEnum.warning),
        ("minor", ResultEnum.warning),
        ("trivial", ResultEnum.warning),
        (None, ResultEnum.failed),
        ("critical", ResultEnum.failed),
        ("error", ResultEnum.failed),
    ],
)
@pytest.mark.parametrize("kind", ["sql", "count", "percent"])
def test_quality_failures_honor_severity(percent_connection, kind, severity, expected):
    percent_connection.executemany("INSERT INTO SALES.ORDERS VALUES (?)", [(None,), ("OK",)])
    quality = (
        DataQuality(type="sql", query="SELECT COUNT(*) FROM {model} WHERE {field} IS NULL", mustBe=0, severity=severity)
        if kind == "sql"
        else DataQuality(
            metric="nullValues", unit="percent" if kind == "percent" else "rows", mustBe=0, severity=severity
        )
    )
    schema = SchemaObject(name="ORDERS", properties=[SchemaProperty(name="STATUS", quality=[quality])])

    check = run_quality_checks(percent_connection, "SALES", schema)[0]

    assert check.result == expected
    assert check.diagnostics.get("severity") == severity


def test_warning_severity_does_not_hide_query_errors(percent_connection):
    quality = DataQuality(type="sql", query="SELECT COUNT(*) FROM SALES.MISSING", mustBe=0, severity="warning")
    schema = SchemaObject(name="ORDERS", quality=[quality])

    check = run_quality_checks(percent_connection, "SALES", schema)[0]

    assert check.result == ResultEnum.error


def test_warning_severity_keeps_a_passing_check_passed(percent_connection):
    quality = DataQuality(metric="rowCount", mustBe=0, severity="warning")

    check = run_quality_checks(percent_connection, "SALES", SchemaObject(name="ORDERS", quality=[quality]))[0]

    assert check.result == ResultEnum.passed


def test_null_values():
    connection = FakeConnection((0,))
    prop = SchemaProperty(name="ID", quality=[DataQuality(metric="nullValues", mustBe=0)])
    schema = SchemaObject(name="ORDERS", properties=[prop])

    checks = run_quality_checks(connection, "SALES", schema)

    assert check_by_type(checks, "field_null_values").result == ResultEnum.passed
    assert '"ID" IS NULL' in connection.executed[0][0]


@pytest.fixture
def percent_connection():
    connection = sqlite3.connect(":memory:")
    connection.execute("ATTACH DATABASE ':memory:' AS SALES")
    connection.execute("CREATE TABLE SALES.ORDERS (STATUS TEXT)")
    try:
        yield connection
    finally:
        connection.close()


@pytest.mark.parametrize(
    "metric,arguments,values,threshold,expected_percent,expected_result",
    [
        ("nullValues", {}, [None, "OK"], 5, 50.0, ResultEnum.failed),
        ("nullValues", {}, [None] * 10 + ["OK"] * 990, 5, 1.0, ResultEnum.passed),
        ("missingValues", {"missingValues": ["N/A"]}, [None, "N/A", "OK", "OK"], 25, 50.0, ResultEnum.failed),
        ("invalidValues", {"validValues": ["OK"]}, ["BAD", "OK"], 5, 50.0, ResultEnum.failed),
        ("nullValues", {}, [], 0, 0.0, ResultEnum.passed),
        ("nullValues", {}, [None, "OK", "OK"], 33.333333, 33.333333, ResultEnum.passed),
    ],
)
def test_percent_thresholds_compare_the_fraction_of_rows(
    percent_connection,
    metric,
    arguments,
    values,
    threshold,
    expected_percent,
    expected_result,
):
    percent_connection.executemany("INSERT INTO SALES.ORDERS VALUES (?)", [(value,) for value in values])
    schema = SchemaObject(
        name="orders",
        physicalName="ORDERS",
        properties=[
            SchemaProperty(
                name="status",
                physicalName="STATUS",
                quality=[
                    DataQuality(metric=metric, arguments=arguments, unit="percent", mustBeLessOrEqualTo=threshold),
                ],
            ),
        ],
    )

    checks = run_quality_checks(percent_connection, "SALES", schema)

    assert len(checks) == 1
    check = checks[0]
    assert check.result == expected_result
    assert check.diagnostics["unit"] == "percent"
    assert check.diagnostics["percent"] == expected_percent
    assert check.diagnostics["row_count"] == len(values)
    assert check.diagnostics["value"] == sum(value != "OK" for value in values)
    if expected_result == ResultEnum.failed:
        assert f"{expected_percent}%" in check.reason
        assert f"of {len(values)} rows" in check.reason


@pytest.mark.parametrize("unit", ["%", "percentage", " Percent "])
def test_percent_unit_aliases(percent_connection, unit):
    percent_connection.executemany("INSERT INTO SALES.ORDERS VALUES (?)", [(None,), ("OK",)])
    schema = SchemaObject(
        name="ORDERS",
        properties=[
            SchemaProperty(
                name="STATUS",
                quality=[
                    DataQuality(metric="nullValues", unit=unit, mustBeLessThan=5),
                ],
            )
        ],
    )

    check = run_quality_checks(percent_connection, "SALES", schema)[0]

    assert check.result == ResultEnum.failed
    assert check.diagnostics["percent"] == 50.0


def test_percent_unit_on_row_count_keeps_absolute_count_and_warns(caplog):
    connection = FakeConnection((10,))
    schema = SchemaObject(name="ORDERS", quality=[DataQuality(metric="rowCount", unit="percent", mustBe=10)])

    check = run_quality_checks(connection, "SALES", schema)[0]

    assert check.result == ResultEnum.passed
    assert "percent" not in check.diagnostics
    assert "does not support unit: percent" in caplog.text
    assert len(connection.executed) == 1


def test_sql_percent_result_is_not_normalized_again():
    connection = FakeConnection((50,))
    schema = SchemaObject(
        name="ORDERS",
        quality=[
            DataQuality(
                type="sql",
                query="SELECT 50 FROM {model}",
                unit="percent",
                mustBe=50,
            )
        ],
    )

    check = run_quality_checks(connection, "SALES", schema)[0]

    assert check.result == ResultEnum.passed
    assert len(connection.executed) == 1


def test_invalid_values():
    connection = FakeConnection((0,))
    quality = DataQuality(metric="invalidValues", arguments={"validValues": ["OPEN", "PAID"]}, mustBe=0)
    prop = SchemaProperty(name="STATUS", quality=[quality])
    schema = SchemaObject(name="ORDERS", properties=[prop])

    checks = run_quality_checks(connection, "SALES", schema)

    assert check_by_type(checks, "field_invalid_values").result == ResultEnum.passed
    assert connection.executed[0][1] == ["OPEN", "PAID"]


def test_missing_values():
    connection = FakeConnection((2,))
    quality = DataQuality(metric="missingValues", arguments={"missingValues": ["", "N/A", None]}, mustBe=0)
    prop = SchemaProperty(name="STATUS", quality=[quality])
    schema = SchemaObject(name="ORDERS", properties=[prop])

    checks = run_quality_checks(connection, "SALES", schema)

    assert check_by_type(checks, "field_missing_values").result == ResultEnum.failed
    assert connection.executed[0][1] == ["", "N/A"]
    assert '"STATUS" IS NULL OR "STATUS" IN (?, ?)' in connection.executed[0][0]


def test_custom_sodacl_warning():
    quality = DataQuality(type="custom", engine="soda", implementation="checks for ORDERS: []")
    schema = SchemaObject(name="ORDERS", quality=[quality])

    checks = run_quality_checks(FakeConnection(), "SALES", schema)

    assert check_by_type(checks, "quality_custom_soda").result == ResultEnum.warning


def test_freshness_check():
    connection = FakeConnection((60,))
    contract = OpenDataContractStandard(
        id="hana-test",
        schema=[SchemaObject(name="ORDERS", properties=[SchemaProperty(name="UPDATED_AT")])],
        slaProperties=[
            ServiceLevelAgreementProperty(property="freshness", element="ORDERS.UPDATED_AT", value=5, unit="m")
        ],
    )

    checks = run_sla_checks(connection, "SALES", contract)

    assert check_by_type(checks, "servicelevel_freshness").result == ResultEnum.passed
    assert "SECONDS_BETWEEN(MAX" in connection.executed[0][0]


def test_retention_check():
    connection = FakeConnection((4000,))
    contract = OpenDataContractStandard(
        id="hana-test",
        schema=[SchemaObject(name="ORDERS", properties=[SchemaProperty(name="CREATED_AT")])],
        slaProperties=[
            ServiceLevelAgreementProperty(property="retention", element="ORDERS.CREATED_AT", value=2, unit="h")
        ],
    )

    checks = run_sla_checks(connection, "SALES", contract)

    assert check_by_type(checks, "servicelevel_retention").result == ResultEnum.passed
    assert "SECONDS_BETWEEN(MIN" in connection.executed[0][0]


def test_query_placeholder_replacement():
    placeholders = [
        "{model}",
        "${model}",
        '"{model}"',
        "'${model}'",
        "{table}",
        "{object}",
    ]
    for placeholder in placeholders:
        assert prepare_hana_query(f"SELECT * FROM {placeholder}", "SALES", "ORDERS") == 'SELECT * FROM "SALES"."ORDERS"'

    assert prepare_hana_query("SELECT * FROM {schema}", "SALES", "ORDERS") == 'SELECT * FROM "SALES"'
    assert prepare_hana_query("SELECT {field}, {column}, {property} FROM {model}", "SALES", "ORDERS", "ID") == (
        'SELECT "ID", "ID", "ID" FROM "SALES"."ORDERS"'
    )


def test_identifier_quoting_escapes_quotes():
    query = prepare_hana_query("SELECT {field} FROM {model}", 'S"1', 'T"1', 'C"1')

    assert query == 'SELECT "C""1" FROM "S""1"."T""1"'
