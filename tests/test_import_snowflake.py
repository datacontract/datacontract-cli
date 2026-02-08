#from typer.testing import CliRunner

#from datacontract.cli import app
#from datacontract.data_contract import DataContract

# logging.basicConfig(level=logging.INFO, force=True)

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
