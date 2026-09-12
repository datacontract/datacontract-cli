from open_data_contract_standard.model import SchemaObject, SchemaProperty

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


def test_field_required_nullable_false():
    connection = FakeConnection(catalog_response([column(nullable="FALSE")]))
    schema = SchemaObject(name="ORDERS", properties=[SchemaProperty(name="ID", required=True)])

    checks = run_schema_checks(connection, "SALES", schema)

    assert check_by_type(checks, "field_required").result == ResultEnum.passed


def test_field_required_nullable_true():
    connection = FakeConnection(catalog_response([column(nullable="TRUE")]))
    schema = SchemaObject(name="ORDERS", properties=[SchemaProperty(name="ID", required=True)])

    checks = run_schema_checks(connection, "SALES", schema)

    assert check_by_type(checks, "field_required").result == ResultEnum.failed


def test_field_unique_pass():
    connection = FakeConnection(catalog_response([column()]) + [(has_sql("COUNT(*) - COUNT(DISTINCT"), [(0,)])])
    schema = SchemaObject(name="ORDERS", properties=[SchemaProperty(name="ID", unique=True)])

    checks = run_schema_checks(connection, "SALES", schema)

    assert check_by_type(checks, "field_unique").result == ResultEnum.passed


def test_field_unique_fail():
    connection = FakeConnection(catalog_response([column()]) + [(has_sql("COUNT(*) - COUNT(DISTINCT"), [(2,)])])
    schema = SchemaObject(name="ORDERS", properties=[SchemaProperty(name="ID", unique=True)])

    checks = run_schema_checks(connection, "SALES", schema)

    assert check_by_type(checks, "field_unique").result == ResultEnum.failed


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


def test_field_regex_uses_like_regexpr():
    connection = FakeConnection(catalog_response([column("EMAIL", "NVARCHAR")]) + [(has_sql("LIKE_REGEXPR"), [(0,)])])
    prop = SchemaProperty(name="EMAIL", logicalType="string", logicalTypeOptions={"pattern": ".*@example.com"})
    schema = SchemaObject(name="ORDERS", properties=[prop])

    checks = run_schema_checks(connection, "SALES", schema)

    assert check_by_type(checks, "field_regex").result == ResultEnum.passed
    assert "LIKE_REGEXPR" in connection.executed[-1][0]


def test_primary_key_table():
    responses = catalog_response([column()]) + [(has_sql("FROM SYS.CONSTRAINTS"), [("ID",)])]
    connection = FakeConnection(responses)
    schema = SchemaObject(name="ORDERS", properties=[SchemaProperty(name="ID", primaryKey=True)])

    checks = run_schema_checks(connection, "SALES", schema)

    assert check_by_type(checks, "field_primary_key").result == ResultEnum.passed


def test_primary_key_view_warning():
    connection = FakeConnection(catalog_response([column()], source="view"))
    schema = SchemaObject(name="ORDERS", properties=[SchemaProperty(name="ID", primaryKey=True)])

    checks = run_schema_checks(connection, "SALES", schema)

    assert check_by_type(checks, "field_primary_key").result == ResultEnum.warning


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
