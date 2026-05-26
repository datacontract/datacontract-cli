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


def test_duplicate_values_field():
    connection = FakeConnection((0,))
    prop = SchemaProperty(name="ID", quality=[DataQuality(metric="duplicateValues", mustBe=0)])
    schema = SchemaObject(name="ORDERS", properties=[prop])

    checks = run_quality_checks(connection, "SALES", schema)

    assert check_by_type(checks, "field_duplicate_values").result == ResultEnum.passed
    assert 'COUNT(DISTINCT "ID")' in connection.executed[0][0]


def test_duplicate_values_model():
    connection = FakeConnection((1,))
    quality = DataQuality(metric="duplicateValues", arguments={"properties": ["ID", "STATUS"]}, mustBe=0)
    schema = SchemaObject(name="ORDERS", quality=[quality])

    checks = run_quality_checks(connection, "SALES", schema)

    assert check_by_type(checks, "model_duplicate_values").result == ResultEnum.failed
    assert 'COUNT(DISTINCT "ID", "STATUS")' in connection.executed[0][0]


def test_null_values():
    connection = FakeConnection((0,))
    prop = SchemaProperty(name="ID", quality=[DataQuality(metric="nullValues", mustBe=0)])
    schema = SchemaObject(name="ORDERS", properties=[prop])

    checks = run_quality_checks(connection, "SALES", schema)

    assert check_by_type(checks, "field_null_values").result == ResultEnum.passed
    assert '"ID" IS NULL' in connection.executed[0][0]


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
