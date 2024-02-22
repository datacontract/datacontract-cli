import logging

import yaml

from datacontract.data_contract import DataContract

logging.basicConfig(level=logging.DEBUG, force=True)

datacontract = "examples/postgres/datacontract.yaml"
sql_file_path = "examples/postgres/data/data.sql"


def test_import_postgres():

    result = DataContract().import_from_source("postgres-sql", sql_file_path)

    expected = '''
dataContractSpecification: 0.9.2
id: postgres
info:
  title: postgres
  version: 0.0.1
  owner: my-domain-team
servers:
  postgres:
    type: postgres
    host: localhost
    port: 5432
    database: postgres
    schema: public
models:
  my_table:
    type: table
    fields:
      field_one:
        type: varchar
        required: true
        unique: true
      field_two:
        type: integer
        minimum: 10
      field_three:
        type: timestamp
    '''
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
    assert DataContract(data_contract_str=expected).lint().has_passed()

