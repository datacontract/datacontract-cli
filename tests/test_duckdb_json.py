from datacontract.engines.soda.connections.duckdb_connection import get_duckdb_connection
from datacontract.lint import resolve
from datacontract.model.run import Run


def test_nested_json():
    data_contract_str = """
kind: DataContract
apiVersion: v3.1.0
id: "61111-0002"
name: Sample data of nested types
version: 1.0.0
status: active
servers:
  - server: sample
    type: local
    path: ./fixtures/local-json/data/nested_types.json
    format: json
    delimiter: array
schema:
  - name: sample_data
    physicalType: object
    properties:
      - name: id
        logicalType: integer
        required: true
      - name: tags
        logicalType: array
        required: true
        items:
          logicalType: object
          properties:
            - name: foo
              logicalType: string
              required: true
            - name: arr
              logicalType: array
              items:
                logicalType: integer
      - name: name
        logicalType: object
        required: false
        properties:
          - name: first
            logicalType: string
          - name: last
            logicalType: string
    """
    data_contract = resolve.resolve_data_contract(data_contract_str=data_contract_str)
    run = Run.create_run()
    server = next(s for s in data_contract.servers if s.server == "sample")
    con = get_duckdb_connection(data_contract, server, run)
    tbl = con.table("sample_data")
    assert tbl.columns == ["id", "tags", "name"]
    assert [x[1].lower() for x in tbl.description] == ["number", "list", "dict"]
    # test that duckdb correct unpacked the nested structures.
    assert tbl.fetchone() == (
        1,
        [{"foo": "bar", "arr": [1, 2, 3]}, {"foo": "lap", "arr": [4]}],
        {"first": "John", "last": "Doe"},
    )
    assert tbl.fetchone() == (2, [{"foo": "zap", "arr": []}], None)
    assert tbl.fetchone() is None
    ## check nested tables
    tbl = con.table("sample_data__tags")
    assert tbl.columns == ["foo", "arr"]
    assert [x[1].lower() for x in tbl.description] == ["string", "list"]
    assert tbl.fetchone() == ("bar", [1, 2, 3])
    assert tbl.fetchone() == ("lap", [4])
    assert tbl.fetchone() == ("zap", [])
    assert tbl.fetchone() is None
    tbl = con.table("sample_data__tags__arr")
    assert tbl.columns == ["arr"]
    assert [x[1].lower() for x in tbl.description] == ["number"]
    assert tbl.fetchall() == [(1,), (2,), (3,), (4,)]
    tbl = con.table("sample_data__name")
    assert tbl.columns == ["first", "last"]
    assert [x[1].lower() for x in tbl.description] == ["string", "string"]
    assert tbl.fetchall() == [("John", "Doe")]


def test_empty_object():
    """Test that objects without defined fields are handled as JSON and don't create nested views."""
    data_contract_str = """
kind: DataContract
apiVersion: v3.1.0
id: "empty-object-test"
name: Test data with objects without fields
version: 1.0.0
status: active
servers:
  - server: sample
    type: local
    path: ./fixtures/local-json/data/empty_object.json
    format: json
    delimiter: array
schema:
  - name: sample_data
    physicalType: object
    properties:
      - name: id
        logicalType: integer
        required: true
      - name: metadata
        logicalType: object
        required: false
        description: "Object with no fields defined - should be treated as JSON"
      - name: name
        logicalType: string
        required: true
      - name: settings
        logicalType: object
        required: false
        description: "Object with explicitly empty fields - should be treated as JSON"
    """
    data_contract = resolve.resolve_data_contract(data_contract_str=data_contract_str)
    run = Run.create_run()
    server = next(s for s in data_contract.servers if s.server == "sample")
    con = get_duckdb_connection(data_contract, server, run)

    # Test main table exists and has correct columns
    tbl = con.table("sample_data")
    assert tbl.columns == ["id", "metadata", "name", "settings"]

    # Test that the data can be read correctly
    row1 = tbl.fetchone()
    assert row1[0] == 1  # id
    assert row1[2] == "Alice"  # name

    row2 = tbl.fetchone()
    assert row2[0] == 2  # id
    assert row2[2] == "Bob"  # name

    row3 = tbl.fetchone()
    assert row3[0] == 3  # id
    assert row3[2] == "Charlie"  # name

    # Test that no nested views were created for empty objects
    tables_result = con.sql("SHOW TABLES").fetchall()
    table_names = [table[0] for table in tables_result]

    # Should only have the main table, not nested views for metadata or settings
    assert "sample_data" in table_names
    assert "sample_data__metadata" not in table_names
    assert "sample_data__settings" not in table_names
