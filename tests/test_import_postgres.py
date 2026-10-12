"""Tests for the Postgres importer, run against a real Postgres container."""

import logging
from pathlib import Path
from unittest.mock import patch

import pytest
import yaml
from open_data_contract_standard.model import OpenDataContractStandard
from testcontainers.postgres import PostgresContainer
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract
from datacontract.imports import postgres_importer
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
      - name: customer_id
        logicalType: integer
        physicalType: integer
        required: true
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
        logicalType: object
        physicalType: jsonb
    """

    print("Result", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)


def test_import_postgres_imports_foreign_key_relationships():
    result = _import(schema="public", postgres_table=["customers", "orders"])

    orders = next(schema for schema in result.schema_ if schema.name == "orders")
    customer_id = next(property for property in orders.properties if property.name == "customer_id")
    relationship = customer_id.relationships[0]

    assert relationship.type == "foreignKey"
    assert relationship.to == "customers.customer_id"
    orders_yaml = next(schema for schema in yaml.safe_load(result.to_yaml())["schema"] if schema["name"] == "orders")
    customer_id_yaml = next(property for property in orders_yaml["properties"] if property["name"] == "customer_id")
    assert "from" not in customer_id_yaml["relationships"][0]


def test_import_postgres_omits_target_partition_foreign_key_clones():
    result = _import(
        schema="partitioned_foreign_keys",
        postgres_table=[
            "partitioned_source",
            "partitioned_target",
            "partitioned_target_low",
            "partitioned_target_high",
        ],
    )

    source = next(schema for schema in result.schema_ if schema.name == "partitioned_source")
    assert [relationship.to for property in source.properties for relationship in property.relationships or []] == [
        "partitioned_target.target_id"
    ]


def test_import_postgres_keeps_partitioned_source_foreign_key_clones():
    result = _import(
        schema="partitioned_foreign_keys",
        postgres_table=[
            "partitioned_source_parent",
            "partitioned_source_low",
            "partitioned_source_high",
            "partitioned_target",
            "partitioned_target_low",
            "partitioned_target_high",
        ],
    )

    relationships = {
        schema.name: [
            relationship.to for property in schema.properties for relationship in property.relationships or []
        ]
        for schema in result.schema_
        if schema.name.startswith("partitioned_source")
    }

    assert relationships == {
        "partitioned_source_parent": ["partitioned_target.target_id"],
        "partitioned_source_low": ["partitioned_target.target_id"],
        "partitioned_source_high": ["partitioned_target.target_id"],
    }


def test_import_postgres_falls_back_to_information_schema_keys_when_catalog_is_unavailable(monkeypatch):
    monkeypatch.setattr(postgres_importer, "_CATALOG_PRIMARY_KEYS_QUERY", "SELECT 1 / 0")

    result = _import(schema="select_only_keys", postgres_table=["simple_target"])

    primary_key = [property for property in result.schema_[0].properties if property.primaryKey]
    assert [(property.name, property.primaryKeyPosition) for property in primary_key] == [("target_id", 1)]


def test_import_postgres_recovers_keys_for_a_select_only_role(monkeypatch):
    reader = "select_only_key_reader"
    password = "select-only-key-reader-password"
    schema = "select_only_keys"
    monkeypatch.setenv("DATACONTRACT_POSTGRES_USERNAME", reader)
    monkeypatch.setenv("DATACONTRACT_POSTGRES_PASSWORD", password)

    result = _import(schema=schema)

    simple_source = next(schema_object for schema_object in result.schema_ if schema_object.name == "simple_source")
    simple_target = next(schema_object for schema_object in result.schema_ if schema_object.name == "simple_target")
    composite_source = next(
        schema_object for schema_object in result.schema_ if schema_object.name == "composite_source"
    )
    composite_target = next(
        schema_object for schema_object in result.schema_ if schema_object.name == "composite_target"
    )

    assert [property.name for property in simple_source.properties if property.primaryKey] == ["source_id"]
    assert [property.name for property in simple_target.properties if property.primaryKey] == ["target_id"]
    assert [property.name for property in composite_source.properties if property.primaryKey] == [
        "source_second_id",
        "source_first_id",
    ]
    assert [property.primaryKeyPosition for property in composite_source.properties if property.primaryKey] == [1, 2]
    assert [property.name for property in composite_target.properties if property.primaryKey] == [
        "first_id",
        "second_id",
    ]
    assert [property.primaryKeyPosition for property in composite_target.properties if property.primaryKey] == [1, 2]
    simple_fk = next(property for property in simple_source.properties if property.name == "target_id").relationships[0]
    assert simple_fk.to == "simple_target.target_id"
    assert simple_fk.from_ is None
    assert all(property.relationships is None for property in composite_source.properties)
    assert composite_source.relationships[0].from_ == [
        "composite_source.source_first_id",
        "composite_source.source_second_id",
    ]
    assert composite_source.relationships[0].to == [
        "composite_target.first_id",
        "composite_target.second_id",
    ]
    assert DataContract(data_contract_str=result.to_yaml()).lint().result == ResultEnum.passed


def test_import_postgres_warns_about_relationships_outside_selected_tables_and_other_schemas(caplog):
    caplog.set_level(logging.WARNING, logger="datacontract.imports.postgres_importer")
    source_only = _import(schema="key_visibility", postgres_table=["selected_source", "composite_source"])
    selected_source = next(schema for schema in source_only.schema_ if schema.name == "selected_source")
    composite_source = next(schema for schema in source_only.schema_ if schema.name == "composite_source")

    assert (
        next(property for property in selected_source.properties if property.name == "target_id").relationships is None
    )
    assert composite_source.relationships is None

    both_endpoints = _import(
        schema="key_visibility",
        postgres_table=["selected_source", "selected_target", "composite_source", "composite_target"],
    )
    selected_source = next(schema for schema in both_endpoints.schema_ if schema.name == "selected_source")
    composite_source = next(schema for schema in both_endpoints.schema_ if schema.name == "composite_source")

    assert next(property for property in selected_source.properties if property.name == "target_id").relationships[
        0
    ].to == ("selected_target.target_id")
    assert composite_source.relationships[0].from_ == [
        "composite_source.source_first_id",
        "composite_source.source_second_id",
    ]
    assert composite_source.relationships[0].to == [
        "composite_target.first_id",
        "composite_target.second_id",
    ]

    cross_schema = _import(schema="key_visibility", postgres_table=["cross_schema_source"])
    cross_schema_source = cross_schema.schema_[0]
    assert (
        next(property for property in cross_schema_source.properties if property.name == "target_id").relationships
        is None
    )

    warnings = [record.getMessage() for record in caplog.records]
    assert len(warnings) == 3
    assert sum("key_visibility.selected_source" in warning for warning in warnings) == 1
    assert sum("key_visibility.composite_source" in warning for warning in warnings) == 1
    assert sum("key_visibility.cross_schema_source" in warning for warning in warnings) == 1
    assert any("key_visibility_other.cross_schema_target" in warning for warning in warnings)

    caplog.clear()
    _import(schema="key_visibility", postgres_table=["selected_target"])

    assert caplog.records == []


def test_import_postgres_isolates_same_named_objects_in_other_schemas():
    result = _import(schema="key_visibility", postgres_table=["same_named"])

    same_named = result.schema_[0]
    assert [property.name for property in same_named.properties if property.primaryKey] == [
        "local_second_id",
        "local_first_id",
    ]
    assert [property.primaryKeyPosition for property in same_named.properties if property.primaryKey] == [1, 2]
    assert "other_id" not in [property.name for property in same_named.properties]


def test_import_postgres_omits_catalog_constraints_with_partially_visible_columns(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_POSTGRES_USERNAME", "partial_key_reader")
    monkeypatch.setenv("DATACONTRACT_POSTGRES_PASSWORD", "partial-key-reader-password")

    result = _import(schema="key_visibility", postgres_table=["partial_source", "partial_target"])
    partial_source = next(schema for schema in result.schema_ if schema.name == "partial_source")
    partial_target = next(schema for schema in result.schema_ if schema.name == "partial_target")

    assert [property.name for property in partial_source.properties] == ["source_first_id"]
    assert [property.name for property in partial_target.properties] == ["first_id"]
    assert all(property.primaryKey is None for property in partial_source.properties + partial_target.properties)
    assert partial_source.relationships is None


def test_import_postgres_catalog_primary_keys_override_partial_column_references(monkeypatch):
    reader = "column_reference_key_reader"
    password = "column-reference-key-reader-password"
    monkeypatch.setenv("DATACONTRACT_POSTGRES_USERNAME", reader)
    monkeypatch.setenv("DATACONTRACT_POSTGRES_PASSWORD", password)
    result = _import(schema="key_visibility", postgres_table=["column_reference_primary_key"])

    primary_key = [property for property in result.schema_[0].properties if property.primaryKey]
    assert {property.name: property.primaryKeyPosition for property in primary_key} == {
        "second_id": 1,
        "first_id": 2,
    }


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

    assert [schema.name for schema in result.schema_] == ["customers", "open_orders", "orders"]
    assert result.schema_[1].physicalType == "view"


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
