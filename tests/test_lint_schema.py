import json
from importlib import resources

from datacontract.lint import schema
from datacontract.lint.schema import fetch_schema

# odcs-3.1.0 has an en dash in a description: "camel case–the same"
ODCS_SCHEMA = "odcs-3.1.0.schema.json"


def test_fetch_schema_decodes_bundled_schema_as_utf8(monkeypatch, non_utf8_default_encoding):
    monkeypatch.setattr(schema, "DEFAULT_DATA_CONTRACT_SCHEMA", ODCS_SCHEMA)

    assert "camel case–the same" in json.dumps(fetch_schema(), ensure_ascii=False)


def test_fetch_schema_decodes_local_schema_as_utf8(non_utf8_default_encoding):
    location = str(resources.files("datacontract").joinpath("schemas", ODCS_SCHEMA))

    assert "camel case–the same" in json.dumps(fetch_schema(location), ensure_ascii=False)
