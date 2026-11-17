import pytest

from datacontract.data_contract import DataContract
from datacontract.model.run import ResultEnum
from tests.dremio_container import PASSWORD, USERNAME, DremioContainer

dremio = DremioContainer()


@pytest.fixture(scope="module", autouse=True)
def dremio_container(request):
    dremio.start()
    request.addfinalizer(dremio.stop)


@pytest.fixture(autouse=True)
def credentials(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_DREMIO_USERNAME", USERNAME)
    monkeypatch.setenv("DATACONTRACT_DREMIO_PASSWORD", PASSWORD)


@pytest.fixture(scope="module")
def valid_orders():
    return load('"$scratch".lake.valid', "orders.sql")


@pytest.fixture(scope="module")
def invalid_orders():
    return load('"$scratch".lake.invalid', "orders_invalid.sql")


def load(folder: str, data_file: str) -> str:
    return dremio.load(folder, data_file)


def contract(schema: str) -> str:
    with open("fixtures/dremio/odcs.yaml") as file:
        quoted = "'" + schema.replace("'", "''") + "'"
        return file.read().replace("__PORT__", str(dremio.port())).replace("__SCHEMA__", quoted)


def failed_checks(run) -> dict[str, str]:
    return {check.name: check.reason for check in run.checks if check.result != ResultEnum.passed}


def test_valid_data_passes_every_check(valid_orders):
    run = DataContract(data_contract_str=contract(valid_orders)).test()

    print(run.pretty())
    assert run.result == ResultEnum.passed
    assert failed_checks(run) == {}
    # one physical type check per column
    assert len([check for check in run.checks if check.type == "field_physical_type"]) == 14


def test_each_violation_fails_its_check(invalid_orders):
    run = DataContract(data_contract_str=contract(invalid_orders)).test()

    print(run.pretty())
    assert run.result == ResultEnum.failed
    assert failed_checks(run) == {
        "Check that unique field order_id has no duplicate values": "Actual duplicate_count(order_id) was 1, expected = 0",
        "Check that field order_id matches regex pattern ^ORD-\\d{4}$": "Actual invalid_count(order_id) was 1, expected = 0",
        "Check that field customer_id has missing_count < 2": "Actual missing_count(customer_id) was 2, expected < 2",
        "Check that field order_status has invalid_count = 0": "Actual invalid_count(order_status) was 1, expected = 0",
        "Check that field order_total has a minimum of 0": "Actual invalid_count(order_total) was 1, expected = 0",
        "Check that field quantity has a minimum of 1": "Actual invalid_count(quantity) was 1, expected = 0",
        "Check that model orders has duplicate_count = 0 for columns order_id": (
            "Actual duplicate_count(orders) was 1, expected = 0"
        ),
        "No order has a negative total": "Actual custom_sql(orders) was 1, expected = 0",
        "Every order id follows the ORD-nnnn scheme": "Actual custom_sql(orders) was 1, expected = 0",
    }


def test_a_physical_type_that_differs_from_the_column_fails(valid_orders):
    wrong = (
        contract(valid_orders)
        .replace("physicalType: BIGINT", "physicalType: INTEGER")
        .replace("physicalType: DECIMAL(10,2)", "physicalType: DECIMAL(12,2)")
        .replace("physicalType: LIST<VARCHAR>", "physicalType: LIST<INTEGER>")
        .replace(
            "physicalType: STRUCT<city VARCHAR, zip VARCHAR>", "physicalType: STRUCT<city VARCHAR, postcode VARCHAR>"
        )
    )

    run = DataContract(data_contract_str=wrong).test()

    assert failed_checks(run) == {
        "Check that field line_count has physical type INTEGER": (
            "expected physical type 'INTEGER' but the column is 'BIGINT'"
        ),
        "Check that field order_total has physical type DECIMAL(12,2)": (
            "expected physical type 'DECIMAL(12,2)' but the column is 'DECIMAL(10,2)'"
        ),
        "Check that field tags has physical type LIST<INTEGER>": (
            "expected physical type 'LIST<INTEGER>' but the column is 'ARRAY<VARCHAR>'"
        ),
        "Check that field shipping has physical type STRUCT<city VARCHAR, postcode VARCHAR>": (
            "expected physical type 'STRUCT<city VARCHAR, postcode VARCHAR>' but the column is "
            "'STRUCT<city VARCHAR, zip VARCHAR>'"
        ),
    }


def test_a_row_filter_restricts_the_row_checks(invalid_orders):
    run = DataContract(data_contract_str=contract(invalid_orders), filter="order_id LIKE 'ORD-%'").test()

    failed = failed_checks(run)
    assert "Check that field order_id matches regex pattern ^ORD-\\d{4}$" not in failed
    assert "Check that field quantity has a minimum of 1" not in failed
    # the duplicate ORD-0001 rows both pass the filter
    assert "Check that unique field order_id has no duplicate values" in failed
    assert run.filters == {"orders": "order_id LIKE 'ORD-%'"}


def test_failed_rows_are_sampled(invalid_orders):
    run = DataContract(data_contract_str=contract(invalid_orders), include_failed_samples=True).test()

    regex = next(
        check for check in run.checks if check.name == "Check that field order_id matches regex pattern ^ORD-\\d{4}$"
    )
    assert regex.failedSamples == [{"order_id": "order-3"}]


def test_a_view_deep_in_the_folders_of_a_space_is_found_by_its_name(valid_orders):
    dremio.create_folders(["shop"], ["shop", "sales"], ["shop", "sales", "marts"], ["shop", "sales", "marts", "eu"])
    dremio.client().run(f"CREATE VIEW shop.sales.marts.eu.orders AS SELECT * FROM {valid_orders}.orders")

    run = DataContract(data_contract_str=contract("shop.sales.marts.eu")).test()

    assert run.result == ResultEnum.passed, failed_checks(run)


def test_a_folder_with_a_period_in_its_name_is_named_in_quotes():
    load('"$scratch"."bucket.v1".raw', "orders.sql")

    run = DataContract(data_contract_str=contract('$scratch."bucket.v1".raw')).test()

    assert run.result == ResultEnum.passed, failed_checks(run)


def test_a_wrong_password_fails_the_connection(valid_orders, monkeypatch):
    monkeypatch.setenv("DATACONTRACT_DREMIO_PASSWORD", "wrong")

    run = DataContract(data_contract_str=contract(valid_orders)).test()

    assert run.result == ResultEnum.failed
    assert failed_checks(run)["Data Contract Tests"] == (
        "Dremio login failed (HTTP 401): Login failed: Invalid username or password, user admin"
    )


def test_an_unknown_table_fails_its_checks_with_dremios_message(valid_orders):
    run = DataContract(
        data_contract_str=contract(valid_orders).replace("physicalName: orders", "physicalName: missing")
    ).test()

    assert run.result in (ResultEnum.failed, ResultEnum.error)
    assert any("not found" in (check.reason or "") for check in run.checks)


NESTED_CONTRACT = """apiVersion: v3.1.0
kind: DataContract
id: dremio-nested
version: 1.0.0
status: active
servers:
  - server: dremio
    type: dremio
    host: localhost
    port: __PORT__
    schema: __SCHEMA__
schema:
  - name: orders
    physicalName: orders
    properties:
      - name: order_id
        logicalType: integer
        primaryKey: true
      - name: items
        logicalType: array
        items:
          logicalType: object
          properties:
            - name: sku
              logicalType: string
              required: true
              unique: true
            - name: discounts
              logicalType: array
              items:
                logicalType: object
                properties:
                  - name: code
                    logicalType: string
                    unique: true
                  - name: amount
                    logicalType: number
                    logicalTypeOptions:
                      minimum: 0
      - name: tags
        logicalType: array
        items:
          logicalType: string
          quality:
            - metric: invalidValues
              arguments:
                validValues: [new, vip]
              mustBe: 0
      - name: customer
        logicalType: object
        properties:
          - name: email
            logicalType: string
            required: true
            quality:
              - type: sql
                query: SELECT COUNT(*) FROM {model} WHERE {property} NOT LIKE '%@%'
                mustBe: 0
"""


@pytest.fixture(scope="module")
def nested_orders():
    return load('"$scratch".lake.nested', "nested_orders.sql")


def nested_contract(schema: str) -> str:
    return NESTED_CONTRACT.replace("__PORT__", str(dremio.port())).replace("__SCHEMA__", f"'{schema}'")


def test_nested_rules_fail_on_the_parent_rows_that_violate_them(nested_orders):
    run = DataContract(data_contract_str=nested_contract(nested_orders), include_failed_samples=True).test()

    print(run.pretty())
    failed = [c for c in run.checks if c.result != ResultEnum.passed]
    assert {(c.field, c.type) for c in failed} == {
        ("items[].sku", "field_required"),
        ("items[].sku", "field_unique"),
        ("items[].discounts[].code", "field_unique"),
        ("items[].discounts[].amount", "field_minimum"),
        ("tags[]", "field_invalid_values"),
        ("customer.email", "field_required"),
        ("customer.email", "field_quality_sql"),
    }
    assert all(c.result == ResultEnum.failed and c.diagnostics["value"] == 1 for c in failed)
    samples = {(c.field, c.type): [sample["order_id"] for sample in c.failedSamples or []] for c in failed}
    assert samples[("items[].sku", "field_required")] == [2]
    # one sample for each order, however many of its tags break the rule
    assert samples[("tags[]", "field_invalid_values")] == [3]
