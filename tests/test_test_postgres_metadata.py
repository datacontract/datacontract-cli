import psycopg2
import pytest
from testcontainers.postgres import PostgresContainer

from datacontract.data_contract import DataContract

postgres = PostgresContainer("postgres:16")


@pytest.fixture(scope="module")
def postgres_container():
    with postgres:
        yield postgres


@pytest.fixture
def execute(postgres_container, monkeypatch):
    monkeypatch.setenv("DATACONTRACT_POSTGRES_USERNAME", postgres.username)
    monkeypatch.setenv("DATACONTRACT_POSTGRES_PASSWORD", postgres.password)
    connection = psycopg2.connect(
        host=postgres.get_container_host_ip(),
        port=postgres.get_exposed_port(5432),
        user=postgres.username,
        password=postgres.password,
        dbname=postgres.dbname,
    )
    connection.autocommit = True
    with connection.cursor() as cursor:
        cursor.execute("DROP SCHEMA public CASCADE; CREATE SCHEMA public;")
        yield cursor.execute
    connection.close()


def _contract():
    with open("fixtures/postgres-metadata/datacontract.yaml") as f:
        return f.read().replace("5432", str(postgres.get_exposed_port(5432)))


def test_catalog_views_are_checked(execute):
    execute("CREATE TABLE orders (id int); INSERT INTO orders VALUES (1), (2); ANALYZE orders;")

    run = DataContract(data_contract_str=_contract()).test()

    assert run.result == "passed", [(c.name, c.reason) for c in run.checks if c.result != "passed"]
    assert {c.field for c in run.checks if c.field} == {"relname", "n_live_tup", "last_analyze"}


def test_catalog_view_violations_fail(execute):
    execute("CREATE TABLE orders (id int); ANALYZE orders; CREATE TABLE customers (id int);")

    run = DataContract(data_contract_str=_contract()).test()

    failed = [c for c in run.checks if c.result != "passed"]
    assert [(c.type, c.field) for c in failed] == [("field_required", "last_analyze")]
    assert failed[0].reason.endswith("was 1, expected = 0")


def test_catalog_schema_wins_over_the_configured_schema(execute, monkeypatch):
    execute("CREATE TABLE orders (id int); ANALYZE orders;")
    monkeypatch.setenv("DATACONTRACT_POSTGRES_SCHEMA", "public")

    run = DataContract(data_contract_str=_contract()).test()

    assert run.result == "passed", [(c.name, c.reason) for c in run.checks if c.result != "passed"]
