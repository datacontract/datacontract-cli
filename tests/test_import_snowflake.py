from unittest.mock import MagicMock, patch

from dotenv import load_dotenv
from open_data_contract_standard.model import OpenDataContractStandard
from snowflake.connector.constants import QueryStatus
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.imports.snowflake_importer import (
    account_usage_lineage_query,
    import_information_schema,
    import_snowflake_from_connector,
)

# logging.basicConfig(level=logging.INFO, force=True)
load_dotenv(override=True)


data_definition_file = "fixtures/snowflake/import/ddl.sql"


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "snowflake",
            "--source",
            "test_account",
            "--database",
            "TEST_DB",
            "--schema",
            "TEST_SCHEMA",
        ],
    )
    assert result.exit_code == 1
    assert "user" in result.exception.msg.lower()


def test_cli_connection():
    with patch("datacontract.imports.snowflake_importer.import_snowflake_from_connector") as mock_import:
        mock_import.return_value = OpenDataContractStandard(id="test", kind="DataContract", apiVersion="v3.1.0")
        runner = CliRunner()
        result = runner.invoke(
            app,
            [
                "import",
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


def test_import_snowflake_from_connector_success():
    account = "test_account"
    database = "TEST_DB"
    schema = "TEST_SCHEMA"

    # Mock response from Snowflake query
    # This JSON mimics the structure returned by the SQL query in snowflake_importer.py

    mock_schemas = [
        {
            "TABLE_CATALOG": "TEST_DB",
            "TABLE_SCHEMA": "TEST_SCHEMA",
            "TABLE_NAME": "TABLE1",
            "DESCRIPTION": "Test table description",
            "PHYSICAL_TYPE": "table",
        }
    ]

    mock_properties = [
        {
            "TABLE_CATALOG": "TEST_DB",
            "TABLE_SCHEMA": "TEST_SCHEMA",
            "TABLE_NAME": "TABLE1",
            "PROPERTIES": """[
                {
                    "id": "col1_propId",
                    "name": "COL1",
                    "logicalType": "string",
                    "physicalType": "VARCHAR(16777216)",
                    "required": false,
                    "unique": false,
                    "description": "Column description",
                    "customProperties": [
                        {"property": "ordinalPosition", "value": 1},
                        {"property": "scdType", "value": 1}
                    ]
                },
                {
                    "id": "col2_propId",
                    "name": "COL2",
                    "logicalType": "integer",
                    "physicalType": "NUMBER(38,0)",
                    "required": true,
                    "unique": false,
                    "customProperties": [
                        {"property": "ordinalPosition", "value": 2},
                        {"property": "scdType", "value": 1}
                    ]
                }
            ]""",
        }
    ]

    with patch("datacontract.imports.snowflake_importer.snowflake_cursor") as mock_cursor_func:
        # Setup mocks
        mock_conn = MagicMock()
        mock_cursor = MagicMock()

        mock_cursor_func.return_value = mock_conn
        mock_cursor_func.return_value.get_query_status.return_value = QueryStatus.SUCCESS

        mock_conn.cursor.return_value.__enter__.return_value = mock_cursor

        # Mock cursor attributes and methods
        with patch("datacontract.imports.snowflake_importer.import_information_schema") as mock_import_info_schema:
            mock_import_info_schema.return_value = {
                "server": [],
                "schemas": mock_schemas,
                "properties": mock_properties,
                "tags": [],
                "quality": [],
                "lineage": [],
            }

            # Run the function
            result = import_snowflake_from_connector(account, database, schema)

            # Verify the result
            assert result.apiVersion == "v3.2.0"
            assert result.kind == "DataContract"
            assert result.name == "My Data Contract"

            assert len(result.schema_) == 1
            table = result.schema_[0]
            assert table.name == "TABLE1"
            assert table.physicalName == "TABLE1"

            assert len(table.properties) == 2
            assert table.properties[0].name == "COL1"
            assert table.properties[1].name == "COL2"


def test_import_snowflake_lineage_enterprise():
    """transformSourceObjects is populated from GET_LINEAGE on Enterprise edition."""
    account = "test_account"
    database = "TEST_DB"
    schema = "TEST_SCHEMA"

    mock_schemas = [
        {
            "TABLE_CATALOG": "TEST_DB",
            "TABLE_SCHEMA": "TEST_SCHEMA",
            "TABLE_NAME": "TABLE1",
            "DESCRIPTION": None,
            "PHYSICAL_TYPE": "table",
        }
    ]
    mock_properties = [
        {
            "TABLE_CATALOG": "TEST_DB",
            "TABLE_SCHEMA": "TEST_SCHEMA",
            "TABLE_NAME": "TABLE1",
            "PROPERTIES": """[
                {
                    "id": "col1_propId",
                    "name": "COL1",
                    "logicalType": "string",
                    "physicalType": "VARCHAR(16777216)",
                    "required": false,
                    "unique": false,
                    "customProperties": [{"property": "ordinalPosition", "value": 1}]
                },
                {
                    "id": "col2_propId",
                    "name": "COL2",
                    "logicalType": "integer",
                    "physicalType": "NUMBER(38,0)",
                    "required": false,
                    "unique": false,
                    "customProperties": [{"property": "ordinalPosition", "value": 2}]
                }
            ]""",
        }
    ]
    # Simulates GET_LINEAGE result: COL1 has one upstream source, COL2 has none
    mock_lineage = [
        {
            "TABLE_NAME": "TABLE1",
            "COLUMN_NAME": "COL1",
            "UPSTREAM_SOURCES": '["SRC_DB.SRC_SCHEMA.SRC_TABLE.SRC_COL"]',
        }
    ]

    with patch("datacontract.imports.snowflake_importer.snowflake_cursor") as mock_cursor_func:
        mock_conn = MagicMock()
        mock_cursor_func.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = MagicMock()

        with patch("datacontract.imports.snowflake_importer.import_information_schema") as mock_import_info_schema:
            mock_import_info_schema.return_value = {
                "server": [],
                "schemas": mock_schemas,
                "properties": mock_properties,
                "tags": [],
                "quality": [],
                "lineage": mock_lineage,
            }

            result = import_snowflake_from_connector(account, database, schema, lineage=True)
            mock_import_info_schema.assert_called_once_with(mock_conn, lineage=True)

            table = result.schema_[0]
            col1 = next(p for p in table.properties if p.name == "COL1")
            col2 = next(p for p in table.properties if p.name == "COL2")

            assert col1.transformSourceObjects == ["SRC_DB.SRC_SCHEMA.SRC_TABLE.SRC_COL"]
            assert col2.transformSourceObjects is None


def test_import_snowflake_lineage_non_enterprise():
    """transformSourceObjects stays None when GET_LINEAGE is unavailable (non-Enterprise)."""
    account = "test_account"
    database = "TEST_DB"
    schema = "TEST_SCHEMA"

    mock_schemas = [
        {
            "TABLE_CATALOG": "TEST_DB",
            "TABLE_SCHEMA": "TEST_SCHEMA",
            "TABLE_NAME": "TABLE1",
            "DESCRIPTION": None,
            "PHYSICAL_TYPE": "table",
        }
    ]
    mock_properties = [
        {
            "TABLE_CATALOG": "TEST_DB",
            "TABLE_SCHEMA": "TEST_SCHEMA",
            "TABLE_NAME": "TABLE1",
            "PROPERTIES": """[
                {
                    "id": "col1_propId",
                    "name": "COL1",
                    "logicalType": "string",
                    "physicalType": "VARCHAR(16777216)",
                    "required": false,
                    "unique": false,
                    "customProperties": [{"property": "ordinalPosition", "value": 1}]
                }
            ]""",
        }
    ]

    with patch("datacontract.imports.snowflake_importer.snowflake_cursor") as mock_cursor_func:
        mock_conn = MagicMock()
        mock_cursor_func.return_value = mock_conn
        mock_conn.cursor.return_value.__enter__.return_value = MagicMock()

        with patch("datacontract.imports.snowflake_importer.import_information_schema") as mock_import_info_schema:
            # lineage is [] — as if GET_LINEAGE failed on non-Enterprise and was silenced
            mock_import_info_schema.return_value = {
                "server": [],
                "schemas": mock_schemas,
                "properties": mock_properties,
                "tags": [],
                "quality": [],
                "lineage": [],
            }

            result = import_snowflake_from_connector(account, database, schema)

            table = result.schema_[0]
            col1 = next(p for p in table.properties if p.name == "COL1")
            assert col1.transformSourceObjects is None


def test_import_information_schema_lineage_is_opt_in():
    """The GET_LINEAGE query only runs when lineage is requested."""
    for lineage in (False, True):
        mock_conn = MagicMock()
        mock_cur = mock_conn.cursor.return_value.__enter__.return_value
        mock_cur.fetchall.return_value = []
        mock_conn.get_query_status.return_value = QueryStatus.SUCCESS

        result_sets = import_information_schema(mock_conn, lineage=lineage)

        executed = [c.args[0] for c in mock_cur.execute_async.call_args_list]
        assert (account_usage_lineage_query() in executed) is lineage
        assert ("lineage" in result_sets) is lineage
