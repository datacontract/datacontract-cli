import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

sql_file_path = "fixtures/clickhouse/data/orders.sql"


def test_cli():
    result = CliRunner().invoke(app, ["import", "sql", "--source", sql_file_path, "--dialect", "clickhouse"])

    assert result.exit_code == 0


def test_import_sql_clickhouse():
    result = DataContract.import_from_source("sql", sql_file_path, dialect="clickhouse")

    contract = yaml.safe_load(result.to_yaml())
    assert contract["servers"] == [
        {"server": "clickhouse", "type": "clickhouse", "host": "my_host", "port": 8123, "database": "my_database"}
    ]
    properties = {p["name"]: p for p in contract["schema"][0]["properties"]}
    assert {name: (p["physicalType"], p.get("logicalType"), p.get("required")) for name, p in properties.items()} == {
        "order_id": ("String", "string", True),
        "customer_id": ("Nullable(String)", "string", None),
        "order_status": ("LowCardinality(String)", "string", True),
        "order_total": ("Decimal(10, 2)", "number", True),
        "quantity": ("Int32", "integer", True),
        "discount": ("Nullable(Float64)", "number", None),
        "is_gift": ("Bool", "boolean", True),
        "order_date": ("DATE", "date", True),
        "order_timestamp": ("DateTime64(3, 'UTC')", "timestamp", True),
        "tags": ("Array(String)", "array", True),
        "updated_at": ("DateTime", "timestamp", True),
    }


def test_import_sql_clickhouse_produces_a_valid_contract():
    result = DataContract.import_from_source("sql", sql_file_path, dialect="clickhouse")

    assert DataContract(data_contract_str=result.to_yaml()).lint().result == "passed"
