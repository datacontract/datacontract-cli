"""``enum`` on properties (ODCS v3.2.0, RFC 0033): one resolver, every consumer."""

import json

import duckdb
import pytest
import yaml
from open_data_contract_standard.model import CustomProperty, DataQuality, EnumValue, SchemaProperty

from datacontract.data_contract import DataContract
from datacontract.model.enum_values import get_enum_entries, get_enum_values
from datacontract.model.run import ResultEnum

CONTRACT = """apiVersion: v3.2.0
kind: DataContract
id: orders-enum
name: Orders
version: 1.0.0
status: active
servers:
  - server: production
    type: duckdb
    database: {database}
schema:
  - name: orders
    properties:
      - name: order_id
        logicalType: string
        physicalType: VARCHAR
      - name: status
        logicalType: string
        physicalType: VARCHAR
        enum:
          - value: placed
            label: Placed
          - value: shipped
            label: Shipped
            description: Handed to the carrier
      - name: priority
        logicalType: integer
        physicalType: INTEGER
        enum:
          - value: 1
          - value: 2
"""


def _property(**kwargs) -> SchemaProperty:
    return SchemaProperty(name="status", logicalType="string", **kwargs)


def test_enum_entries_win_over_every_legacy_representation():
    prop = _property(
        enum=[EnumValue(value="a", label="A")],
        logicalTypeOptions={"enum": ["legacy"]},
        customProperties=[CustomProperty(property="enum", value='["custom"]')],
        quality=[DataQuality(metric="invalidValues", arguments={"validValues": ["rule"]})],
    )

    assert get_enum_values(prop) == ["a"]
    assert get_enum_entries(prop)[0].label == "A"


def test_legacy_representations_are_read_in_order():
    assert get_enum_values(_property(logicalTypeOptions={"enum": ["a", "b"]})) == ["a", "b"]
    assert get_enum_values(_property(customProperties=[CustomProperty(property="enum", value='["c"]')])) == ["c"]
    assert get_enum_values(_property(customProperties=[CustomProperty(property="enum", value=["d"])])) == ["d"]
    rule = DataQuality(metric="invalidValues", arguments={"validValues": ["e"]})
    assert get_enum_values(_property(quality=[rule])) == ["e"]
    assert get_enum_values(_property(quality=[rule]), include_quality_rule=False) is None
    assert get_enum_values(_property()) is None
    assert get_enum_entries(_property()) is None


def test_legacy_values_become_entries():
    entries = get_enum_entries(_property(logicalTypeOptions={"enum": ["a"]}))

    assert [e.value for e in entries] == ["a"]
    assert entries[0].label is None


@pytest.fixture
def orders_db(tmp_path) -> str:
    path = str(tmp_path / "orders.duckdb")
    con = duckdb.connect(path)
    con.execute("CREATE TABLE orders (order_id VARCHAR, status VARCHAR, priority INTEGER)")
    con.execute("INSERT INTO orders VALUES ('1', 'placed', 1), ('2', 'shipped', 2)")
    con.close()
    return path


def test_test_checks_enum_entries(orders_db):
    run = DataContract(data_contract_str=CONTRACT.format(database=orders_db)).test()

    print(run.pretty())
    assert run.result == ResultEnum.passed
    assert {c.type for c in run.checks if c.type == "field_enum"} == {"field_enum"}
    assert sum(1 for c in run.checks if c.type == "field_enum") == 2


def test_test_fails_on_a_value_outside_the_enum(orders_db):
    con = duckdb.connect(orders_db)
    con.execute("INSERT INTO orders VALUES ('3', 'lost', 9)")
    con.close()

    run = DataContract(data_contract_str=CONTRACT.format(database=orders_db)).test()

    failed = [c for c in run.checks if c.result == ResultEnum.failed]
    assert {c.type for c in failed} == {"field_enum"}
    assert len(failed) == 2


def test_exporters_read_enum_entries():
    data_contract = DataContract(data_contract_str=CONTRACT.format(database="orders.duckdb"))

    json_schema = json.loads(data_contract.export("jsonschema"))
    assert json_schema["properties"]["status"]["enum"] == ["placed", "shipped"]
    assert json_schema["properties"]["priority"]["enum"] == [1, 2]

    pydantic_model = data_contract.export("pydantic-model")
    assert "typing.Literal['placed', 'shipped']" in pydantic_model
    assert "typing.Literal[1, 2]" in pydantic_model

    avro_contract = CONTRACT.format(database="orders.duckdb").replace(
        "      - name: status\n        logicalType: string\n        physicalType: VARCHAR\n",
        "      - name: status\n        logicalType: string\n        physicalType: enum\n",
    )
    avro = json.loads(DataContract(data_contract_str=avro_contract).export("avro"))
    status = next(f for f in avro["fields"] if f["name"] == "status")
    assert status["type"]["type"] == "enum"
    assert status["type"]["symbols"] == ["placed", "shipped"]

    protobuf = data_contract.export("protobuf")
    assert "enum Status {" in protobuf
    assert "PLACED = 0;" in protobuf and "SHIPPED = 1;" in protobuf

    html = data_contract.export("html")
    assert "Allowed values" in html
    assert "Handed to the carrier" in html

    dcs = yaml.safe_load(data_contract.export("dcs"))
    assert dcs["models"]["orders"]["fields"]["status"]["enum"] == ["placed", "shipped"]


def test_jsonschema_import_writes_enum_entries(tmp_path):
    schema = {
        "type": "object",
        "properties": {"status": {"type": "string", "enum": ["placed", "shipped"]}},
    }
    path = tmp_path / "orders.schema.json"
    path.write_text(json.dumps(schema))

    result = DataContract.import_from_source("jsonschema", str(path))

    status = result.schema_[0].properties[0]
    assert [e.value for e in status.enum] == ["placed", "shipped"]
    assert status.quality is None


def test_dcs_import_writes_enum_entries():
    dcs = """dataContractSpecification: 1.2.0
id: orders
info:
  title: Orders
  version: 1.0.0
models:
  orders:
    fields:
      status:
        type: string
        enum: [placed, shipped]
"""
    result = DataContract(data_contract_str=dcs).get_data_contract()

    status = result.schema_[0].properties[0]
    assert [e.value for e in status.enum] == ["placed", "shipped"]
    assert status.quality is None
