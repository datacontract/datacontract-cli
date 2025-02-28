import pytest
import duckdb

from datacontract.data_contract import DataContract
from datacontract.model.run import Run
from datacontract.lint import resolve
from datacontract.engines.soda.connections.duckdb import get_duckdb_connection

def test_csv_all_fields_present():
    data_contract_str = """dataContractSpecification: 1.1.0
id: my-data-contract-id
info:
  title: My Data Contract
  version: 0.0.1
servers:
  production:
    type: local
    format: csv
    path: ./fixtures/csv/data/sample_data.csv
    delimiter: ','
models:
  sample_data:
    description: Csv file with encoding ascii
    type: table
    fields:
      field_one:
        type: string
      field_two:
        type: integer
      field_three:
        type: string
    """
    data_contract = resolve.resolve_data_contract(data_contract_str = data_contract_str)
    con = get_duckdb_connection(data_contract, data_contract.servers["production"], Run.create_run())
    assert con.table("sample_data").columns == ['field_one', 'field_two', 'field_three']
    assert con.table("sample_data").shape == (10,3)

def test_csv_missing_field():
    data_contract_str = """dataContractSpecification: 1.1.0
id: my-data-contract-id
info:
  title: My Data Contract
  version: 0.0.1
servers:
  production:
    type: local
    format: csv
    path: ./fixtures/csv/data/sample_data.csv
    delimiter: ','
models:
  sample_data:
    description: Csv file with encoding ascii
    type: table
    fields:
      field_one:
        type: string
      field_two:
        type: integer
      field_three:
        type: string
      missing_field:
        type: string
    """
    data_contract = resolve.resolve_data_contract(data_contract_str = data_contract_str)
    # this is ok
    run = Run.create_run()
    con = get_duckdb_connection(data_contract, data_contract.servers["production"], run)
    assert con.table("sample_data").columns == ['field_one', 'field_two', 'field_three']
    assert con.table("sample_data").shape == (10,3)
    assert any([c.name == 'Column order mismatch' for c in run.checks if c.result == 'warning'])
    # now test
    data_contract = DataContract(data_contract_str=data_contract_str)
    run = data_contract.test()
    checks = {k.field:k for k in run.checks if k.type == 'field_is_present'}
    assert checks['field_one'].result == 'passed'
    assert checks['field_two'].result == 'passed'
    assert checks['field_three'].result == 'passed'
    assert checks['missing_field'].result == 'failed'


def test_local_csv_extra_field():
    data_contract_str = """dataContractSpecification: 1.1.0
id: my-data-contract-id
info:
  title: My Data Contract
  version: 0.0.1
servers:
  production:
    type: local
    format: csv
    path: ./fixtures/csv/data/sample_data.csv
    delimiter: ','
models:
  sample_data:
    description: Csv file with encoding ascii
    type: table
    fields:
      field_three:
        type: string
      field_one:
        type: string
    """
    data_contract = resolve.resolve_data_contract(data_contract_str = data_contract_str)
    # this is somewhat ok
    run = Run.create_run()
    con = get_duckdb_connection(data_contract, data_contract.servers["production"], run)
    assert con.table("sample_data").columns == ['field_one', 'field_two', 'field_three']
    assert con.table("sample_data").shape == (10,3)
    assert any([c.name == 'Column order mismatch' for c in run.checks if c.result == 'warning'])
    assert any([c.name == 'Dataset contained unexpected fields' for c in run.checks if c.result == 'warning'])

    # now test
    data_contract = DataContract(data_contract_str=data_contract_str)
    run = data_contract.test()
    checks = {k.field:k for k in run.checks if k.type == 'field_is_present'}
    assert len(checks) == 2
    assert checks['field_one'].result == 'passed'
    assert checks['field_three'].result == 'passed'
