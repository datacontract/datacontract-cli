from google.cloud import bigquery
import logging

from datacontract.data_contract import DataContract

logging.basicConfig(level=logging.INFO, force=True)

# directly with Google client lib
# def test_examples_bigquery():
#     project_id = 'datameshexample-product'
#     client = bigquery.Client(project=project_id)

#     # Perform a query
#     QUERY = (
#         'SELECT field_one FROM `datameshexample-product.datacontract_cli_test_dataset.datacontract_cli_test_table` '
#         'LIMIT 100'
#     )
#     query_job = client.query(QUERY) # API request
#     rows = query_job.result() # Waits for query to finish

#     for row in rows:
#         print(row.field_one)

datacontract = "examples/bigquery/datacontract.yaml"

def test_examples_bigquery():
    data_contract = DataContract(data_contract_file=datacontract)

    run = data_contract.test()

    print(run)
    assert run.result == "passed"
    assert all(check.result == "passed" for check in run.checks)
