"""Tests for the Oracle importer, run against a real Oracle XE container.

Marked slow like the other Oracle suite: the image is large, so these run in the
dedicated CI job rather than on every invocation.
"""

import pytest
from testcontainers.oracle import OracleDbContainer

from datacontract.data_contract import DataContract
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import ResultEnum

# XE 21c: pre-23ai, and freely available unlike 19c.
oracleContainer = OracleDbContainer("gvenzl/oracle-xe:21-slim-faststart")
ORACLE_SERVER_PORT = 1521
# XE's pluggable-database service name differs from oracle-free's FREEPDB1.
_XE_SERVICE_NAME = "XEPDB1"
SCHEMA = "SYSTEM"

SEED = [
    """CREATE TABLE orders (
         order_id VARCHAR2(36) NOT NULL PRIMARY KEY,
         order_total NUMBER(10,2),
         line_count NUMBER(10) NOT NULL,
         ordered_at TIMESTAMP,
         notes CLOB,
         created_on DATE
       )""",
    "INSERT INTO orders VALUES ('CX-263-DU', 50.00, 2, SYSTIMESTAMP, 'hello', SYSDATE)",
    "CREATE TABLE customers (id NUMBER(10) NOT NULL PRIMARY KEY)",
    "CREATE VIEW open_orders AS SELECT order_id FROM orders WHERE line_count > 1",
]


@pytest.fixture(scope="module")
def oracle_container(request):
    oracleContainer.start()
    request.addfinalizer(oracleContainer.stop)
    _seed()


@pytest.fixture
def credentials(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_ORACLE_USERNAME", SCHEMA)
    monkeypatch.setenv("DATACONTRACT_ORACLE_PASSWORD", oracleContainer.oracle_password)


def _seed():
    import oracledb

    connection = oracledb.connect(
        user=SCHEMA,
        password=oracleContainer.oracle_password,
        dsn=f"{oracleContainer.get_container_host_ip()}:"
        f"{oracleContainer.get_exposed_port(ORACLE_SERVER_PORT)}/{_XE_SERVICE_NAME}",
    )
    cursor = connection.cursor()
    for statement in SEED:
        cursor.execute(statement)
    connection.commit()
    connection.close()


def _import(**kwargs):
    kwargs.setdefault("service_name", _XE_SERVICE_NAME)
    kwargs.setdefault("schema", SCHEMA)
    kwargs.setdefault("port", oracleContainer.get_exposed_port(ORACLE_SERVER_PORT))
    return DataContract.import_from_source("oracle", oracleContainer.get_container_host_ip(), **kwargs)


@pytest.mark.slow
def test_import_oracle_reconstructs_the_declared_types(oracle_container, credentials):
    """Oracle reports DATA_LENGTH for every column; only some types carry it."""
    result = _import(oracle_table=["ORDERS"])
    types = {prop.name: prop.physicalType for prop in result.schema_[0].properties}

    assert types == {
        "ORDER_ID": "VARCHAR2(36)",
        "ORDER_TOTAL": "NUMBER(10,2)",
        "LINE_COUNT": "NUMBER(10)",
        "ORDERED_AT": "TIMESTAMP(6)",
        # DATE reports length 7 and CLOB 4000; neither belongs in the type
        "NOTES": "CLOB",
        "CREATED_ON": "DATE",
    }


@pytest.mark.slow
def test_catalog_numbers_are_plain_integers(oracle_container, credentials):
    """Oracle returns Decimal, which YAML would write as a Python-specific tag."""
    result = _import(oracle_table=["ORDERS"])

    assert "!!python" not in result.to_yaml()
    order_id = result.schema_[0].properties[0]
    assert order_id.logicalTypeOptions["maxLength"] == 36
    assert isinstance(order_id.logicalTypeOptions["maxLength"], int)


@pytest.mark.slow
def test_imported_contract_passes_test_without_editing(oracle_container, credentials):
    """The point of the native import: import, then test, no hand-editing."""
    result = _import(oracle_table=["ORDERS"])

    run = DataContract(data_contract_str=result.to_yaml()).test()

    print(run.pretty())
    assert run.result == ResultEnum.passed


@pytest.mark.slow
def test_import_oracle_produces_a_valid_contract(oracle_container, credentials):
    result = _import(oracle_table=["ORDERS"])

    assert DataContract(data_contract_str=result.to_yaml()).lint().result == ResultEnum.passed


@pytest.mark.slow
def test_the_primary_key_is_imported(oracle_container, credentials):
    result = _import(oracle_table=["ORDERS"])
    order_id = result.schema_[0].properties[0]

    assert (order_id.primaryKey, order_id.primaryKeyPosition, order_id.required) == (True, 1, True)


@pytest.mark.slow
def test_a_lower_case_schema_still_matches(oracle_container, credentials):
    """Oracle stores identifiers upper case, so the importer upper-cases --schema."""
    result = _import(schema=SCHEMA.lower(), oracle_table=["ORDERS"])

    assert result.servers[0].schema_ == SCHEMA


@pytest.mark.slow
def test_import_oracle_fails_on_an_unknown_table(oracle_container, credentials):
    with pytest.raises(DataContractException) as exc_info:
        _import(oracle_table=["does_not_exist"])

    assert "No tables found" in exc_info.value.reason


def test_import_oracle_requires_a_service_name():
    with pytest.raises(DataContractException) as exc_info:
        DataContract.import_from_source("oracle", "localhost", schema="ADMIN")

    assert "service name is required" in exc_info.value.reason


def test_import_oracle_requires_a_schema():
    with pytest.raises(DataContractException) as exc_info:
        DataContract.import_from_source("oracle", "localhost", service_name="XEPDB1")

    assert "schema is required" in exc_info.value.reason


def test_import_oracle_requires_a_host():
    with pytest.raises(DataContractException) as exc_info:
        DataContract.import_from_source("oracle", None, service_name="XEPDB1", schema="ADMIN")

    assert "host is required" in exc_info.value.reason
