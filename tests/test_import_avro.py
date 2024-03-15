import logging

import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

logging.basicConfig(level=logging.DEBUG, force=True)

avro_file_path = "examples/avro/data/orders.avsc"


def test_cli():
    runner = CliRunner()
    result = runner.invoke(app, [
        "import",
        "--format", "avro",
        "--source", avro_file_path,
    ])
    assert result.exit_code == 0
    
    

def test_import_avro_schema():
    result = DataContract().import_from_source("avro", avro_file_path)

    expected = '''
dataContractSpecification: 0.9.3
id: my-data-contract-id
info:
  title: My Data Contract
  version: 0.0.1
models:
  orders:
    type: table
    description: My Model
    fields:
      ordertime:
        type: long
        description: My Field
      orderid:
        type: int
      itemid:
        type: string
      orderunits:
        type: double
      address:
        type: object
        fields:
          city:
            type: string
          state:
            type: string
          zipcode:
            type: long
    '''
    print("Result:\n", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
    assert DataContract(data_contract_str=expected).lint(enabled_linters=set()).has_passed()
