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
