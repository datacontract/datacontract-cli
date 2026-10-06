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
from datacontract.imports.postgres_importer import import_postgres_from_connector
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


class _InsufficientPrivilegeError(Exception):
    sqlstate = "42501"


class _FetchFailure:
    def __init__(self, exception):
        self.exception = exception


class _CatalogConnection:
    def __init__(self, results):
        self.results = results
        self.rollbacks = 0
        self.closed = False

    def cursor(self):
        return _CatalogCursor(self)

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


class _CatalogCursor:
    def __init__(self, connection):
        self.connection = connection
        self.description = None
        self.rows = None

    def __enter__(self):
        return self

    def __exit__(self, *args):
        return False

    def execute(self, query, params):
        result = self.connection.results[query]
        if isinstance(result, Exception):
            raise result
        self.rows = result
        if isinstance(result, _FetchFailure):
            self.description = [("table_name",)]
            return
        self.description = [(column,) for column in result[0]] if result else [("table_name",)]

    def fetchall(self):
        if isinstance(self.rows, _FetchFailure):
            raise self.rows.exception
        return [tuple(row[column] for column, *_ in self.description) for row in self.rows]


def _catalog_results(catalog_primary_keys, foreign_keys):
    from datacontract.imports import postgres_importer

    return {
        postgres_importer._TABLES_QUERY: [
            {"table_name": "orders", "table_type": "BASE TABLE", "remarks": None},
            {"table_name": "customers", "table_type": "BASE TABLE", "remarks": None},
        ],
        postgres_importer._COLUMNS_QUERY: [
            {
                "table_name": "orders",
                "column_name": "id",
                "data_type": "integer",
                "character_maximum_length": None,
                "numeric_precision": 32,
                "numeric_scale": 0,
                "is_nullable": "NO",
                "remarks": None,
            },
            {
                "table_name": "orders",
                "column_name": "customer_id",
                "data_type": "integer",
                "character_maximum_length": None,
                "numeric_precision": 32,
                "numeric_scale": 0,
                "is_nullable": "YES",
                "remarks": None,
            },
            {
                "table_name": "customers",
                "column_name": "id",
                "data_type": "integer",
                "character_maximum_length": None,
                "numeric_precision": 32,
                "numeric_scale": 0,
                "is_nullable": "NO",
                "remarks": None,
            },
        ],
        postgres_importer._INFORMATION_SCHEMA_PRIMARY_KEYS_QUERY: [
            {"table_name": "orders", "column_name": "id", "ordinal_position": 1}
        ],
        postgres_importer._CATALOG_PRIMARY_KEYS_QUERY: catalog_primary_keys,
        postgres_importer._FOREIGN_KEYS_QUERY: foreign_keys,
    }


def _import_with_catalog_results(monkeypatch, catalog_primary_keys, foreign_keys):
    connection = _CatalogConnection(_catalog_results(catalog_primary_keys, foreign_keys))
    monkeypatch.setattr("datacontract.imports.postgres_importer.postgres_connection", lambda **kwargs: connection)
    return import_postgres_from_connector(host="localhost", database="postgres"), connection


def test_import_postgres_catalog_primary_keys_override_information_schema_when_empty(monkeypatch):
    result, connection = _import_with_catalog_results(monkeypatch, [], [])

    orders = next(schema for schema in result.schema_ if schema.name == "orders")
    assert orders.properties[0].primaryKey is None
    assert connection.rollbacks == 0


def test_import_postgres_falls_back_to_information_schema_primary_keys_after_catalog_failure(monkeypatch):
    foreign_key = {
        "table_name": "orders",
        "column_name": "customer_id",
        "foreign_table_name": "customers",
        "foreign_table_schema": "public",
        "foreign_column_name": "id",
        "constraint_oid": 1,
        "expected_column_count": 1,
        "ordinal_position": 1,
    }
    result, connection = _import_with_catalog_results(
        monkeypatch, _InsufficientPrivilegeError("catalog PK unavailable"), [foreign_key]
    )

    orders = next(schema for schema in result.schema_ if schema.name == "orders")
    assert orders.properties[0].primaryKey is True
    assert orders.properties[1].relationships[0].to == "customers.id"
    assert connection.rollbacks == 1


def test_import_postgres_omits_foreign_keys_after_catalog_failure(monkeypatch):
    catalog_primary_key = {
        "table_name": "orders",
        "column_name": "id",
        "constraint_oid": 1,
        "expected_column_count": 1,
        "ordinal_position": 1,
    }
    result, connection = _import_with_catalog_results(
        monkeypatch, [catalog_primary_key], _InsufficientPrivilegeError("catalog FK unavailable")
    )

    orders = next(schema for schema in result.schema_ if schema.name == "orders")
    assert orders.properties[0].primaryKey is True
    assert orders.properties[1].relationships is None
    assert connection.rollbacks == 1


def test_import_postgres_keeps_composite_catalog_keys_atomic_and_ordered(monkeypatch):
    from datacontract.imports import postgres_importer

    results = _catalog_results(
        [
            {
                "table_name": "orders",
                "column_name": "customer_id",
                "constraint_oid": 1,
                "expected_column_count": 2,
                "ordinal_position": 2,
            },
            {
                "table_name": "orders",
                "column_name": "id",
                "constraint_oid": 1,
                "expected_column_count": 2,
                "ordinal_position": 1,
            },
        ],
        [
            {
                "table_name": "orders",
                "column_name": "customer_id",
                "foreign_table_name": "customers",
                "foreign_table_schema": "public",
                "foreign_column_name": "id",
                "constraint_oid": 2,
                "expected_column_count": 2,
                "ordinal_position": 2,
            },
            {
                "table_name": "orders",
                "column_name": "id",
                "foreign_table_name": "customers",
                "foreign_table_schema": "public",
                "foreign_column_name": "id",
                "constraint_oid": 2,
                "expected_column_count": 2,
                "ordinal_position": 1,
            },
        ],
    )
    results[postgres_importer._COLUMNS_QUERY].append(
        {
            "table_name": "customers",
            "column_name": "customer_id",
            "data_type": "integer",
            "character_maximum_length": None,
            "numeric_precision": 32,
            "numeric_scale": 0,
            "is_nullable": "NO",
            "remarks": None,
        }
    )
    results[postgres_importer._FOREIGN_KEYS_QUERY][0]["foreign_column_name"] = "customer_id"
    results[postgres_importer._FOREIGN_KEYS_QUERY][1]["foreign_column_name"] = "id"
    connection = _CatalogConnection(results)
    monkeypatch.setattr("datacontract.imports.postgres_importer.postgres_connection", lambda **kwargs: connection)

    result = import_postgres_from_connector(host="localhost", database="postgres")

    orders = next(schema for schema in result.schema_ if schema.name == "orders")
    assert [property.primaryKeyPosition for property in orders.properties if property.primaryKey] == [1, 2]
    assert orders.properties[0].relationships is None
    assert orders.properties[1].relationships is None
    assert len(orders.relationships) == 1
    assert orders.relationships[0].from_ == ["orders.id", "orders.customer_id"]
    assert orders.relationships[0].to == ["customers.id", "customers.customer_id"]
    assert DataContract(data_contract_str=result.to_yaml()).lint().result == ResultEnum.passed


def test_import_postgres_omits_incomplete_catalog_constraints(monkeypatch):
    incomplete_primary_key = {
        "table_name": "orders",
        "column_name": "id",
        "constraint_oid": 1,
        "expected_column_count": 2,
        "ordinal_position": 1,
    }
    incomplete_foreign_key = {
        "table_name": "orders",
        "column_name": "customer_id",
        "foreign_table_name": "customers",
        "foreign_table_schema": "public",
        "foreign_column_name": "id",
        "constraint_oid": 2,
        "expected_column_count": 2,
        "ordinal_position": 1,
    }

    result, _ = _import_with_catalog_results(monkeypatch, [incomplete_primary_key], [incomplete_foreign_key])

    orders = next(schema for schema in result.schema_ if schema.name == "orders")
    assert all(property.primaryKey is None for property in orders.properties)
    assert orders.properties[1].relationships is None
    assert orders.relationships is None


def test_import_postgres_keeps_distinct_foreign_keys_on_the_same_source_property(monkeypatch):
    foreign_keys = [
        {
            "table_name": "orders",
            "column_name": "customer_id",
            "foreign_table_name": "customers",
            "foreign_table_schema": "public",
            "foreign_column_name": "id",
            "constraint_oid": constraint_oid,
            "expected_column_count": 1,
            "ordinal_position": 1,
        }
        for constraint_oid in (1, 2)
    ]

    result, _ = _import_with_catalog_results(monkeypatch, [], foreign_keys)

    orders = next(schema for schema in result.schema_ if schema.name == "orders")
    customer_id = next(property for property in orders.properties if property.name == "customer_id")
    assert [relationship.to for relationship in customer_id.relationships] == ["customers.id", "customers.id"]


def test_import_postgres_raises_when_a_required_catalog_query_fails(monkeypatch):
    from datacontract.imports import postgres_importer

    connection = _CatalogConnection(_catalog_results([], []))
    connection.results[postgres_importer._TABLES_QUERY] = RuntimeError("tables unavailable")
    monkeypatch.setattr("datacontract.imports.postgres_importer.postgres_connection", lambda **kwargs: connection)

    with pytest.raises(DataContractException, match="Could not read the Postgres catalog"):
        import_postgres_from_connector(host="localhost", database="postgres")

    assert connection.rollbacks == 0


def test_import_postgres_raises_for_an_optional_catalog_failure_that_is_not_an_access_error(monkeypatch):
    connection = _CatalogConnection(_catalog_results(RuntimeError("catalog syntax error"), []))
    monkeypatch.setattr("datacontract.imports.postgres_importer.postgres_connection", lambda **kwargs: connection)

    with pytest.raises(DataContractException, match="Could not read the Postgres catalog") as exc_info:
        import_postgres_from_connector(host="localhost", database="postgres")

    assert isinstance(exc_info.value.original_exception, RuntimeError)
    assert connection.rollbacks == 0


def test_import_postgres_raises_when_a_required_catalog_row_cannot_be_processed(monkeypatch):
    failure = RuntimeError("table rows unavailable")
    connection = _CatalogConnection(_catalog_results([], []))
    from datacontract.imports import postgres_importer

    connection.results[postgres_importer._TABLES_QUERY] = _FetchFailure(failure)
    monkeypatch.setattr("datacontract.imports.postgres_importer.postgres_connection", lambda **kwargs: connection)

    with pytest.raises(DataContractException, match="Could not read the Postgres catalog") as exc_info:
        import_postgres_from_connector(host="localhost", database="postgres")

    assert exc_info.value.original_exception is failure
    assert connection.rollbacks == 0


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


def test_import_postgres_recovers_keys_for_a_select_only_role(monkeypatch):
    import psycopg

    reader = "select_only_key_reader"
    password = "select-only-key-reader-password"
    schema = "select_only_keys"
    host = postgres.get_container_host_ip()
    port = postgres.get_exposed_port(5432)

    with psycopg.connect(
        dbname=postgres.dbname, user=reader, password=password, host=host, port=port, autocommit=True
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                WITH application_tables AS (
                    SELECT relation.oid
                    FROM pg_catalog.pg_class AS relation
                    JOIN pg_catalog.pg_namespace AS namespace ON namespace.oid = relation.relnamespace
                    WHERE namespace.nspname = %s
                      AND relation.relkind = 'r'
                )
                SELECT bool_and(has_schema_privilege(current_user, %s, 'USAGE')),
                       bool_and(has_table_privilege(current_user, oid, 'SELECT')),
                       NOT bool_or(has_table_privilege(current_user, oid, 'INSERT')),
                       NOT bool_or(has_table_privilege(current_user, oid, 'UPDATE')),
                       NOT bool_or(has_table_privilege(current_user, oid, 'DELETE')),
                       NOT bool_or(has_table_privilege(current_user, oid, 'REFERENCES')),
                       bool_and(has_table_privilege(current_user, 'pg_catalog.pg_constraint', 'SELECT')),
                       bool_and(has_table_privilege(current_user, 'pg_catalog.pg_class', 'SELECT')),
                       bool_and(has_table_privilege(current_user, 'pg_catalog.pg_namespace', 'SELECT')),
                       bool_and(has_table_privilege(current_user, 'pg_catalog.pg_attribute', 'SELECT'))
                FROM application_tables
                """,
                (schema, schema),
            )
            privileges = cursor.fetchone()

    assert privileges == (True, True, True, True, True, True, True, True, True, True)
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


def test_import_postgres_omits_relationships_outside_selected_tables_and_other_schemas():
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
    import psycopg

    reader = "column_reference_key_reader"
    password = "column-reference-key-reader-password"
    host = postgres.get_container_host_ip()
    port = postgres.get_exposed_port(5432)

    with psycopg.connect(
        dbname=postgres.dbname, user=reader, password=password, host=host, port=port, autocommit=True
    ) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                SELECT has_column_privilege(
                           current_user,
                           'key_visibility.column_reference_primary_key',
                           'first_id',
                           'REFERENCES'
                       ),
                       has_column_privilege(
                           current_user,
                           'key_visibility.column_reference_primary_key',
                           'second_id',
                           'REFERENCES'
                       )
                """
            )
            assert cursor.fetchone() == (True, False)

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
