import pytest
from testcontainers.postgres import PostgresContainer

from datacontract.data_contract import DataContract
from datacontract.model.run import ResultEnum

postgres = PostgresContainer("postgres:16")


@pytest.fixture(scope="function")
def postgres_container(request):
    postgres.start()
    request.addfinalizer(postgres.stop)


def test_failing_minimum_check_attaches_row_sample(postgres_container, monkeypatch):
    monkeypatch.setenv("DATACONTRACT_POSTGRES_USERNAME", postgres.username)
    monkeypatch.setenv("DATACONTRACT_POSTGRES_PASSWORD", postgres.password)
    _init_sql("fixtures/quality-samples/data/data.sql")

    data_contract_str = _setup_datacontract("fixtures/quality-samples/datacontract.yaml")
    run = DataContract(data_contract_str=data_contract_str).test()

    assert run.result == ResultEnum.failed

    minimum_check = next(
        (c for c in run.checks if c.type == "field_minimum" and c.field == "order_total"),
        None,
    )
    assert minimum_check is not None, "Expected a field_minimum check on order_total"
    assert minimum_check.result == ResultEnum.failed

    # Structured samples: the bad row should be captured with its actual values.
    assert minimum_check.failed_rows_samples, (
        "Expected failed_rows_samples to contain at least the offending row, "
        f"got: {minimum_check.failed_rows_samples!r}"
    )
    sample = minimum_check.failed_rows_samples[0]
    assert sample.get("order_id") == "O-BAD123"
    assert str(sample.get("order_total")) == "-5" or str(sample.get("order_total")) == "-5.0"

    # Inline summary in reason: user should see the offending value without
    # needing to open the JSON output.
    assert "order_total" in minimum_check.reason
    assert "-5" in minimum_check.reason


def _setup_datacontract(file):
    with open(file) as f:
        data_contract_str = f.read()
    port = postgres.get_exposed_port(5432)
    return data_contract_str.replace("5432", str(port))


def _init_sql(file_path):
    import psycopg2

    connection = psycopg2.connect(
        database=postgres.dbname,
        user=postgres.username,
        password=postgres.password,
        host=postgres.get_container_host_ip(),
        port=postgres.get_exposed_port(5432),
    )
    try:
        with connection.cursor() as cursor, open(file_path) as f:
            cursor.execute(f.read())
        connection.commit()
    finally:
        connection.close()
