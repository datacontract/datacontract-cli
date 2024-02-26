import logging

import yaml

from datacontract.data_contract import DataContract

logging.basicConfig(level=logging.DEBUG, force=True)

datacontract = "examples/postgres/datacontract.yaml"
sql_file_path = "examples/postgres/data/data.sql"


def test_import_postgres():

    result = DataContract().import_from_source("sql", sql_file_path)

    expected = '''
dataContractSpecification: 0.9.2
id: my-data-contract-id
info:
  title: My Data Contract
  version: 0.0.1
# servers:
#   postgres:
#     type: postgres
#     host: localhost
#     port: 5432
#     database: postgres
#     schema: public
models:
  my_table:
    type: table
    fields:
      field_one:
        type: varchar
        required: true
        unique: true
        maxLength: 10
      field_two:
        type: integer
        required: true
      field_three:
        type: timestamp
    '''
    print("Result", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
    assert DataContract(data_contract_str=expected).lint().has_passed()

