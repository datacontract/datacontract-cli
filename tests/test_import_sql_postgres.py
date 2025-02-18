import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

# logging.basicConfig(level=logging.DEBUG, force=True)

datacontract = "fixtures/postgres/datacontract.yaml"
sql_file_path = "fixtures/postgres/data/data.sql"


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--format",
            "sql",
            "--source",
            sql_file_path,
        ],
    )
    assert result.exit_code == 0


def test_import_sql_postgres():
    result = DataContract().import_from_source("sql", sql_file_path, dialect="postgres")

    expected = """
dataContractSpecification: 1.1.0
id: my-data-contract-id
info:
  title: My Data Contract
  version: 0.0.1
servers:
  postgres: 
    type: postgres
models:
  my_table:
    type: table
    fields:
      field_one:
        type: string
        primaryKey: true
        maxLength: 10
        config:
          postgresType: VARCHAR(10)
      field_two:
        type: int
        required: true
        config:
          postgresType: INT
      field_three:
        type: timestamp_tz
        config:
          postgresType: TIMESTAMPTZ
    """
    print("Result", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
    # Disable linters so we don't get "missing description" warnings
    assert DataContract(data_contract_str=expected).lint(enabled_linters=set()).has_passed()


def test_import_sql_constraints():
    result = DataContract().import_from_source("sql", "fixtures/postgres/data/data_constraints.sql", dialect="postgres")

    expected = """
dataContractSpecification: 1.1.0
id: my-data-contract-id
info:
  title: My Data Contract
  version: 0.0.1
servers:
  postgres:
    type: postgres
models:
  customer_location:
    type: table
    fields:
      id:
        type: decimal
        required: true
        # primaryKey: true
        config:
          postgresType: DECIMAL
      created_by:
        type: string
        required: true
        maxLength: 30
        config:
          postgresType: VARCHAR(30)
      create_date:
        type: timestamp_ntz
        required: true
        config:
          postgresType: TIMESTAMP
      changed_by:
        type: string
        maxLength: 30
        config:
          postgresType: VARCHAR(30)
      change_date:
        type: timestamp_ntz
        config:
          postgresType: TIMESTAMP
      name:
        type: string
        required: true
        maxLength: 120
        config:
          postgresType: VARCHAR(120)
      short_name:
        type: string
        maxLength: 60
        config:
          postgresType: VARCHAR(60)
      display_name:
        type: string
        required: true
        maxLength: 120
        config:
          postgresType: VARCHAR(120)
      code:
        type: string
        required: true
        maxLength: 30
        config:
          postgresType: VARCHAR(30)
      description:
        type: string
        maxLength: 4000
        config:
          postgresType: VARCHAR(4000)
      language_id:
        type: decimal
        required: true
        config:
          postgresType: DECIMAL
      status:
        type: string
        required: true
        maxLength: 2
        config:
          postgresType: VARCHAR(2)
    """
    print("Result", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
    # Disable linters so we don't get "missing description" warnings
    assert DataContract(data_contract_str=expected).lint(enabled_linters=set()).has_passed()
