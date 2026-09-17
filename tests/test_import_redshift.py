"""Tests for the Redshift importer.

No Redshift is reachable in CI (and the ``SVV_*`` catalog views have no Postgres
equivalent, so a testcontainer cannot stand in either), so the psycopg
connection is faked and fed rows in the shape Redshift returns.
"""

from unittest.mock import MagicMock, patch

import pytest
import yaml
from open_data_contract_standard.model import OpenDataContractStandard
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract
from datacontract.imports.redshift_importer import redshift_connection
from datacontract.model.exceptions import DataContractException
from datacontract.model.run import ResultEnum

HOST = "my-workgroup.123456789012.us-east-1.redshift-serverless.amazonaws.com"

TABLE_COLUMNS = ["table_name", "table_type", "remarks"]
# table_type values as SVV_TABLES actually reports them on Redshift.
TABLE_ROWS = [
    ("orders", "BASE TABLE", "All orders"),
    ("order_view", "VIEW", None),
]

COLUMN_COLUMNS = [
    "table_name",
    "column_name",
    "data_type",
    "character_maximum_length",
    "numeric_precision",
    "numeric_scale",
    "is_nullable",
    "remarks",
]
COLUMN_ROWS = [
    ("order_view", "order_id", "character varying", 36, None, None, "YES", None),
    ("orders", "order_id", "character varying", 36, None, None, "NO", "The order id"),
    ("orders", "order_total", "numeric", None, 10, 2, "YES", None),
    ("orders", "line_count", "integer", None, 32, 0, "YES", None),
    ("orders", "ordered_at", "timestamp without time zone", None, None, None, "YES", None),
    ("orders", "payload", "super", None, None, None, "YES", None),
]

PRIMARY_KEY_COLUMNS = ["table_name", "column_name", "ordinal_position"]
PRIMARY_KEY_ROWS = [("orders", "order_id", 1)]


class FakeCursor:
    """Serves the catalog rows matching whichever query the importer runs."""

    def __init__(self, failing_query: str = None):
        self.failing_query = failing_query
        self.description = None
        self._rows = []

    def __enter__(self):
        return self

    def __exit__(self, *exc_info):
        return False

    def execute(self, query, params=None):
        if self.failing_query and self.failing_query in query:
            raise RuntimeError("permission denied")
        if "svv_tables" in query:
            columns, self._rows = TABLE_COLUMNS, TABLE_ROWS
        elif "svv_columns" in query:
            columns, self._rows = COLUMN_COLUMNS, COLUMN_ROWS
        else:
            columns, self._rows = PRIMARY_KEY_COLUMNS, PRIMARY_KEY_ROWS
        self.description = [(column,) for column in columns]

    def fetchall(self):
        return self._rows


class FakeConnection:
    def __init__(self, failing_query: str = None):
        self.failing_query = failing_query
        self.rollbacks = 0
        self.closed = False

    def cursor(self):
        return FakeCursor(self.failing_query)

    def rollback(self):
        self.rollbacks += 1

    def close(self):
        self.closed = True


def _import(connection=None, **kwargs):
    connection = connection or FakeConnection()
    with patch("datacontract.imports.redshift_importer.redshift_connection", return_value=connection):
        return DataContract.import_from_source("redshift", HOST, **kwargs)


def test_import_redshift():
    result = _import(database="dev", schema="analytics", redshift_table=["orders"])

    expected = f"""
apiVersion: v3.2.0
kind: DataContract
id: my-data-contract
name: My Data Contract
version: 1.0.0
status: draft
servers:
  - server: redshift
    type: redshift
    host: {HOST}
    port: 5439
    database: dev
    schema: analytics
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
      - name: ordered_at
        logicalType: timestamp
        physicalType: timestamp without time zone
      - name: payload
        physicalType: super
    """

    print("Result", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)


def test_import_redshift_produces_a_valid_contract():
    result = _import(database="dev", schema="analytics")

    run = DataContract(data_contract_str=result.to_yaml()).lint()

    assert run.result == ResultEnum.passed


def test_import_redshift_imports_all_tables_by_default():
    result = _import(database="dev", schema="analytics")

    assert [schema.name for schema in result.schema_] == ["order_view", "orders"]
    assert result.schema_[0].physicalType == "view"


def test_import_redshift_closes_the_connection():
    connection = FakeConnection()
    _import(connection, database="dev", schema="analytics")

    assert connection.closed


def test_import_redshift_without_primary_key_access():
    """A user without access to information_schema constraints still gets a contract."""
    connection = FakeConnection(failing_query="table_constraints")
    result = _import(connection, database="dev", schema="analytics", redshift_table=["orders"])

    assert result.schema_[0].properties[0].primaryKey is None
    assert connection.rollbacks == 1


def test_import_redshift_fails_on_an_unreadable_catalog():
    with pytest.raises(DataContractException) as exc_info:
        _import(FakeConnection(failing_query="svv_columns"), database="dev", schema="analytics")

    assert "Could not read the Redshift catalog" in exc_info.value.reason


def test_import_redshift_fails_on_an_unknown_table():
    with pytest.raises(DataContractException) as exc_info:
        _import(database="dev", schema="analytics", redshift_table=["does_not_exist"])

    assert "No tables found" in exc_info.value.reason


@pytest.mark.parametrize(
    "kwargs, expected_reason",
    [
        ({"database": None, "schema": "analytics"}, "database is required"),
        ({"database": "dev", "schema": None}, "schema is required"),
    ],
)
def test_import_redshift_requires_database_and_schema(kwargs, expected_reason):
    with pytest.raises(DataContractException) as exc_info:
        _import(**kwargs)

    assert expected_reason in exc_info.value.reason


def test_import_redshift_requires_host():
    with pytest.raises(DataContractException) as exc_info:
        DataContract.import_from_source("redshift", None, database="dev", schema="analytics")

    assert "endpoint host is required" in exc_info.value.reason


def test_connection_uses_the_shared_login_resolution(monkeypatch):
    """The import authenticates exactly like the test path — IAM included."""
    monkeypatch.setenv("DATACONTRACT_REDSHIFT_AUTHENTICATION", "iam")
    aws = MagicMock()
    aws.get_credentials.return_value = {"dbUser": "IAM:alice", "dbPassword": "temporary"}

    with patch("boto3.client", return_value=aws), patch("psycopg.connect") as connect:
        redshift_connection(host=HOST, port=5439, database="dev")

    assert connect.call_args.kwargs == {
        "host": HOST,
        "port": 5439,
        "dbname": "dev",
        "user": "IAM:alice",
        "password": "temporary",
        "sslmode": "require",
        # Redshift reports client_encoding as "UNICODE", which psycopg can't map.
        "client_encoding": "utf8",
    }


def test_cli_schema_option_is_not_rewritten_to_json_schema():
    """`--schema` means the database schema here, not the v0.12.0 `--json-schema`."""
    with patch("datacontract.imports.redshift_importer.import_redshift_from_connector") as mock_import:
        mock_import.return_value = OpenDataContractStandard(id="test", kind="DataContract", apiVersion="v3.1.0")
        runner = CliRunner()
        result = runner.invoke(
            app,
            ["import", "redshift", "--source", HOST, "--database", "dev", "--schema", "analytics"],
        )

    assert result.exit_code == 0
    assert mock_import.call_args.kwargs["schema"] == "analytics"
    assert "--json-schema" not in result.output
