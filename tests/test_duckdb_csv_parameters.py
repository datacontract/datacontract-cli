import pytest
from datacontract_specification.model import Server

from datacontract.engines.soda.connections.duckdb_connection import build_csv_parameters, get_duckdb_connection
from datacontract.lint import resolve
from datacontract.model.run import Run


def test_build_csv_parameters_with_infer_schema_true():
    """Test CSV parameters when infer_schema is True (default behavior)."""
    # Create a server configuration with infer_schema=True
    server_data = {
        "type": "local",
        "format": "csv",
        "path": "./test.csv", 
        "infer_schema": True,
        "delimiter": ",",
        "header": True
    }
    server = Server(**server_data)
    
    params = build_csv_parameters(server)
    
    assert params == ""


def test_build_csv_parameters_with_infer_schema_false():
    """Test CSV parameters when infer_schema is False."""
    # Create a server configuration with infer_schema=False
    server_data = {
        "type": "local",
        "format": "csv",
        "path": "./test.csv", 
        "infer_schema": False,
        "delimiter": ",",
        "header": True
    }
    server = Server(**server_data)
    
    params = build_csv_parameters(server)
    
    assert "delim=','" in params
    assert "header=true" in params


def test_build_csv_parameters_all_options():
    """Test CSV parameters with all supported options."""
    server = Server(
        type="local", 
        format="csv",
        path="./test.csv",
        infer_schema=False,
        all_varchar=False,
        comment="#",
        compression="gzip", 
        delimiter=";",
        decimal_separator=",",
        escape="\\",
        header=True,
        new_line="\\n",
        quote="\"",
        skip=1,
        encoding="utf-8"
    )
    
    params = build_csv_parameters(server)
    
    assert "all_varchar=false" in params
    assert "comment='#'" in params
    assert "compression='gzip'" in params
    assert "delim=';'" in params
    assert "decimal_separator=','" in params
    assert "escape='\\'" in params
    assert "header=true" in params
    assert "new_line='\\n'" in params
    assert "quote='\"'" in params
    assert "skip=1" in params
    assert "encoding='utf-8'" in params

def test_csv_connection_with_custom_parameters():
    """Test that custom CSV parameters work in actual DuckDB connection."""
    data_contract_str = """
dataContractSpecification: 1.2.1
id: "csv-params-test"
info:
  title: CSV Parameters Test
  version: 1.0.0
servers:
  sample:
    type: local
    path: ./fixtures/csv/data/sample_data.csv
    format: csv
    infer_schema: true
    delimiter: ','
    header: true
models:
  sample_data:
    type: table
    fields:
      field_one:
        type: string
      field_two: 
        type: integer
      field_three:
        type: timestamp
    """
    
    data_contract = resolve.resolve_data_contract(data_contract_str=data_contract_str)
    run = Run.create_run()
    
    # This should not raise an exception and should create the connection successfully
    con = get_duckdb_connection(data_contract, data_contract.servers["sample"], run)
    
    # Verify the table was created and has the expected columns
    tbl = con.table("sample_data")
    assert tbl.columns == ["field_one", "field_two", "field_three"]
    
    # Verify we can fetch data
    row = tbl.fetchone()
    assert row is not None
    assert len(row) == 3


def test_build_csv_parameters_empty():
    """Test that build_csv_parameters can return empty string."""
    server = Server(
        type="local",
        format="csv",
        path="./test.csv"
    )
    
    params = build_csv_parameters(server)
    
    # Should return empty string when no additional parameters are set
    assert params == ""


def test_csv_connection_no_infer_schema():
    """Test CSV connection with infer_schema=False."""
    data_contract_str = """
dataContractSpecification: 1.2.1
id: "csv-no-infer-test" 
info:
  title: CSV No Infer Test
  version: 1.0.0
servers:
  sample:
    type: local
    path: ./fixtures/csv/data/sample_data.csv
    format: csv
    delimiter: ','
    header: true
models:
  sample_data:
    type: table
    fields:
      field_one:
        type: string
      field_two:
        type: integer
      field_three:
        type: timestamp
    """
    
    data_contract = resolve.resolve_data_contract(data_contract_str=data_contract_str)
    run = Run.create_run()
    
    # This should work with explicit column definitions 
    con = get_duckdb_connection(data_contract, data_contract.servers["sample"], run)
    
    # Verify the table was created
    tbl = con.table("sample_data")
    assert tbl.columns == ["field_one", "field_two", "field_three"]


def test_csv_connection_with_wrong_delimiter_should_fail():
    """Negative test: CSV connection with wrong delimiter should fail."""
    data_contract_str = """
dataContractSpecification: 1.2.1
id: "csv-wrong-delimiter-test"
info:
  title: CSV Wrong Delimiter Test
  version: 1.0.0
servers:
  sample:
    type: local
    path: ./fixtures/csv/data/sample_data.csv
    format: csv
    infer_schema: false
    delimiter: ';'  # Wrong delimiter - file uses comma
    header: true
models:
  sample_data:
    type: table
    fields:
      field_one:
        type: string
      field_two:
        type: integer
      field_three:
        type: timestamp
    """
    
    data_contract = resolve.resolve_data_contract(data_contract_str=data_contract_str)
    run = Run.create_run()
    
    with pytest.raises(Exception):
        get_duckdb_connection(data_contract, data_contract.servers["sample"], run)


def test_csv_connection_with_wrong_header_setting_should_fail():
    """Negative test: CSV connection with wrong header setting should fail when fetching data."""
    data_contract_str = """
dataContractSpecification: 1.2.1
id: "csv-wrong-header-test"
info:
  title: CSV Wrong Header Test
  version: 1.0.0
servers:
  sample:
    type: local
    path: ./fixtures/csv/data/sample_data.csv
    format: csv
    infer_schema: false
    delimiter: ','
    header: false  # Wrong - file actually has header
models:
  sample_data:
    type: table
    fields:
      field_one:
        type: string
      field_two:
        type: integer
      field_three:
        type: timestamp
    """
    
    data_contract = resolve.resolve_data_contract(data_contract_str=data_contract_str)
    run = Run.create_run()
    
    # Connection creation should succeed, but data fetching should fail
    con = get_duckdb_connection(data_contract, data_contract.servers["sample"], run)
    tbl = con.table("sample_data")
    assert tbl.columns == ["field_one", "field_two", "field_three"]
    
    # This should fail because header row can't be converted to expected types
    with pytest.raises(Exception) as exc_info:
        tbl.fetchall()
    
    # Should get ConversionException when trying to convert header strings to integers/timestamps
    assert "ConversionException" in str(type(exc_info.value)) or "Could not convert" in str(exc_info.value)


def test_csv_connection_with_wrong_quote_character():
    """Negative test: CSV connection with wrong quote character should fail due to SQL syntax error."""
    data_contract_str = """
dataContractSpecification: 1.2.1
id: "csv-wrong-quote-test"
info:
  title: CSV Wrong Quote Test
  version: 1.0.0
servers:
  sample:
    type: local
    path: ./fixtures/csv/data/sample_data.csv
    format: csv
    infer_schema: false
    delimiter: ','
    header: true
    quote: "'"  # Single quote causes SQL syntax issues in parameter string
models:
  sample_data:
    type: table
    fields:
      field_one:
        type: string
      field_two:
        type: integer
      field_three:
        type: timestamp
    """
    
    data_contract = resolve.resolve_data_contract(data_contract_str=data_contract_str)
    run = Run.create_run()
    
    # This should fail due to SQL syntax error with single quotes
    with pytest.raises(Exception) as exc_info:
        get_duckdb_connection(data_contract, data_contract.servers["sample"], run)
    
    # Should get ParserException due to unterminated quoted string in SQL
    assert "ParserException" in str(type(exc_info.value)) or "unterminated quoted string" in str(exc_info.value)


def test_csv_connection_with_skip_parameter():
    """Negative test: CSV connection with wrong skip parameter produces incorrect results."""
    data_contract_str = """
dataContractSpecification: 1.2.1
id: "csv-wrong-skip-test"
info:
  title: CSV Wrong Skip Test
  version: 1.0.0
servers:
  sample:
    type: local
    path: ./fixtures/csv/data/sample_data.csv
    format: csv
    infer_schema: false
    skip: 2  # Wrong - skips one data row unnecessarily
models:
  sample_data:
    type: table
    fields:
      field_one:
        type: string
      field_two:
        type: integer
      field_three:
        type: timestamp
    """
    
    data_contract = resolve.resolve_data_contract(data_contract_str=data_contract_str)
    run = Run.create_run()
    
    con = get_duckdb_connection(data_contract, data_contract.servers["sample"], run)
    
    tbl = con.table("sample_data")
    assert tbl.columns == ["field_one", "field_two", "field_three"]
    
    rows = tbl.fetchall()
    
    # Should have 9 rows instead of 11 because skip=2 skips header + 1 data row
    assert len(rows) == 9
    
    # Verify we're missing the first two data rows (CX-263-DU and IK-894-MN)
    first_row = rows[0]
    # Should be the third data row instead of the first
    assert str(first_row[0]) != "CX-263-DU"  # First data row was skipped
    assert str(first_row[0]) == "IK-894-MN"  # This should be the actual first row now
