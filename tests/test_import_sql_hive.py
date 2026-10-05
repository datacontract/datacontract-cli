import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

DDL = """
CREATE TABLE orders (
    order_id STRING NOT NULL COMMENT 'The order',
    customer_id VARCHAR(10),
    order_total DECIMAL(10,2),
    quantity INT,
    is_gift BOOLEAN,
    ordered_at TIMESTAMP,
    tags ARRAY<STRING>,
    attributes MAP<STRING,STRING>
)
PARTITIONED BY (region STRING)
STORED AS PARQUET;
"""


def _ddl_file(tmp_path):
    path = tmp_path / "orders.sql"
    path.write_text(DDL)
    return str(path)


def test_cli(tmp_path):
    result = CliRunner().invoke(app, ["import", "sql", "--source", _ddl_file(tmp_path), "--dialect", "hive"])

    assert result.exit_code == 0


def test_import_sql_hive(tmp_path):
    result = DataContract.import_from_source("sql", _ddl_file(tmp_path), dialect="hive")

    contract = yaml.safe_load(result.to_yaml())
    assert contract["servers"] == [
        {"server": "hive", "type": "hive", "host": "my_host", "port": 10000, "database": "my_database"}
    ]
    properties = {p["name"]: p for p in contract["schema"][0]["properties"]}
    assert {name: (p["physicalType"], p.get("logicalType")) for name, p in properties.items()} == {
        "order_id": ("STRING", "string"),
        "customer_id": ("VARCHAR(10)", "string"),
        "order_total": ("DECIMAL(10, 2)", "number"),
        "quantity": ("INT", "integer"),
        "is_gift": ("BOOLEAN", "boolean"),
        "ordered_at": ("TIMESTAMP", "timestamp"),
        "tags": ("ARRAY<STRING>", "array"),
        "attributes": ("MAP<STRING, STRING>", "map"),
        "region": ("STRING", "string"),
    }
    assert properties["order_id"]["required"] is True
    assert properties["order_id"]["description"] == "The order"


def test_import_sql_hive_produces_a_valid_contract(tmp_path):
    result = DataContract.import_from_source("sql", _ddl_file(tmp_path), dialect="hive")

    assert DataContract(data_contract_str=result.to_yaml()).lint().result == "passed"
