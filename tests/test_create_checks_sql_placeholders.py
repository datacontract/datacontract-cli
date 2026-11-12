from open_data_contract_standard.model import DataQuality, Server

from datacontract.data_contract import DataContract
from datacontract.engines.checks.check_spec import FieldPath
from datacontract.engines.checks.create_checks import prepare_query


def test_schema_placeholder():
    quality = DataQuality(type="sql", query="SELECT * FROM {schema}.{model}")
    server = Server(**{"type": "postgres", "schema": "my_schema"})

    assert prepare_query(quality.query, "my_table", None, server) == "SELECT * FROM my_schema.my_table"


def test_schema_placeholder_falls_back_to_model_name():
    quality = DataQuality(type="sql", query="SELECT * FROM {schema}")
    server = Server(type="postgres")

    assert prepare_query(quality.query, "my_table", None, server) == "SELECT * FROM my_table"


def test_dataset_and_project_placeholders():
    quality = DataQuality(type="sql", query="SELECT COUNT(*) FROM ${project}.${dataset}.${table}")
    server = Server(type="bigquery", project="my_project", dataset="my_dataset")

    assert (
        prepare_query(quality.query, "my_table", None, server) == "SELECT COUNT(*) FROM my_project.my_dataset.my_table"
    )


def test_catalog_and_database_placeholders():
    quality = DataQuality(type="sql", query="SELECT * FROM {catalog}.{database}.{model}")
    server = Server(**{"type": "databricks", "catalog": "my_catalog", "database": "my_database"})

    assert prepare_query(quality.query, "my_table", None, server) == "SELECT * FROM my_catalog.my_database.my_table"


def test_dataset_placeholder_falls_back_to_model_name():
    quality = DataQuality(type="sql", query="SELECT * FROM {dataset}")
    server = Server(**{"type": "postgres", "schema": "my_schema"})

    assert prepare_query(quality.query, "my_table", None, server) == "SELECT * FROM my_table"


def test_placeholders_without_server():
    quality = DataQuality(type="sql", query="SELECT {column} FROM {dataset}.{table}")

    assert prepare_query(quality.query, "my_table", "my_field", None) == "SELECT my_field FROM my_table.my_table"


def test_a_name_that_cannot_be_read_bare_is_quoted_in_the_server_dialect():
    quality = DataQuality(type="sql", query="SELECT COUNT(*) FROM {object} WHERE {property} IS NULL")

    assert (
        prepare_query(quality.query, "my orders", "A B", Server(type="local"))
        == 'SELECT COUNT(*) FROM "my orders" WHERE "A B" IS NULL'
    )
    assert (
        prepare_query(quality.query, "my orders", "A B", Server(type="databricks"))
        == "SELECT COUNT(*) FROM `my orders` WHERE `A B` IS NULL"
    )
    assert (
        prepare_query(quality.query, "my orders", "A B", Server(type="sqlserver"))
        == "SELECT COUNT(*) FROM [my orders] WHERE [A B] IS NULL"
    )


def test_a_plain_name_stays_bare_so_the_backend_resolves_its_case():
    quality = DataQuality(type="sql", query="SELECT COUNT(*) FROM {object} WHERE {property} IS NULL")
    server = Server(type="snowflake")

    assert (
        prepare_query(quality.query, "Orders", "order_id", server)
        == "SELECT COUNT(*) FROM Orders WHERE order_id IS NULL"
    )


def test_each_step_of_a_nested_property_path_is_quoted_on_its_own():
    quality = DataQuality(type="sql", query="SELECT COUNT(*) FROM {model} WHERE {field} IS NULL")
    server = Server(type="databricks")

    assert (
        prepare_query(quality.query, "analytics.my orders", FieldPath(("customer", "home address")), server)
        == "SELECT COUNT(*) FROM analytics.`my orders` WHERE customer.`home address` IS NULL"
    )


def test_a_nested_property_is_a_path_into_its_column_on_snowflake():
    quality = DataQuality(type="sql", query="SELECT COUNT(*) FROM {model} WHERE {property} IS NULL")
    server = Server(type="snowflake")

    assert (
        prepare_query(quality.query, "analytics.orders", FieldPath(("customer", "home address")), server)
        == 'SELECT COUNT(*) FROM analytics.orders WHERE customer:"home address" IS NULL'
    )


def test_a_property_name_with_a_dot_is_one_quoted_name_on_every_dialect():
    quality = DataQuality(type="sql", query="SELECT COUNT(*) FROM orders WHERE {property} < 0")

    for server_type, quoted in (("duckdb", '"Rate.x"'), ("databricks", "`Rate.x`"), ("snowflake", '"Rate.x"')):
        assert (
            prepare_query(quality.query, "orders", "Rate.x", Server(type=server_type))
            == f"SELECT COUNT(*) FROM orders WHERE {quoted} < 0"
        ), server_type


def test_quotes_around_a_placeholder_are_replaced_by_the_dialect_quoting():
    server = Server(type="databricks")
    expected = "SELECT COUNT(*) FROM orders WHERE `A B` IS NULL"

    for written in ('"{property}"', "'{property}'", "`{property}`"):
        quality = DataQuality(type="sql", query=f"SELECT COUNT(*) FROM orders WHERE {written} IS NULL")
        assert prepare_query(quality.query, "orders", "A B", server) == expected, written


def test_backticks_around_a_placeholder_force_quoting():
    quality = DataQuality(
        type="sql", query="SELECT COUNT(*) FROM `{catalog}.{schema}.{table}` WHERE `{property}` IS NULL"
    )
    server = Server(type="databricks", catalog="main", schema="sales")

    assert (
        prepare_query(quality.query, "orders", "join", server)
        == "SELECT COUNT(*) FROM `main`.sales.`orders` WHERE `join` IS NULL"
    )


def test_a_name_the_dialect_reads_bare_stays_bare():
    quality = DataQuality(type="sql", query="SELECT COUNT(*) FROM orders WHERE {property} IS NULL")

    assert (
        prepare_query(quality.query, "orders", "amount$usd", Server(type="snowflake"))
        == "SELECT COUNT(*) FROM orders WHERE amount$usd IS NULL"
    )
    assert (
        prepare_query(quality.query, "orders", "amount$usd", Server(type="databricks"))
        == "SELECT COUNT(*) FROM orders WHERE `amount$usd` IS NULL"
    )


def test_a_mysql_rule_quotes_for_duckdb_which_runs_it():
    quality = DataQuality(type="sql", query="SELECT COUNT(*) FROM orders WHERE {property} IS NULL")

    assert (
        prepare_query(quality.query, "orders", "A B", Server(type="mysql"))
        == 'SELECT COUNT(*) FROM orders WHERE "A B" IS NULL'
    )


def test_a_rule_on_a_column_with_a_space_runs(tmp_path):
    data = tmp_path / "orders.csv"
    data.write_text("id,A B\n1,x\n2,\n")
    contract = f"""apiVersion: v3.1.0
kind: DataContract
id: orders
name: orders
version: 1.0.0
status: active
servers:
  - server: local
    type: local
    path: {data}
    format: csv
schema:
  - name: orders
    properties:
      - name: A B
        logicalType: string
        quality:
          - type: sql
            query: SELECT COUNT(*) FROM {{object}} WHERE {{property}} IS NULL
            mustBe: 0
"""

    run = DataContract(data_contract_str=contract, inline_references=False).test()

    check = next(c for c in run.checks if c.type == "field_quality_sql")
    assert check.reason == "Actual custom_sql(A B) was 1, expected = 0"


def test_a_substituted_name_is_not_searched_for_placeholders():
    quality = DataQuality(type="sql", query="SELECT COUNT(*) FROM {model}")
    server = Server(type="postgres", schema="sales")

    assert prepare_query(quality.query, "t{schema}", None, server) == 'SELECT COUNT(*) FROM "t{schema}"'
