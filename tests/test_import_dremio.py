"""Tests for the Dremio importer, run against a real Dremio container."""

import pytest
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import ResultEnum
from tests.dremio_container import PASSWORD, USERNAME, DremioContainer

dremio = DremioContainer()

# A table in a folder of a file system source, and a view deep in the folders of a space.
LAKE = '"$scratch".shop.raw'
MARTS = "shop.sales.marts.eu"


@pytest.fixture(scope="module", autouse=True)
def dremio_server(request):
    dremio.start()
    request.addfinalizer(dremio.stop)
    dremio.load(LAKE, "orders.sql")
    dremio.create_folders(["shop"], ["shop", "sales"], ["shop", "sales", "marts"], ["shop", "sales", "marts", "eu"])
    client = dremio.client()
    client.run(f"CREATE VIEW {MARTS}.orders AS SELECT * FROM {LAKE}.orders")
    client.run(f"CREATE VIEW {MARTS}.open_orders AS SELECT order_id, order_total FROM {LAKE}.orders")


@pytest.fixture(autouse=True)
def credentials(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_DREMIO_USERNAME", USERNAME)
    monkeypatch.setenv("DATACONTRACT_DREMIO_PASSWORD", PASSWORD)


def _import(schema=MARTS, **kwargs):
    return DataContract.import_from_source(
        "dremio", source=dremio.get_container_host_ip(), port=dremio.port(), schema=schema, **kwargs
    )


def _properties(odcs, schema_name="orders"):
    schema = next(s for s in odcs.schema_ if s.name == schema_name)
    return {p.name: p for p in schema.properties}


def test_import_dremio_takes_the_types_of_the_query_results():
    properties = _properties(_import(dremio_table=["orders"]))

    assert {name: (p.physicalType, p.logicalType) for name, p in properties.items()} == {
        "order_id": ("VARCHAR", "string"),
        "customer_id": ("VARCHAR", "string"),
        "order_status": ("VARCHAR", "string"),
        "currency": ("VARCHAR", "string"),
        "order_total": ("DECIMAL(10,2)", "number"),
        "quantity": ("INTEGER", "integer"),
        "line_count": ("BIGINT", "integer"),
        "discount": ("DOUBLE", "number"),
        "is_gift": ("BOOLEAN", "boolean"),
        "order_date": ("DATE", "date"),
        "order_timestamp": ("TIMESTAMP", "timestamp"),
        "tags": ("ARRAY", "array"),
        "shipping": ("STRUCT", "object"),
        "region": ("VARCHAR", "string"),
    }
    assert (properties["tags"].items.physicalType, properties["tags"].items.logicalType) == ("VARCHAR", "string")
    assert {p.name: p.physicalType for p in properties["shipping"].properties} == {"city": "VARCHAR", "zip": "VARCHAR"}


def test_import_dremio_imports_every_dataset_in_the_path_by_default():
    odcs = _import()

    assert {s.name: s.physicalType for s in odcs.schema_} == {"open_orders": "view", "orders": "view"}


def test_import_dremio_reads_a_table_in_a_folder_of_a_file_system_source():
    odcs = _import(schema=LAKE)

    assert {s.name: s.physicalType for s in odcs.schema_} == {"orders": "table"}


def test_the_server_is_the_path_imported_from():
    server = _import(dremio_table=["orders"]).servers[0]

    assert (server.type, server.host, server.port, server.schema_) == (
        "dremio",
        dremio.get_container_host_ip(),
        dremio.port(),
        MARTS,
    )


def test_imported_contract_passes_test_without_editing():
    odcs = _import()

    run = DataContract(data_contract_str=odcs.to_yaml()).test()

    print(run.pretty())
    assert run.result == ResultEnum.passed
    assert all(check.result == ResultEnum.passed for check in run.checks)
    assert any(c.field == "tags[]" and c.type == "field_physical_type" for c in run.checks)
    assert any(c.field == "shipping.city" and c.type == "field_physical_type" for c in run.checks)


def test_a_folder_with_a_period_in_its_name_is_imported_by_its_quoted_path():
    dremio.load('"$scratch"."bucket.v1".raw', "orders.sql")

    odcs = _import(schema='$scratch."bucket.v1".raw')

    assert [s.name for s in odcs.schema_] == ["orders"]
    assert odcs.servers[0].schema_ == '$scratch."bucket.v1".raw'
    assert DataContract(data_contract_str=odcs.to_yaml()).test().result == ResultEnum.passed


def test_import_dremio_produces_a_valid_contract():
    run = DataContract(data_contract_str=_import().to_yaml()).lint()

    assert run.result == ResultEnum.passed


def test_the_cli_imports_from_dremio(tmp_path):
    output = tmp_path / "datacontract.yaml"

    result = CliRunner().invoke(
        app,
        [
            "import",
            "dremio",
            "--source",
            dremio.get_container_host_ip(),
            "--port",
            str(dremio.port()),
            "--schema",
            MARTS,
            "--table",
            "open_orders",
            "--output",
            str(output),
        ],
    )

    assert result.exit_code == 0, result.output
    assert "name: open_orders" in output.read_text()


def test_import_dremio_fails_on_an_unknown_table():
    with pytest.raises(DataContractException, match="No tables or views found"):
        _import(dremio_table=["no_such_table"])


def test_import_dremio_fails_on_a_wrong_password(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_DREMIO_PASSWORD", "wrong")

    with pytest.raises(DataContractException, match="Dremio login failed"):
        _import()


def test_import_dremio_requires_a_schema():
    with pytest.raises(DataContractException, match="--schema"):
        DataContract.import_from_source("dremio", source="localhost")


def test_import_dremio_requires_a_host():
    with pytest.raises(DataContractException, match="--source"):
        DataContract.import_from_source("dremio", source=None, schema=MARTS)
