"""Smoke test for the Redshift test path against a Postgres testcontainer.

Redshift has no dedicated ibis backend; it rides the Postgres backend over the
Postgres wire protocol (see ``connect_ibis``), with two compatibility patches on
top: tables are qualified with the configured ``schema`` (#1338) and the column
introspection query is rewritten to drop the ``pg_catalog.pg_enum`` join that
Redshift does not expose (``redshift_patch``).

No real Redshift is reachable in CI, so this exercises the full ``type: redshift``
code path — connect branch, schema-qualified introspection, the pg_enum-free
``get_schema``, the batched aggregations, a pattern check, and custom SQL quality
checks — against a wire-compatible Postgres. It proves the redshift branch and
the patched introspection produce correct schemas and a passing run end-to-end;
it cannot catch Redshift-only dialect divergences (POSIX regex, temp-view-backed
``con.sql`` falling back to ``raw_sql``), which need a live cluster.
"""

import pytest
from testcontainers.postgres import PostgresContainer

from datacontract.data_contract import DataContract
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import ResultEnum

postgres = PostgresContainer("postgres:16")


@pytest.fixture(scope="function", autouse=True)
def postgres_container(request):
    postgres.start()

    def remove_container():
        postgres.stop()

    request.addfinalizer(remove_container)


def test_test_redshift_path_via_postgres_wire(postgres_container, monkeypatch):
    monkeypatch.setenv("DATACONTRACT_REDSHIFT_USERNAME", postgres.username)
    monkeypatch.setenv("DATACONTRACT_REDSHIFT_PASSWORD", postgres.password)
    _init_sql("fixtures/postgres/data/data.sql")

    data_contract_str = _setup_datacontract("fixtures/redshift/odcs.yaml")
    data_contract = DataContract(data_contract_str=data_contract_str)

    run = data_contract.test()

    print(run.pretty())
    assert run.result == "passed"
    assert all(check.result == ResultEnum.passed for check in run.checks)


def _setup_datacontract(file):
    with open(file) as data_contract_file:
        data_contract_str = data_contract_file.read()
    port = postgres.get_exposed_port(5432)
    # The fixture uses the default Redshift port 5439 as a placeholder.
    return data_contract_str.replace("5439", str(port))


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
        host=postgres.get_container_host_ip(),
        port=postgres.get_exposed_port(5432),
    )
    cursor = connection.cursor()
    with open(file_path, "r") as sql_file:
        cursor.execute(sql_file.read())
    connection.commit()
    cursor.close()
    connection.close()
