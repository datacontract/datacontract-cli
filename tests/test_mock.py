import csv
import io
import json

import pytest
from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, SchemaProperty, Server
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract
from datacontract.lint.resolve import resolve_data_contract
from datacontract.mock.mock_generator import generate_mock_data

FIXTURE = "./fixtures/mock/datacontract.odcs.yaml"


def _load():
    return resolve_data_contract(data_contract_location=FIXTURE)


def test_cli_mock(tmp_path):
    runner = CliRunner()
    result = runner.invoke(
        app,
        ["mock", FIXTURE, "--output", str(tmp_path), "--rows", "5", "--seed", "42"],
    )

    assert result.exit_code == 0
    assert (tmp_path / "orders.sql").exists()
    assert (tmp_path / "customers.json").exists()


def test_mock_table_renders_sql_insert_statements():
    data_contract = _load()

    results = generate_mock_data(data_contract, schema_name="orders", rows=3, seed=42)

    assert len(results) == 1
    result = results[0]
    assert result.schema_name == "orders"
    assert result.physical_type == "table"
    assert result.format == "sql"
    assert result.content.count("INSERT INTO orders (order_id, customer_id, order_total, order_status)") == 1
    assert _value_tuples(result.content) == 3


def test_mock_table_respects_enum_and_pattern_constraints():
    data_contract = _load()

    results = generate_mock_data(data_contract, schema_name="orders", rows=20, seed=1)
    content = results[0].content

    for line in content.splitlines():
        if not line.strip().startswith("("):
            continue
        assert any(status in line for status in ("'pending'", "'shipped'", "'delivered'"))
        # order_id is the primary key with pattern `^B[0-9]+$`
        assert "'B" in line


def test_mock_file_defaults_to_json():
    data_contract = _load()

    results = generate_mock_data(data_contract, schema_name="customers", rows=4, seed=7)

    assert len(results) == 1
    result = results[0]
    assert result.physical_type == "file"
    assert result.format == "json"
    records = json.loads(result.content)
    assert len(records) == 4
    assert set(records[0].keys()) == {"customer_id", "email", "full_name", "signup_date", "is_active"}


def test_mock_file_uses_server_format_csv():
    data_contract = _load()
    data_contract.servers[1].format = "csv"

    results = generate_mock_data(data_contract, schema_name="customers", rows=3, seed=7)

    result = results[0]
    assert result.format == "csv"
    rows = list(csv.DictReader(io.StringIO(result.content)))
    assert len(rows) == 3


def test_mock_file_uses_server_format_parquet():
    pyarrow_parquet = __import__("pyarrow.parquet", fromlist=["parquet"])

    data_contract = _load()
    data_contract.servers[1].format = "parquet"

    results = generate_mock_data(data_contract, schema_name="customers", rows=3, seed=7)

    result = results[0]
    assert result.format == "parquet"
    table = pyarrow_parquet.read_table(io.BytesIO(result.content))
    assert table.num_rows == 3


def test_mock_unknown_schema_name_raises():
    data_contract = _load()

    try:
        generate_mock_data(data_contract, schema_name="does-not-exist")
        assert False, "expected RuntimeError"
    except RuntimeError as e:
        assert "does-not-exist" in str(e)


def test_mock_is_reproducible_with_seed():
    data_contract = _load()

    first = generate_mock_data(data_contract, schema_name="customers", rows=5, seed=123)
    second = generate_mock_data(data_contract, schema_name="customers", rows=5, seed=123)

    assert first[0].content == second[0].content


def test_data_contract_mock_method():
    results = DataContract(data_contract_file=FIXTURE).mock(schema_name="orders", rows=2, seed=42)

    assert len(results) == 1
    assert results[0].schema_name == "orders"


# ---------------------------------------------------------------------------
# Locale support (FR, EN, ES, DE, NL, IT, PT, ZH)
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("locale", ["FR", "EN", "ES", "DE", "NL", "IT", "PT", "ZH", "fr", "  de  "])
def test_mock_accepts_supported_locale_codes(locale):
    data_contract = _load()

    results = generate_mock_data(data_contract, schema_name="customers", rows=2, seed=1, locale=locale)

    records = json.loads(results[0].content)
    assert len(records) == 2


def test_mock_different_locales_generate_different_names():
    data_contract = _load()

    fr_records = json.loads(
        generate_mock_data(data_contract, schema_name="customers", rows=5, seed=1, locale="FR")[0].content
    )
    de_records = json.loads(
        generate_mock_data(data_contract, schema_name="customers", rows=5, seed=1, locale="DE")[0].content
    )

    assert [r["full_name"] for r in fr_records] != [r["full_name"] for r in de_records]


def test_mock_unsupported_locale_raises():
    data_contract = _load()

    try:
        generate_mock_data(data_contract, schema_name="customers", locale="XX")
        assert False, "expected RuntimeError"
    except RuntimeError as e:
        assert "XX" in str(e)
        for code in ("FR", "EN", "ES", "DE", "NL", "IT", "PT", "ZH"):
            assert code in str(e)


# ---------------------------------------------------------------------------
# Referential integrity (ODCS `relationships`)
# ---------------------------------------------------------------------------


def _value_tuple_lines(content: str) -> list[str]:
    """The `(v1, v2, ...)` lines of the VALUES clause, one per generated row."""
    return [line.strip().rstrip(",;") for line in content.splitlines() if line.strip().startswith("(")]


def _value_tuples(content: str) -> int:
    """Number of value tuples (i.e. generated rows) in the rendered INSERT statement."""
    return len(_value_tuple_lines(content))


def _extract_sql_column(content: str, table: str, columns: list[str], column: str) -> list[str]:
    """Pull one column's literal values out of the generated multi-row INSERT statement."""
    index = columns.index(column)
    values = []
    for tuple_line in _value_tuple_lines(content):
        values_part = tuple_line.removeprefix("(").removesuffix(")")
        values.append([v.strip().strip("'") for v in values_part.split(", ")][index])
    return values


def test_mock_generates_parents_before_children_regardless_of_declaration_order():
    data_contract = _load()
    # `line_items` is declared before `orders` in the fixture on purpose.
    assert [s.name for s in data_contract.schema_][0] == "line_items"

    results = generate_mock_data(data_contract, schema_name="all", rows=5, seed=42)

    order = [r.schema_name for r in results]
    assert order.index("customers") < order.index("orders") < order.index("line_items")


def test_mock_cross_schema_foreign_key_references_generated_values():
    data_contract = _load()

    results = generate_mock_data(data_contract, schema_name="all", rows=5, seed=42)
    by_name = {r.schema_name: r for r in results}

    customer_records = json.loads(by_name["customers"].content)
    customer_ids = {c["customer_id"] for c in customer_records}
    order_customer_ids = _extract_sql_column(
        by_name["orders"].content, "orders", ["order_id", "customer_id", "order_total", "order_status"], "customer_id"
    )
    assert order_customer_ids
    assert set(order_customer_ids) <= customer_ids

    order_ids = _extract_sql_column(
        by_name["orders"].content, "orders", ["order_id", "customer_id", "order_total", "order_status"], "order_id"
    )
    line_item_order_ids = _extract_sql_column(
        by_name["line_items"].content, "line_items", ["line_item_id", "order_id", "sku"], "order_id"
    )
    assert line_item_order_ids
    assert set(line_item_order_ids) <= set(order_ids)


def test_mock_self_referencing_foreign_key():
    data_contract = _load()

    results = generate_mock_data(data_contract, schema_name="employees", rows=5, seed=42)
    content = results[0].content
    columns = ["employee_id", "manager_id", "full_name"]

    employee_ids = set(_extract_sql_column(content, "employees", columns, "employee_id"))
    manager_ids = [v for v in _extract_sql_column(content, "employees", columns, "manager_id") if v != "NULL"]

    # `manager_id` is optional, so at least the very first row (nothing to reference yet) is NULL.
    assert "NULL" in content
    assert set(manager_ids) <= employee_ids


def test_mock_relationship_to_excluded_schema_falls_back_with_warning(caplog):
    data_contract = _load()

    with caplog.at_level("WARNING", logger="datacontract.mock.mock_generator"):
        results = generate_mock_data(data_contract, schema_name="line_items", rows=3, seed=1)

    assert len(results) == 1
    assert any("orders.order_id" in message for message in caplog.messages)


# ---------------------------------------------------------------------------
# Identity/auto-increment columns (dialect-specific INSERT directives)
# ---------------------------------------------------------------------------


def _load_identity_contract(server_type: str) -> OpenDataContractStandard:
    """Builds an in-memory ODCS contract directly (skipping YAML JSON-schema
    validation, whose required server fields vary per `type`) with a single
    `products` table with an integer primary key, so `is_identity_column`
    treats it as an auto-increment/IDENTITY column.
    """
    return OpenDataContractStandard(
        kind="DataContract",
        apiVersion="v3.1.0",
        id="mock-identity-unit-test",
        name="Mock Identity Unit Test",
        version="1.0.0",
        status="active",
        servers=[Server(server="production", type=server_type)],
        schema=[
            SchemaObject(
                name="products",
                physicalType="table",
                properties=[
                    SchemaProperty(
                        name="product_id",
                        physicalType="integer",
                        primaryKey=True,
                        primaryKeyPosition=1,
                        logicalType="integer",
                        required=True,
                    ),
                    SchemaProperty(
                        name="product_name",
                        physicalType="string",
                        logicalType="string",
                        required=True,
                    ),
                ],
            )
        ],
    )


def test_mock_sqlserver_wraps_inserts_with_identity_insert_toggle():
    data_contract = _load_identity_contract("sqlserver")

    content = generate_mock_data(data_contract, schema_name="products", rows=3, seed=1)[0].content
    lines = [line for line in content.splitlines() if line.strip()]

    assert "SET IDENTITY_INSERT products ON;" in lines
    assert "SET IDENTITY_INSERT products OFF;" in lines
    on_index = lines.index("SET IDENTITY_INSERT products ON;")
    off_index = lines.index("SET IDENTITY_INSERT products OFF;")
    insert_index = lines.index("INSERT INTO products (product_id, product_name)")
    assert on_index < insert_index < off_index
    assert content.count("INSERT INTO products (product_id, product_name)") == 1
    assert _value_tuples(content) == 3
    assert "OVERRIDING SYSTEM VALUE" not in content


def test_mock_postgres_uses_overriding_system_value_and_resyncs_sequence():
    data_contract = _load_identity_contract("postgres")

    content = generate_mock_data(data_contract, schema_name="products", rows=3, seed=1)[0].content

    assert content.count("INSERT INTO products (product_id, product_name)") == 1
    assert content.count("OVERRIDING SYSTEM VALUE") == 1
    assert _value_tuples(content) == 3
    assert "SET IDENTITY_INSERT" not in content
    assert (
        "SELECT setval(pg_get_serial_sequence('products', 'product_id'), "
        "(SELECT MAX(product_id) FROM products));" in content
    )


def test_mock_oracle_uses_overriding_system_value_without_sequence_resync():
    data_contract = _load_identity_contract("oracle")

    content = generate_mock_data(data_contract, schema_name="products", rows=3, seed=1)[0].content

    assert content.count("INSERT INTO products (product_id, product_name)") == 1
    assert content.count("OVERRIDING SYSTEM VALUE") == 1
    assert _value_tuples(content) == 3
    assert "setval" not in content
    assert "SET IDENTITY_INSERT" not in content


@pytest.mark.parametrize("server_type", ["mysql", "snowflake", "databricks", "trino", "clickhouse"])
def test_mock_other_dialects_render_plain_inserts(server_type):
    data_contract = _load_identity_contract(server_type)

    content = generate_mock_data(data_contract, schema_name="products", rows=3, seed=1)[0].content

    assert content.count("INSERT INTO products (product_id, product_name)") == 1
    assert _value_tuples(content) == 3
    assert "OVERRIDING SYSTEM VALUE" not in content
    assert "SET IDENTITY_INSERT" not in content


def test_mock_non_identity_primary_key_gets_no_special_directive():
    # The shared fixture's `orders.order_id` primary key is a `varchar`, not an
    # integer, so it should never be treated as an identity column even though
    # the fixture declares a `postgres` server.
    data_contract = _load()

    content = generate_mock_data(data_contract, schema_name="orders", rows=3, seed=1)[0].content

    assert "OVERRIDING SYSTEM VALUE" not in content
    assert "SET IDENTITY_INSERT" not in content
