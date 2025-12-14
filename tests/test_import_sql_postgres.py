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
    result = DataContract.import_from_source("sql", sql_file_path, dialect="postgres")

    expected = """
apiVersion: v3.1.0
kind: DataContract
id: my-data-contract
name: My Data Contract
version: 1.0.0
status: draft
servers:
  - server: postgres
    type: postgres
schema:
  - name: my_table
    physicalType: table
    logicalType: object
    physicalName: my_table
    properties:
      - name: field_one
        logicalType: string
        logicalTypeOptions:
          maxLength: 10
        physicalType: VARCHAR(10)
        primaryKey: true
        primaryKeyPosition: 1
      - name: field_two
        logicalType: integer
        physicalType: INT
        required: true
      - name: field_three
        logicalType: date
        physicalType: TIMESTAMPTZ
    """
    print("Result", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)


def test_import_sql_constraints():
    result = DataContract.import_from_source("sql", "fixtures/postgres/data/data_constraints.sql", dialect="postgres")

    expected = """
apiVersion: v3.1.0
kind: DataContract
id: my-data-contract
name: My Data Contract
version: 1.0.0
status: draft
servers:
  - server: postgres
    type: postgres
schema:
  - name: customer_location
    physicalType: table
    logicalType: object
    physicalName: customer_location
    properties:
      - name: id
        logicalType: number
        physicalType: DECIMAL
        required: true
      - name: created_by
        logicalType: string
        logicalTypeOptions:
          maxLength: 30
        physicalType: VARCHAR(30)
        required: true
      - name: create_date
        logicalType: date
        physicalType: TIMESTAMP
        required: true
      - name: changed_by
        logicalType: string
        logicalTypeOptions:
          maxLength: 30
        physicalType: VARCHAR(30)
      - name: change_date
        logicalType: date
        physicalType: TIMESTAMP
      - name: name
        logicalType: string
        logicalTypeOptions:
          maxLength: 120
        physicalType: VARCHAR(120)
        required: true
      - name: short_name
        logicalType: string
        logicalTypeOptions:
          maxLength: 60
        physicalType: VARCHAR(60)
      - name: display_name
        logicalType: string
        logicalTypeOptions:
          maxLength: 120
        physicalType: VARCHAR(120)
        required: true
      - name: code
        logicalType: string
        logicalTypeOptions:
          maxLength: 30
        physicalType: VARCHAR(30)
        required: true
      - name: description
        logicalType: string
        logicalTypeOptions:
          maxLength: 4000
        physicalType: VARCHAR(4000)
      - name: language_id
        logicalType: number
        physicalType: DECIMAL
        required: true
      - name: status
        logicalType: string
        logicalTypeOptions:
          maxLength: 2
        physicalType: VARCHAR(2)
        required: true
    """
    print("Result", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
