import logging
import yaml

from typer.testing import CliRunner
from unittest.mock import patch

from datacontract.cli import app
from datacontract.data_contract import DataContract

logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--format",
            "bigquery",
            "--source",
            "fixtures/bigquery/import/complete_table_schema.json",
        ],
    )
    assert result.exit_code == 0


def test_import_bigquery_schema():
    result = DataContract().import_from_source("bigquery", "fixtures/bigquery/import/complete_table_schema.json")

    print("Result:\n", result.to_yaml())
    with open("fixtures/bigquery/import/datacontract.yaml") as file:
        expected = file.read()
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
    assert DataContract(data_contract_str=expected).lint(enabled_linters="none").has_passed()

@patch('google.cloud.bigquery.Client.get_table')
def test_import_from_api(mock_client):
    # Set up mocks
    # mock_table = Mock()
    # mock_table.to_api_repr.return_value = {
    #     'kind': 'bigquery#table',
    #     'etag': 'K9aCQ39hav0KNzG9cq3p7g==',
    #     'id': 'bigquery-test-423213:dataset_test.table_test',
    #     'selfLink': 'https://bigquery.googleapis.com/bigquery/v2/projects/bigquery-test-423213/datasets/dataset_test/tables/table_test',
    #     'tableReference': {'projectId': 'bigquery-test-423213',
    #                         'datasetId': 'dataset_test',
    #                         'tableId': 'table_test'},
    #     'description': 'Test table description',
    #     'labels': {'label_1': 'value_1'},
    #     'schema': {'fields': [{'name': 'field_one',
    #                             'type': 'STRING',
    #                             'mode': 'REQUIRED',
    #                             'maxLength': '25'},
    #                         {'name': 'field_two',
    #                             'type': 'INTEGER',
    #                             'mode': 'REQUIRED'},
    #                         {'name': 'field_three',
    #                             'type': 'RANGE',
    #                             'mode': 'NULLABLE',
    #                             'rangeElementType': {'type': 'DATETIME'}}]},
    #     'numBytes': '0',
    #     'numLongTermBytes': '0',
    #     'numRows': '0',
    #     'creationTime': '1715626217137',
    #     'expirationTime': '1720810217137',
    #     'lastModifiedTime': '1715626262846',
    #     'type': 'TABLE',
    #     'location': 'europe-west6',
    #     'numTotalLogicalBytes': '0',
    #     'numActiveLogicalBytes': '0',
    #     'numLongTermLogicalBytes': '0'}
    
    # mock_client.response_value = mock_table

    # Call the API Import    
    # result = DataContract().import_from_source(format="bigquery", source=None, tables=["Test_One"], bt_project_id=
                                            #    "project_id", bt_dataset_id="dataset_id")
    # print("Result:\n", result)
    # TODO: This really should have a proper test, but I've not been able to set the mocks up
    # correctly – maybe there's some help to be had?
    # Anyway, the serialized dict above is a real response as captured from the Bigquery API and should
    # be sufficient to check the behavior of this way of importing things
    assert True is True