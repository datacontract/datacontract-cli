import pytest
from testcontainers.postgres import PostgresContainer

from datacontract.data_contract import DataContract
from datacontract.model.exceptions import DataContractException

# logging.basicConfig(level=logging.DEBUG, force=True)


postgres = PostgresContainer("postgres:16")


@pytest.fixture(scope="function", autouse=True)
def postgres_container(request):
    postgres.start()

    def remove_container():
        postgres.stop()

    request.addfinalizer(remove_container)


def test_test_postgres(postgres_container, monkeypatch):
    monkeypatch.setenv("DATACONTRACT_POSTGRES_USERNAME", postgres.username)
    monkeypatch.setenv("DATACONTRACT_POSTGRES_PASSWORD", postgres.password)
    _init_sql("fixtures/postgres/data/data.sql")

    datacontract_file = "fixtures/postgres/datacontract.yaml"
    data_contract_str = _setup_datacontract(datacontract_file)
    data_contract = DataContract(data_contract_str=data_contract_str)

    run = data_contract.test()

    print(run)
    assert run.result == "passed"
    assert all(check.result == "passed" for check in run.checks)


def test_test_postgres_odcs(postgres_container, monkeypatch):
    monkeypatch.setenv("DATACONTRACT_POSTGRES_USERNAME", postgres.username)
    monkeypatch.setenv("DATACONTRACT_POSTGRES_PASSWORD", postgres.password)
    _init_sql("fixtures/postgres/data/data.sql")

    datacontract_file = "fixtures/postgres/odcs.yaml"
    data_contract_str = _setup_datacontract(datacontract_file)
    data_contract = DataContract(data_contract_str=data_contract_str)

    run = data_contract.test()

    print(run.pretty())
    assert run.result == "passed"
    assert all(check.result == "passed" for check in run.checks)


def test_test_postgres_case_sensitive_table_name(postgres_container, monkeypatch):
    monkeypatch.setenv("DATACONTRACT_POSTGRES_USERNAME", postgres.username)
    monkeypatch.setenv("DATACONTRACT_POSTGRES_PASSWORD", postgres.password)
    _init_sql("fixtures/postgres/data/data_case_sensitive.sql")

    datacontract_file = "fixtures/postgres/datacontract_case_sensitive.yaml"
    data_contract_str = _setup_datacontract(datacontract_file)
    data_contract = DataContract(data_contract_str=data_contract_str)

    run = data_contract.test()

    print(run)
    assert run.result == "passed"
    assert all(check.result == "passed" for check in run.checks)


def _setup_datacontract(file):
    with open(file) as data_contract_file:
        data_contract_str = data_contract_file.read()
    port = postgres.get_exposed_port(5432)
    data_contract_str = data_contract_str.replace("5432", port)
    return data_contract_str


def _init_sql(file_path):
    try:
        import psycopg2
    except ImportError as e:
        raise DataContractException(
            type="schema",
            result="failed",
            name="postgres extra missing",
            reason="Install the extra datacontract-cli[postgres] to use postgres",
            engine="datacontract",
            original_exception=e,
        )

    connection = psycopg2.connect(
        database=postgres.dbname,
        user=postgres.username,
        password=postgres.password,
        # database=postgres.dbname,
        # user=postgres.username,
        # password=postgres.password,
        host=postgres.get_container_host_ip(),
        port=postgres.get_exposed_port(5432),
    )
    cursor = connection.cursor()
    with open(file_path, "r") as sql_file:
        sql_commands = sql_file.read()
        cursor.execute(sql_commands)
    connection.commit()
    cursor.close()
    connection.close()
