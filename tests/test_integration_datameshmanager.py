from typer.testing import CliRunner

runner = CliRunner()


# @pytest.mark.skipif(os.environ.get("DATAMESH_MANAGER_API_KEY") is None, reason="Requires DATAMESH_MANAGER_API_KEY to be set")
# def test_remote_data_contract():
#     load_dotenv(override=True)
#     data_contract = DataContract(
#         data_contract_file="https://innoq.datamesh-manager.com/checker/datacontracts/6b49c320-aaa2-4d26-bfaf-9f356a711175",
#         publish=True
#     )
#
#     run = data_contract.test()
#
#     print(run)
#     assert run.result == "passed"
#     assert len(run.checks) == 5
#     assert all(check.result == "passed" for check in run.checks)
#
