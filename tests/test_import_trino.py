"""Tests for the Trino importer, run against a real Trino container.

The container helper is the one the other Trino suite uses: waiting for the logs
is not enough, the catalog has to answer.
"""

import pytest
import trino as trino_client

from datacontract.data_contract import DataContract
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import ResultEnum
from tests.test_test_trino import TrinoContainer

TRINO_PORT = 8080
CATALOG = "memory"
SCHEMA = "shop"

SEED = [
    f"CREATE SCHEMA IF NOT EXISTS {CATALOG}.{SCHEMA}",
    f"""CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.orders (
          order_id varchar(36), order_total decimal(10,2), line_count integer,
          ordered_at timestamp(3), tags array(varchar), notes varchar)""",
    f"INSERT INTO {CATALOG}.{SCHEMA}.orders VALUES ('CX-263-DU', 50.00, 2, current_timestamp(3), ARRAY['a'], 'hi')",
    f"CREATE TABLE IF NOT EXISTS {CATALOG}.{SCHEMA}.customers (id integer)",
]

trino_container = TrinoContainer()


@pytest.fixture(scope="module")
def trino_server(request):
    trino_container.start()
    request.addfinalizer(trino_container.stop)
    _seed()


@pytest.fixture
def credentials(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_TRINO_USERNAME", "my_user")
    monkeypatch.setenv("DATACONTRACT_TRINO_PASSWORD", "")


def _port():
    return int(trino_container.get_exposed_port(TRINO_PORT))


def _seed():
    connection = trino_client.dbapi.connect(
        host=trino_container.get_container_host_ip(), port=_port(), user="my_user", catalog=CATALOG
    )
    cursor = connection.cursor()
    for statement in SEED:
        cursor.execute(statement)
        cursor.fetchall()
    connection.close()


def _import(**kwargs):
    kwargs.setdefault("catalog", CATALOG)
    kwargs.setdefault("schema", SCHEMA)
    kwargs.setdefault("port", _port())
    return DataContract.import_from_source("trino", trino_container.get_container_host_ip(), **kwargs)


def test_import_trino_takes_the_declared_type_verbatim(trino_server, credentials):
    result = _import(trino_table=["orders"])
    types = {prop.name: prop.physicalType for prop in result.schema_[0].properties}

    assert types == {
        "order_id": "varchar(36)",
        "order_total": "decimal(10,2)",
        "line_count": "integer",
        "ordered_at": "timestamp(3)",
        "tags": "array(varchar)",
        "notes": "varchar",
    }


def test_imported_contract_passes_test_without_editing(trino_server, credentials):
    """The point of the native import: import, then test, no hand-editing."""
    result = _import(trino_table=["orders"])

    run = DataContract(data_contract_str=result.to_yaml()).test()

    print(run.pretty())
    assert run.result == ResultEnum.passed


def test_a_wrong_physical_type_is_caught(trino_server, credentials):
    """Trino's information_schema has no length columns, so asking for them used
    to fail the whole query and skip this check silently."""
    result = _import(trino_table=["orders"])
    result.schema_[0].properties[0].physicalType = "integer"

    run = DataContract(data_contract_str=result.to_yaml()).test()

    assert run.result == ResultEnum.failed
    assert any("varchar(36)" in (check.reason or "") for check in run.checks)


def test_import_trino_produces_a_valid_contract(trino_server, credentials):
    result = _import()

    assert DataContract(data_contract_str=result.to_yaml()).lint().result == ResultEnum.passed


def test_import_trino_imports_all_tables_by_default(trino_server, credentials):
    result = _import()

    assert [schema.name for schema in result.schema_] == ["customers", "orders"]


def test_import_trino_fails_on_an_unknown_table(trino_server, credentials):
    with pytest.raises(DataContractException) as exc_info:
        _import(trino_table=["does_not_exist"])

    assert "No tables found" in exc_info.value.reason


def test_import_trino_requires_a_catalog():
    with pytest.raises(DataContractException) as exc_info:
        DataContract.import_from_source("trino", "localhost", schema="s")

    assert "catalog is required" in exc_info.value.reason


def test_import_trino_requires_a_schema():
    with pytest.raises(DataContractException) as exc_info:
        DataContract.import_from_source("trino", "localhost", catalog="c")

    assert "schema is required" in exc_info.value.reason


def test_import_trino_requires_a_host():
    with pytest.raises(DataContractException) as exc_info:
        DataContract.import_from_source("trino", None, catalog="c", schema="s")

    assert "host is required" in exc_info.value.reason
