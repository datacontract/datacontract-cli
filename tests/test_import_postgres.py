"""Tests for the Postgres importer, run against a real Postgres container."""

from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from open_data_contract_standard.model import OpenDataContractStandard
from testcontainers.postgres import PostgresContainer
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import ResultEnum

postgres = PostgresContainer("postgres:16")

# This module-scoped fixture is instantiated before conftest's function-scoped
# chdir into the test directory, so the seed file is addressed from this file.
SEED_SQL = Path(__file__).parent / "fixtures" / "postgres" / "data" / "import.sql"


@pytest.fixture(scope="module", autouse=True)
def postgres_container(request):
    postgres.start()
    request.addfinalizer(postgres.stop)
    _init_sql(SEED_SQL)


@pytest.fixture(autouse=True)
def credentials(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_POSTGRES_USERNAME", postgres.username)
    monkeypatch.setenv("DATACONTRACT_POSTGRES_PASSWORD", postgres.password)


def _import(**kwargs):
    kwargs.setdefault("database", postgres.dbname)
    kwargs.setdefault("port", postgres.get_exposed_port(5432))
    return DataContract.import_from_source("postgres", postgres.get_container_host_ip(), **kwargs)


def test_import_postgres():
    result = _import(schema="public", postgres_table=["orders"])

    expected = f"""
apiVersion: v3.2.0
kind: DataContract
id: my-data-contract
name: My Data Contract
version: 1.0.0
status: draft
servers:
  - server: postgres
    type: postgres
    host: {postgres.get_container_host_ip()}
    port: {postgres.get_exposed_port(5432)}
    database: {postgres.dbname}
    schema: public
schema:
  - name: orders
    physicalName: orders
    logicalType: object
    physicalType: table
    description: All orders
    properties:
      - name: order_id
        logicalType: string
        logicalTypeOptions:
          maxLength: 36
        physicalType: character varying(36)
        description: The order id
        required: true
        primaryKey: true
        primaryKeyPosition: 1
      - name: order_total
        logicalType: number
        physicalType: numeric(10,2)
        customProperties:
          - property: precision
            value: 10
          - property: scale
            value: 2
      - name: line_count
        logicalType: integer
        physicalType: integer
        required: true
      - name: ordered_at
        logicalType: timestamp
        physicalType: timestamp with time zone
      - name: payload
        physicalType: jsonb
    """

    print("Result", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)


def test_import_postgres_produces_a_valid_contract():
    result = _import(schema="public")

    run = DataContract(data_contract_str=result.to_yaml()).lint()

    assert run.result == ResultEnum.passed


def test_imported_contract_passes_test_without_editing():
    """The whole point of the native import: import, then test, no hand-editing."""
    result = _import(postgres_table=["orders"])

    run = DataContract(data_contract_str=result.to_yaml()).test()

    print(run.pretty())
    assert run.result == ResultEnum.passed


def test_import_postgres_imports_all_tables_by_default():
    result = _import()

    assert [schema.name for schema in result.schema_] == ["open_orders", "orders"]
    assert result.schema_[0].physicalType == "view"


def test_import_postgres_defaults_to_the_public_schema():
    result = _import(schema=None)

    assert result.servers[0].schema_ == "public"


def test_import_postgres_fails_on_an_unknown_table():
    with pytest.raises(DataContractException) as exc_info:
        _import(schema="public", postgres_table=["does_not_exist"])

    assert "No tables found" in exc_info.value.reason


def test_import_postgres_requires_a_database():
    with pytest.raises(DataContractException) as exc_info:
        DataContract.import_from_source("postgres", postgres.get_container_host_ip(), database=None)

    assert "database is required" in exc_info.value.reason


def test_import_postgres_requires_a_host():
    with pytest.raises(DataContractException) as exc_info:
        DataContract.import_from_source("postgres", None, database="postgres")

    assert "host is required" in exc_info.value.reason


def test_import_postgres_requires_credentials(monkeypatch):
    monkeypatch.delenv("DATACONTRACT_POSTGRES_PASSWORD")

    with pytest.raises(DataContractException) as exc_info:
        _import()

    assert "DATACONTRACT_POSTGRES_PASSWORD is not set" in exc_info.value.reason


def test_cli_schema_option_is_not_rewritten_to_json_schema():
    """`--schema` means the database schema here, not the v0.12.0 `--json-schema`."""
    with patch("datacontract.imports.postgres_importer.import_postgres_from_connector") as mock_import:
        mock_import.return_value = OpenDataContractStandard(id="test", kind="DataContract", apiVersion="v3.1.0")
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["import", "postgres", "--source", "localhost", "--database", "postgres", "--schema", "analytics"],
        )

    assert result.exit_code == 0
    assert mock_import.call_args.kwargs["schema"] == "analytics"
    assert "--json-schema" not in result.output


def _init_sql(file_path):
    import psycopg

    with psycopg.connect(
        dbname=postgres.dbname,
        user=postgres.username,
        password=postgres.password,
        host=postgres.get_container_host_ip(),
        port=postgres.get_exposed_port(5432),
    ) as connection:
        with open(file_path) as sql_file:
            connection.execute(sql_file.read())
