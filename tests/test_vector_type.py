"""``logicalType: vector`` (ODCS v3.2.0, RFC 0042): embeddings as a typed column."""

import json

import duckdb
import pyarrow
import pyarrow.parquet
import pytest
import yaml
from open_data_contract_standard.model import SchemaProperty

from datacontract.data_contract import DataContract
from datacontract.engines.checks.type_normalize import (
    normalize_type_name,
    schema_property_matches,
    schema_property_mismatch_reason,
)
from datacontract.export.sql_type_converter import convert_to_sql_type
from datacontract.model.run import ResultEnum
from datacontract.model.vector_type import is_vector, parse_vector_type, vector_dimensions, vector_element_type

CONTRACT = """apiVersion: v3.2.0
kind: DataContract
id: documents
name: Documents
version: 1.0.0
status: active
servers:
  - server: production
    type: duckdb
    database: {database}
schema:
  - name: documents
    properties:
      - name: document_id
        logicalType: string
        physicalType: VARCHAR
      - name: embedding
        logicalType: vector
        physicalType: FLOAT[3]
        logicalTypeOptions:
          dimensions: {dimensions}
          elementType: float32
          distanceMetric: cosine
          normalized: true
          embeddingModel: openai/text-embedding-3-small
"""


def _vector(dimensions=1536, **options) -> SchemaProperty:
    return SchemaProperty(
        name="embedding", logicalType="vector", logicalTypeOptions={"dimensions": dimensions, **options}
    )


# --- the helper --------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "type_string, expected",
    [
        ("vector(1536)", (1536, "float32")),
        ("VECTOR(1536)", (1536, "float32")),
        ("halfvec(768)", (768, "float16")),
        ("vector", (None, "float32")),
        ("VECTOR(FLOAT, 1536)", (1536, "float32")),
        ("VECTOR(INT, 8)", (8, "int8")),
        ("FLOAT[3]", (3, "float32")),
        ("DOUBLE[3]", (3, "float64")),
        ("ARRAY<FLOAT>", None),
        ("varchar(10)", None),
    ],
)
def test_parse_vector_type(type_string, expected):
    assert parse_vector_type(type_string) == expected


def test_dimensions_and_element_type():
    assert vector_dimensions(_vector(1536)) == 1536
    assert vector_element_type(_vector(1536)) == "float32"
    assert vector_element_type(_vector(1536, elementType="float64")) == "float64"
    native = SchemaProperty(name="embedding", physicalType="vector(768)")
    assert is_vector(native)
    assert vector_dimensions(native) == 768
    assert not is_vector(SchemaProperty(name="tags", logicalType="array"))
    assert normalize_type_name("halfvec(768)") == "vector"
    assert normalize_type_name("FLOAT[1536]") == "vector"


# --- the comparator ----------------------------------------------------------------------------


def test_vector_matches_a_native_vector_and_an_array_of_numbers():
    expected = _vector(3)
    assert schema_property_matches(expected, SchemaProperty(logicalType="vector", physicalType="vector(3)"))
    assert schema_property_matches(
        expected, SchemaProperty(logicalType="array", items=SchemaProperty(logicalType="number"))
    )
    assert schema_property_matches(expected, SchemaProperty(logicalType="vector"))  # dimensions unknown


def test_vector_mismatches():
    expected = _vector(3)
    wrong_dimensions = SchemaProperty(logicalType="vector", physicalType="vector(4)")
    assert not schema_property_matches(expected, wrong_dimensions)
    assert "expected 3 dimensions but got 4" in schema_property_mismatch_reason(expected, wrong_dimensions)
    strings = SchemaProperty(logicalType="array", items=SchemaProperty(logicalType="string"))
    assert not schema_property_matches(expected, strings)
    assert "array of 'string'" in schema_property_mismatch_reason(expected, strings)
    assert not schema_property_matches(expected, SchemaProperty(logicalType="string"))


@pytest.mark.parametrize(
    "expected_element,actual_element",
    [("float32", "float64"), ("float32", "int8"), ("float16", "bfloat16"), ("int8", "uint8")],
)
def test_vector_element_mismatches(expected_element, actual_element):
    expected = _vector(3, elementType=expected_element)
    actual = _vector(3, elementType=actual_element)
    assert not schema_property_matches(expected, actual)
    reason = schema_property_mismatch_reason(expected, actual)
    assert expected_element in reason and actual_element in reason


def test_unknown_actual_element_type_does_not_assume_float32():
    assert schema_property_matches(_vector(3, elementType="float64"), SchemaProperty(logicalType="vector"))


def test_equal_physical_types_do_not_hide_conflicting_vector_options():
    expected = _vector(3, elementType="float64").model_copy(update={"physicalType": "FLOAT[3]"})
    actual = SchemaProperty(logicalType="vector", physicalType="FLOAT[3]")
    assert not schema_property_matches(expected, actual)
    assert "float64" in schema_property_mismatch_reason(expected, actual)


def test_nested_vector_elements_keep_catalog_information():
    import ibis.expr.datatypes as dt

    from datacontract.engines.ibis.dtype_category import ibis_dtype_to_schema_property

    actual = ibis_dtype_to_schema_property(dt.Struct({"vectors": dt.Map(dt.string, dt.Array(dt.float64))}))
    expected = SchemaProperty.model_validate(
        {
            "logicalType": "object",
            "properties": [
                {
                    "name": "vectors",
                    "logicalType": "map",
                    "map": {
                        "key": {"logicalType": "string"},
                        "value": {
                            "logicalType": "vector",
                            "logicalTypeOptions": {"dimensions": 3, "elementType": "float32"},
                        },
                    },
                }
            ],
        }
    )
    assert not schema_property_matches(expected, actual)
    reason = schema_property_mismatch_reason(expected, actual)
    assert "vectors[value]" in reason and "float64" in reason


@pytest.mark.parametrize(
    "native,expected_element,passes",
    [
        ("FLOAT[3]", "float32", True),
        ("DOUBLE[3]", "float32", False),
        ("DOUBLE[3]", "float64", True),
        ("TINYINT[3]", "float32", False),
        ("TINYINT[3]", "int8", True),
    ],
)
def test_runtime_vector_elements_without_declared_physical_type(tmp_path, native, expected_element, passes):
    path = str(tmp_path / "vectors.duckdb")
    con = duckdb.connect(path)
    con.execute(f"CREATE TABLE documents (embedding {native})")
    con.close()
    document = yaml.safe_load(CONTRACT.format(database=path, dimensions=3))
    prop = document["schema"][0]["properties"][1]
    prop.pop("physicalType")
    prop["logicalTypeOptions"]["elementType"] = expected_element
    document["schema"][0]["properties"] = [prop]
    run = DataContract(data_contract_str=yaml.safe_dump(document)).test()
    assert (run.result == ResultEnum.passed) is passes, run.pretty()
    if not passes:
        assert any("vector element type" in (c.reason or "") for c in run.checks if c.result == ResultEnum.failed)


# --- datacontract test against DuckDB -----------------------------------------------------------


@pytest.fixture
def documents_db(tmp_path) -> str:
    path = str(tmp_path / "documents.duckdb")
    con = duckdb.connect(path)
    con.execute("CREATE TABLE documents (document_id VARCHAR, embedding FLOAT[3])")
    con.execute("INSERT INTO documents VALUES ('1', [0.1, 0.2, 0.3]::FLOAT[3])")
    con.close()
    return path


def test_test_accepts_a_fixed_size_float_array(documents_db):
    run = DataContract(data_contract_str=CONTRACT.format(database=documents_db, dimensions=3)).test()

    print(run.pretty())
    assert run.result == ResultEnum.passed


def test_test_fails_on_an_array_of_strings(tmp_path):
    # DuckDB reports a fixed-size array without its length, so the element type is
    # what the check can verify there; dimensions are compared where the catalog
    # states them (Snowflake VECTOR(FLOAT, n), a declared physicalType).
    path = str(tmp_path / "documents.duckdb")
    con = duckdb.connect(path)
    con.execute("CREATE TABLE documents (document_id VARCHAR, embedding VARCHAR[3])")
    con.execute("INSERT INTO documents VALUES ('1', ['a', 'b', 'c']::VARCHAR[3])")
    con.close()
    contract = CONTRACT.format(database=path, dimensions=3).replace("        physicalType: FLOAT[3]\n", "")

    run = DataContract(data_contract_str=contract).test()

    print(run.pretty())
    assert run.result == ResultEnum.failed
    failed = [c for c in run.checks if c.result == ResultEnum.failed]
    assert any("array of 'string'" in (c.reason or "") for c in failed), [c.reason for c in failed]


# --- exporters ---------------------------------------------------------------------------------


@pytest.mark.parametrize(
    "server_type, expected",
    [
        ("postgres", "vector(1536)"),
        ("snowflake", "VECTOR(FLOAT, 1536)"),
        ("local", "FLOAT[1536]"),
        ("mysql", "vector(1536)"),
        ("databricks", "ARRAY<FLOAT>"),
        ("dataframe", "ARRAY<FLOAT>"),
        ("trino", "array(real)"),
        ("clickhouse", "Array(Float32)"),
        ("bigquery", "ARRAY<FLOAT64>"),
    ],
)
def test_sql_types(server_type, expected):
    assert convert_to_sql_type(_vector(1536), server_type) == expected


def test_sql_types_for_other_element_types():
    assert convert_to_sql_type(_vector(768, elementType="float16"), "postgres") == "halfvec(768)"
    assert convert_to_sql_type(_vector(8, elementType="int8"), "snowflake") == "VECTOR(INT, 8)"
    assert convert_to_sql_type(_vector(3, elementType="float64"), "local") == "DOUBLE[3]"
    assert convert_to_sql_type(_vector(3, elementType="float64"), "databricks") == "ARRAY<DOUBLE>"


def test_exporters_read_the_vector():
    data_contract = DataContract(data_contract_str=CONTRACT.format(database="documents.duckdb", dimensions=3))

    json_schema = json.loads(data_contract.export("jsonschema"))
    embedding = json_schema["properties"]["embedding"]
    assert embedding["type"] == ["array", "null"]
    assert embedding["items"] == {"type": "number"}
    assert embedding["minItems"] == 3 and embedding["maxItems"] == 3

    avro = json.loads(data_contract.export("avro"))
    embedding = next(f for f in avro["fields"] if f["name"] == "embedding")
    assert embedding["type"] == {"type": "array", "items": "float"}

    assert "array<float>" in data_contract.export("avro-idl")
    assert "ArrayType(" in data_contract.export("spark") and "FloatType()" in data_contract.export("spark")
    assert "repeated float embedding" in data_contract.export("protobuf")
    assert "list[float]" in data_contract.export("pydantic-model")
    assert "[]float32" in data_contract.export("go")
    assert "ARRAY(Float)" in data_contract.export("sqlalchemy")
    assert "FLOAT[3]" in data_contract.export("sql", sql_server_type="local")

    iceberg = json.loads(data_contract.export("iceberg"))
    embedding = next(f for f in iceberg["fields"] if f["name"] == "embedding")
    assert embedding["type"]["type"] == "list" and embedding["type"]["element"] == "float"

    bigquery_contract = CONTRACT.format(database="documents.duckdb", dimensions=3).replace(
        "    type: duckdb\n    database: documents.duckdb\n", "    type: bigquery\n    project: p\n    dataset: d\n"
    )
    bigquery = json.loads(DataContract(data_contract_str=bigquery_contract, server="production").export("bigquery"))
    embedding = next(f for f in bigquery["schema"]["fields"] if f["name"] == "embedding")
    assert embedding["type"] == "FLOAT64" and embedding["mode"] == "REPEATED"

    html = data_contract.export("html")
    assert "dimensions: 3" in html and "embeddingModel: openai/text-embedding-3-small" in html

    dcs = yaml.safe_load(data_contract.export("dcs"))
    field = dcs["models"]["documents"]["fields"]["embedding"]
    assert field["type"] == "array" and field["items"]["type"] == "float"

    # the type expectation carries a platform type, never the bare logical name
    great_expectations = json.loads(data_contract.export("great-expectations"))
    type_expectations = [
        e["kwargs"]["type_"]
        for e in great_expectations["expectations"]
        if e["type"] == "expect_column_values_to_be_of_type" and e["kwargs"]["column"] == "embedding"
    ]
    assert "vector" not in type_expectations

    exported = yaml.safe_load(data_contract.export("odcs"))
    assert exported["schema"][0]["properties"][1]["logicalTypeOptions"]["dimensions"] == 3


# --- importers ---------------------------------------------------------------------------------


def test_sql_import_reads_pgvector_and_snowflake_vectors(tmp_path):
    ddl = tmp_path / "documents.sql"
    ddl.write_text("CREATE TABLE documents (document_id varchar, embedding vector(1536), summary halfvec(768));")
    result = DataContract.import_from_source("sql", str(ddl), dialect="postgres")
    embedding, summary = result.schema_[0].properties[1], result.schema_[0].properties[2]
    assert embedding.logicalType == "vector"
    assert embedding.logicalTypeOptions == {"dimensions": 1536, "elementType": "float32"}
    assert summary.logicalTypeOptions == {"dimensions": 768, "elementType": "float16"}

    ddl.write_text("CREATE TABLE documents (embedding VECTOR(FLOAT, 1024));")
    result = DataContract.import_from_source("sql", str(ddl), dialect="snowflake")
    embedding = result.schema_[0].properties[0]
    assert embedding.logicalType == "vector"
    assert embedding.logicalTypeOptions["dimensions"] == 1024


def test_parquet_import_reads_a_fixed_size_list_of_floats_as_a_vector(tmp_path):
    table = pyarrow.table({"embedding": pyarrow.array([[0.1, 0.2, 0.3]], type=pyarrow.list_(pyarrow.float32(), 3))})
    path = tmp_path / "documents.parquet"
    pyarrow.parquet.write_table(table, path)

    result = DataContract.import_from_source("parquet", str(path))

    embedding = result.schema_[0].properties[0]
    assert embedding.logicalType == "vector"
    assert embedding.logicalTypeOptions == {"dimensions": 3, "elementType": "float32"}
