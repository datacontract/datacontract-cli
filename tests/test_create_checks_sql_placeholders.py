import pytest
from open_data_contract_standard.model import DataQuality, Server

from datacontract.engines.checks.create_checks import prepare_query


def test_schema_placeholder():
    quality = DataQuality(type="sql", query="SELECT * FROM {schema}.{model}")
    server = Server(**{"type": "postgres", "schema": "my_schema"})

    assert prepare_query(quality, "my_table", None, server) == "SELECT * FROM my_schema.my_table"


def test_schema_placeholder_falls_back_to_model_name():
    quality = DataQuality(type="sql", query="SELECT * FROM {schema}")
    server = Server(type="postgres")

    assert prepare_query(quality, "my_table", None, server) == "SELECT * FROM my_table"


def test_dataset_and_project_placeholders():
    quality = DataQuality(type="sql", query="SELECT COUNT(*) FROM ${project}.${dataset}.${table}")
    server = Server(type="bigquery", project="my_project", dataset="my_dataset")

    assert prepare_query(quality, "my_table", None, server) == "SELECT COUNT(*) FROM my_project.my_dataset.my_table"


def test_catalog_and_database_placeholders():
    quality = DataQuality(type="sql", query="SELECT * FROM {catalog}.{database}.{model}")
    server = Server(**{"type": "databricks", "catalog": "my_catalog", "database": "my_database"})

    assert prepare_query(quality, "my_table", None, server) == "SELECT * FROM my_catalog.my_database.my_table"


def test_dataset_placeholder_falls_back_to_model_name():
    quality = DataQuality(type="sql", query="SELECT * FROM {dataset}")
    server = Server(**{"type": "postgres", "schema": "my_schema"})

    assert prepare_query(quality, "my_table", None, server) == "SELECT * FROM my_table"


def test_placeholders_without_server():
    quality = DataQuality(type="sql", query="SELECT {column} FROM {dataset}.{table}")

    assert prepare_query(quality, "my_table", "my_field", None) == "SELECT my_field FROM my_table.my_table"


@pytest.mark.parametrize(
    "server_type, expected",
    [
        ("local", 'SELECT COUNT(*) FROM orders WHERE "A B" IS NULL'),
        ("bigquery", "SELECT COUNT(*) FROM orders WHERE `A B` IS NULL"),
        ("sqlserver", "SELECT COUNT(*) FROM orders WHERE [A B] IS NULL"),
    ],
)
def test_field_with_a_space_is_quoted_for_the_server_dialect(server_type, expected):
    quality = DataQuality(type="sql", query="SELECT COUNT(*) FROM {model} WHERE {field} IS NULL")

    assert prepare_query(quality, "orders", "A B", Server(type=server_type)) == expected


def test_nested_field_path_quotes_only_the_segment_that_needs_it():
    quality = DataQuality(type="sql", query="SELECT COUNT(*) FROM {model} WHERE {property} IS NULL")

    assert (
        prepare_query(quality, "orders", "customer.first name", Server(type="postgres"))
        == 'SELECT COUNT(*) FROM orders WHERE customer."first name" IS NULL'
    )


def test_plain_field_name_stays_unquoted():
    quality = DataQuality(type="sql", query="SELECT COUNT(*) FROM {model} WHERE {column} IS NULL")

    assert (
        prepare_query(quality, "orders", "Order_Date", Server(type="postgres"))
        == "SELECT COUNT(*) FROM orders WHERE Order_Date IS NULL"
    )


@pytest.mark.parametrize(
    "server_type, query, expected",
    [
        (
            "local",
            'SELECT COUNT(*) FROM {model} WHERE "{field}" IS NULL',
            'SELECT COUNT(*) FROM orders WHERE "A B" IS NULL',
        ),
        (
            "bigquery",
            "SELECT COUNT(*) FROM {model} WHERE `{field}` IS NULL",
            "SELECT COUNT(*) FROM orders WHERE `A B` IS NULL",
        ),
        (
            "sqlserver",
            "SELECT COUNT(*) FROM {model} WHERE [{field}] IS NULL",
            "SELECT COUNT(*) FROM orders WHERE [A B] IS NULL",
        ),
    ],
)
def test_already_quoted_field_placeholder_is_not_quoted_twice(server_type, query, expected):
    quality = DataQuality(type="sql", query=query)

    assert prepare_query(quality, "orders", "A B", Server(type=server_type)) == expected
