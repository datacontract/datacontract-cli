from datacontract.engines.soda.connections.duckdb_connection import get_duckdb_connection
from datacontract.lint import resolve
from datacontract.model.run import Run


def test_nested_json():
    data_contract_str = """
dataContractSpecification: 1.1.0
id: "61111-0002"
info:
  title: Sample data of nested types
  version: 1.0.0
servers:
  sample:
    type: local
    path: ./fixtures/local-json/data/nested_types.json
    format: json
    delimiter: array
models:
  sample_data:
    type: object
    fields:
      id:
        type: integer
        required: true
      tags:
        type: array
        required: true
        items:
          type: object
          fields:
            foo:
              type: string
              required: true
            arr:
              type: array
              items:
                type: integer
      name:
        type: object
        required: false
        fields:
          first:
            type: string
          last:
            type: string
    """
    data_contract = resolve.resolve_data_contract(data_contract_str=data_contract_str)
    run = Run.create_run()
    con = get_duckdb_connection(data_contract, data_contract.servers["sample"], run)
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
