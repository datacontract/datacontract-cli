import json
from unittest.mock import MagicMock, patch

import pytest
import yaml
from dotenv import load_dotenv
from open_data_contract_standard.model import OpenDataContractStandard
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract
from datacontract.imports.snowflake_importer import import_Snowflake_from_connector
from datacontract.model.exceptions import DataContractException

# logging.basicConfig(level=logging.INFO, force=True)
load_dotenv(override=True)


data_definition_file = "fixtures/snowflake/import/ddl.sql"


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--format",
            "sql",
            "--source",
            data_definition_file,
            "--dialect",
            "snowflake",
        ],
    )
    assert result.exit_code == 0


def test_cli_connection():
    with patch("datacontract.imports.snowflake_importer.import_Snowflake_from_connector") as mock_import:
        mock_import.return_value = OpenDataContractStandard(id="test", kind="DataContract", apiVersion="v3.1.0")
        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "import",
                "--format",
                "snowflake",
                "--source",
                "test_account",
                "--database",
                "TEST_DB",
                "--schema",
                "TEST_SCHEMA",
            ],
        )
        assert result.exit_code == 0


def test_import_sql_snowflake():
    result = DataContract.import_from_source("sql", data_definition_file, dialect="snowflake")

    print("Result:\n", result.to_yaml())
    with open("fixtures/snowflake/import/datacontract.yaml") as file:
        expected = file.read()
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)


def test_import_snowflake_from_connector_success():
    account = "test_account"
    database = "TEST_DB"
    schema = "TEST_SCHEMA"

    # Mock response from Snowflake query
    # This JSON mimics the structure returned by the SQL query in snowflake_importer.py
    mock_response_data = {
        "apiVersion": "v3.1.0",
        "kind": "DataContract",
        "id": "test-id",
        "name": "TEST_SCHEMA",
        "version": "0.0.1",
        "status": "development",
        "schema": [
            {
                "id": "table1_propId",
                "name": "TABLE1",
                "physicalName": "TEST_DB.TEST_SCHEMA.TABLE1",
                "logicalType": "object",
                "physicalType": "table",
                "description": "Test table description",
                "properties": [
                    {
                        "id": "col1_propId",
                        "name": "COL1",
                        "logicalType": "string",
                        "physicalType": "VARCHAR(16777216)",
                        "required": False,
                        "unique": False,
                        "description": "Column description",
                        "customProperties": [
                            {"property": "ordinalPosition", "value": 1},
                            {"property": "scdType", "value": 1},
                        ],
                    },
                    {
                        "id": "col2_propId",
                        "name": "COL2",
                        "logicalType": "integer",
                        "physicalType": "NUMBER(38,0)",
                        "required": True,
                        "unique": False,
                        "customProperties": [
                            {"property": "ordinalPosition", "value": 2},
                            {"property": "scdType", "value": 1},
                        ],
                    },
                ],
            }
        ],
    }

    # The fetchall returns a list of tuples/lists, where the first element is the JSON string
    mock_fetchall_result = [[json.dumps(mock_response_data)]]

    with patch("datacontract.imports.snowflake_importer.snowflake_cursor") as mock_cursor_func:
        # Setup mocks
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_cursor_func.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # Mock cursor attributes and methods
        mock_cursor.sfqid = "mock_sfqid"
        mock_cursor.fetchall.return_value = mock_fetchall_result

        # Run the function
        result = import_Snowflake_from_connector(account, database, schema)

        # Verify the result
        assert result.apiVersion == "v3.1.0"
        assert result.kind == "DataContract"
        assert result.name == "TEST_SCHEMA"

        assert len(result.schema_) == 1
        table = result.schema_[0]
        assert table.name == "TABLE1"
        assert table.physicalName == "TEST_DB.TEST_SCHEMA.TABLE1"

        assert len(table.properties) == 2
        assert table.properties[0].name == "COL1"
        assert table.properties[1].name == "COL2"

        # Verify Snowflake interactions
        mock_cursor.execute.assert_any_call(f"USE SCHEMA {database}.{schema}")
        mock_cursor.execute.assert_any_call(f"SHOW COLUMNS IN SCHEMA {database}.{schema}")
        mock_cursor.execute.assert_any_call(f"SHOW PRIMARY KEYS IN SCHEMA {database}.{schema}")

        assert mock_cursor.execute_async.called
        args, _ = mock_cursor.execute_async.call_args
        query = args[0]
        assert "WITH INFO_SCHEMA_COLUMNS AS" in query
        assert f"WHERE T.table_schema = '{schema}'" in query

        mock_cursor.get_results_from_sfqid.assert_called_with("mock_sfqid")


def test_import_snowflake_from_connector_empty_result():
    account = "test_account"
    database = "TEST_DB"
    schema = "TEST_SCHEMA"

    # Empty result
    mock_fetchall_result = []

    with patch("datacontract.imports.snowflake_importer.snowflake_cursor") as mock_cursor_func:
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_cursor_func.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor
        mock_cursor.sfqid = "mock_sfqid"
        mock_cursor.fetchall.return_value = mock_fetchall_result

        with pytest.raises(DataContractException) as excinfo:
            import_Snowflake_from_connector(account, database, schema)

        assert "No data contract returned" in str(excinfo.value)


# @pytest.mark.skipif(os.environ.get("DATACONTRACT_SNOWFLAKE_USERNAME") is None, reason="Requires DATACONTRACT_SNOWFLAKE_USERNAME to be set")
# def test_cli():
#     load_dotenv(override=True)
#     # os.environ['DATACONTRACT_SNOWFLAKE_USERNAME'] = "xxx"
#     # os.environ['DATACONTRACT_SNOWFLAKE_PASSWORD'] = "xxx"
#     # os.environ['DATACONTRACT_SNOWFLAKE_ROLE'] = "xxx"
#     # os.environ['DATACONTRACT_SNOWFLAKE_WAREHOUSE'] = "COMPUTE_WH"
#     runner = CliRunner()
#     result = runner.invoke(
#         app,
#         [
#             "import",
#             "--format",
#             "snowflake",
#             "--source",
#             "workspace.canada-central.azure",
#             "--schema",
#             "PUBLIC",
#             "--database",
#             "DEMO_DB"
#         ],
#     )
#     assert result.exit_code == 0

# @pytest.mark.skipif(os.environ.get("DATACONTRACT_SNOWFLAKE_USERNAME") is None, reason="Requires DATACONTRACT_SNOWFLAKE_USERNAME to be set")
# def test_import_source():
#     load_dotenv(override=True)
#     # os.environ['DATACONTRACT_SNOWFLAKE_USERNAME'] = "xxx"
#     # os.environ['DATACONTRACT_SNOWFLAKE_PASSWORD'] = "xxx"
#     # os.environ['DATACONTRACT_SNOWFLAKE_ROLE'] = "xxx"
#     # os.environ['DATACONTRACT_SNOWFLAKE_WAREHOUSE'] = "COMPUTE_WH"
#     result = DataContract.import_source("snowflake",  {
#         "source": "workspace.canada-central.azure",
#         "schema": "PUBLIC",
#         "database": "DEMO_DB"
#     })

#     print("Result:\n", result.to_yaml())
#     with open("fixtures/snowflake/import/datacontract.yaml") as file:
#         expected = file.read()
#     assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
