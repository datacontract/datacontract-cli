"""Test importing Teradata SQL DDL files into Data Contracts."""

import logging

import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

logger = logging.getLogger(__name__)

sql_file_path = "fixtures/teradata/import/ddl.sql"


def test_cli():
    """Test the CLI import command for Teradata SQL DDL files."""
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


def test_import_sql_teradata():
    """Test importing a Teradata SQL DDL file into a Data Contract."""
    result = DataContract.import_from_source("sql", sql_file_path, dialect="teradata")

    expected = """
apiVersion: v3.1.0
kind: DataContract
id: my-data-contract
name: My Data Contract
version: 1.0.0
status: draft
servers:
  - server: teradata
    type: teradata
schema:
  - name: my_table
    physicalType: table
    logicalType: object
    physicalName: my_table
    properties:
      - name: field_primary_key
        physicalType: INT
        description: Primary key
        primaryKey: true
        primaryKeyPosition: 1
        logicalType: integer
      - name: field_not_null
        physicalType: INT
        description: Not null
        logicalType: integer
        required: true
      - name: field_byteint
        physicalType: SMALLINT
        description: Single-byte integer
        logicalType: integer
      - name: field_smallint
        physicalType: SMALLINT
        description: Small integer
        logicalType: integer
      - name: field_int
        physicalType: INT
        description: Regular integer
        logicalType: integer
      - name: field_bigint
        physicalType: BIGINT
        description: Large integer
        logicalType: integer
      - name: field_decimal
        physicalType: DECIMAL(10, 2)
        description: Fixed precision decimal
        logicalType: number
        logicalTypeOptions:
          precision: 10
          scale: 2
      - name: field_numeric
        physicalType: DECIMAL(18, 4)
        description: Numeric type
        logicalType: number
        logicalTypeOptions:
          precision: 18
          scale: 4
      - name: field_float
        physicalType: FLOAT
        description: Floating-point number
        logicalType: number
      - name: field_double
        physicalType: DOUBLE PRECISION
        description: Double precision float
        logicalType: number
      - name: field_char
        physicalType: CHAR(10)
        description: Fixed-length character
        logicalType: string
        logicalTypeOptions:
          maxLength: 10
      - name: field_varchar
        physicalType: VARCHAR(100)
        description: Variable-length character
        logicalType: string
        logicalTypeOptions:
          maxLength: 100
      - name: field_date
        physicalType: DATE
        description: Date only (YYYY-MM-DD)
        logicalType: date
      - name: field_time
        physicalType: TIME
        description: Time only (HH:MM:SS)
        logicalType: string
      - name: field_timestamp
        physicalType: TIMESTAMP
        description: Date and time
        logicalType: date
      - name: field_interval_year_month
        physicalType: INTERVAL YEAR TO MONTH
        description: Year-month interval
        logicalType: string
      - name: field_interval_day_second
        physicalType: INTERVAL DAY TO SECOND
        description: Day-second interval
        logicalType: string
      - name: field_byte
        physicalType: TINYINT(50)
        description: Fixed-length byte string
        logicalType: integer
      - name: field_varbyte
        physicalType: VARBYTE(100)
        description: Variable-length byte string
        logicalType: array
      - name: field_blob
        physicalType: VARBINARY
        description: Binary large object
        logicalType: array
      - name: field_clob
        physicalType: TEXT
        description: Character large object
        logicalType: string
    """
    logger.info("Result: %s", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)


def test_import_sql_constraints():
    """Test importing SQL DDL file with constraints into a Data Contract."""
    result = DataContract.import_from_source("sql", "fixtures/teradata/data/data_constraints.sql", dialect="teradata")

    expected = """
apiVersion: v3.1.0
kind: DataContract
id: my-data-contract
name: My Data Contract
version: 1.0.0
status: draft
servers:
  - server: teradata
    type: teradata
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
    logger.info("Result: %s", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
