import json

import pytest
import yaml
from typer.testing import CliRunner

from datacontract.cli import app

ODCS = """
apiVersion: v3.2.0
kind: DataContract
id: orders
version: 1.0.0
status: active
schema:
  - name: orders
    properties:
      - name: address
        logicalType: object
        properties:
          - name: zip
            logicalType: string
            examples: ["14482"]
      - name: lines
        logicalType: array
        examples: [["A1"]]
        items:
          logicalType: object
          properties:
            - name: sku
              logicalType: string
              examples: [A1]
      - name: labels
        logicalType: map
        map:
          key:
            logicalType: string
            examples: [gift]
          value:
            logicalType: string
            examples: ["yes"]
"""

JSON_SCHEMA = {
    "title": "orders",
    "type": "object",
    "properties": {"status": {"type": "string", "examples": ["shipped"]}},
}

OPENAPI = {
    "openapi": "3.0.0",
    "info": {"title": "Orders", "version": "1"},
    "servers": [{"url": "https://example.com"}],
    "paths": {"/orders": {"get": {"responses": {"200": {"content": {"application/json": {"schema": JSON_SCHEMA}}}}}}},
}

PYDANTIC = """
from pydantic import BaseModel, Field


class Order(BaseModel):
    status: str = Field(examples=["shipped"])
"""

SOURCES = {
    "csv": ("orders.csv", "status,total\nshipped,5\nopen,7\n"),
    "json": ("orders.ndjson", '{"address": {"zip": "14482"}, "tags": ["a"]}\n{"address": {"zip": "10115"}}\n'),
    "jsonschema": ("orders.schema.json", json.dumps(JSON_SCHEMA)),
    "openapi": ("openapi.yaml", yaml.safe_dump(OPENAPI)),
    "pydantic-model": ("orders.py", PYDANTIC),
    "odcs": ("orders.odcs.yaml", ODCS),
}


@pytest.mark.parametrize("format", [*SOURCES, "excel"])
def test_no_examples(format, tmp_path):
    if format == "excel":
        source = "fixtures/excel/full-odcs-3.2.xlsx"
    else:
        name, content = SOURCES[format]
        source = tmp_path / name
        source.write_text(content)
    command = ["import", format, "--source", str(source), "--output", str(tmp_path / "out.yaml")]

    assert CliRunner().invoke(app, command).exit_code == 0
    with_examples = yaml.safe_load((tmp_path / "out.yaml").read_text())
    assert with_examples != _drop_examples(with_examples)

    assert CliRunner().invoke(app, [*command, "--no-examples"]).exit_code == 0
    without_examples = yaml.safe_load((tmp_path / "out.yaml").read_text())
    assert without_examples == _drop_examples(with_examples)


def _drop_examples(node):
    if isinstance(node, dict):
        return {key: _drop_examples(value) for key, value in node.items() if key != "examples"}
    if isinstance(node, list):
        return [_drop_examples(value) for value in node]
    return node
