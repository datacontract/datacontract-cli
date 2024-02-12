import logging

from dotenv import load_dotenv

from datacontract.data_contract import DataContract

logging.basicConfig(level=logging.DEBUG, force=True)

datacontract = "examples/databricks-sql/datacontract.yaml"


def test_examples_databricks_sql():
    load_dotenv(override=True)
    # os.environ['DATACONTRACT_DATABRICKS_TOKEN'] = "xxx"
    # os.environ['DATACONTRACT_DATABRICKS_HTTP_PATH'] = "/sql/1.0/warehouses/b053a326fa014fb3"
    data_contract = DataContract(data_contract_file=datacontract)

    run = data_contract.test()

    print(run)
    assert run.result == "passed"
    assert all(check.result == "passed" for check in run.checks)
