"""Tests for resolving and inlining `type: definition` references into ODCS properties."""

from unittest.mock import MagicMock, patch

import pytest
import requests
from open_data_contract_standard.model import (
    AuthoritativeDefinition,
    OpenDataContractStandard,
    SchemaObject,
    SchemaProperty,
)

from datacontract.data_contract import DataContract
from datacontract.lint.resolve import (
    _apply_definition_to_property,
    _definition_reference_url,
    _resolve_definition,
    clear_definition_cache,
    inline_definitions_into_data_contract,
)

SAMPLE_DEFINITION_YAML = """
id: foo/bar
title: Foo Bar
type: string
description: A reusable Foo Bar concept.
example: abc-123
classification: internal
tags:
  - pii:false
pattern: "^[a-z0-9-]+$"
maxLength: 32
"""


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_definition_cache()
    yield
    clear_definition_cache()


def _file_url(tmp_path, content: str = SAMPLE_DEFINITION_YAML, name: str = "definition.yaml") -> str:
    path = tmp_path / name
    path.write_text(content)
    return f"file://{path}"


def _http_response(status_code: int = 200, text: str = "") -> MagicMock:
    response = MagicMock()
    response.status_code = status_code
    response.text = text
    return response


# ---------------------------------------------------------------------------
# _resolve_definition -- a reference may be a relative path, absolute URL, or IRI
# ---------------------------------------------------------------------------


def test_resolve_definition_from_file_url(tmp_path):
    assert _resolve_definition(_file_url(tmp_path))["type"] == "string"


def test_resolve_definition_returns_none_when_missing():
    # A broken reference is non-fatal — resolution returns None.
    assert _resolve_definition("file:///does/not/exist/definition.yaml") is None


def test_resolve_definition_returns_none_for_non_object(tmp_path):
    assert _resolve_definition(_file_url(tmp_path, "- a\n- b\n")) is None


def test_resolve_definition_caches_by_url(tmp_path):
    url = _file_url(tmp_path)
    first = _resolve_definition(url)
    # Overwrite the file — a cached resolver must not see the change.
    (tmp_path / "definition.yaml").write_text("type: integer\n")
    assert _resolve_definition(url) is first


@patch("datacontract.lint.resolve.requests.get")
def test_resolve_definition_absolute_url_used_verbatim(mock_get):
    mock_get.return_value = _http_response(200, SAMPLE_DEFINITION_YAML)
    url = "https://example.com/definitions/foo.yaml"

    assert _resolve_definition(url)["type"] == "string"
    assert mock_get.call_args.args[0] == url


@patch("datacontract.lint.resolve.requests.get")
def test_resolve_definition_iri_used_verbatim(mock_get, monkeypatch):
    # An IRI is an absolute reference — used as written, not joined to a host.
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "ed_test_key")
    mock_get.return_value = _http_response(200, SAMPLE_DEFINITION_YAML)
    iri = "http://www.entropy-data.com/ns/main/sku"

    assert _resolve_definition(iri)["type"] == "string"
    assert mock_get.call_args.args[0] == iri


@patch("datacontract.lint.resolve.requests.get")
def test_resolve_definition_relative_path_joined_to_host(mock_get, monkeypatch):
    # A relative reference is resolved against ENTROPY_DATA_HOST and fetched
    # with the x-api-key header.
    monkeypatch.setenv("ENTROPY_DATA_HOST", "https://demo.entropy-data.com")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "ed_test_key")
    mock_get.return_value = _http_response(200, SAMPLE_DEFINITION_YAML)

    assert _resolve_definition("/demo576739864845/definitions/foo/bar")["type"] == "string"
    assert mock_get.call_args.args[0] == "https://demo.entropy-data.com/demo576739864845/definitions/foo/bar"
    assert mock_get.call_args.kwargs["headers"]["x-api-key"] == "ed_test_key"


@patch("datacontract.lint.resolve.requests.get")
def test_resolve_definition_does_not_leak_api_key_to_third_party_host(mock_get, monkeypatch):
    # A key is configured, but a third-party URL named in a contract must
    # never receive it -- it is fetched anonymously.
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "ed_test_key")
    monkeypatch.delenv("ENTROPY_DATA_HOST", raising=False)
    mock_get.return_value = _http_response(200, SAMPLE_DEFINITION_YAML)

    assert _resolve_definition("https://raw.githubusercontent.com/acme/defs/main/foo.yaml")["type"] == "string"
    assert "x-api-key" not in mock_get.call_args.kwargs["headers"]


@patch("datacontract.lint.resolve.requests.get")
def test_resolve_definition_self_hosted_host_gets_api_key(mock_get, monkeypatch):
    # A self-hosted instance on a custom domain (no "entropy-data.com") still
    # gets the key, because its host matches the configured ENTROPY_DATA_HOST.
    monkeypatch.setenv("ENTROPY_DATA_HOST", "https://datacontracts.acme.com")
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "ed_test_key")
    mock_get.return_value = _http_response(200, SAMPLE_DEFINITION_YAML)

    assert _resolve_definition("https://datacontracts.acme.com/v/definitions/foo")["type"] == "string"
    assert mock_get.call_args.kwargs["headers"]["x-api-key"] == "ed_test_key"


def test_resolve_definition_entropy_data_reference_without_api_key_returns_none(monkeypatch):
    monkeypatch.setenv("ENTROPY_DATA_HOST", "https://demo.entropy-data.com")
    for var in ("ENTROPY_DATA_API_KEY", "DATAMESH_MANAGER_API_KEY", "DATACONTRACT_MANAGER_API_KEY"):
        monkeypatch.delenv(var, raising=False)
    # No API key configured — the reference is skipped, not an error.
    assert _resolve_definition("/demo576739864845/definitions/foo/bar") is None


@patch("datacontract.lint.resolve.requests.get")
def test_resolve_definition_returns_none_on_http_error(mock_get):
    mock_get.return_value = _http_response(404, "not found")
    assert _resolve_definition("https://example.com/definitions/missing.yaml") is None


@patch("datacontract.lint.resolve.requests.get")
def test_resolve_definition_returns_none_on_network_error(mock_get):
    mock_get.side_effect = requests.ConnectionError("offline")
    assert _resolve_definition("https://example.com/definitions/foo.yaml") is None


@patch("datacontract.lint.resolve.requests.get")
def test_resolve_definition_caches_failure(mock_get):
    # A dead reference is resolved (and failed) once, not re-fetched per property.
    mock_get.return_value = _http_response(404, "not found")
    assert _resolve_definition("https://example.com/definitions/missing.yaml") is None
    assert _resolve_definition("https://example.com/definitions/missing.yaml") is None
    assert mock_get.call_count == 1


# ---------------------------------------------------------------------------
# _definition_reference_url
# ---------------------------------------------------------------------------


def test_reference_url_returns_definition_type():
    prop = SchemaProperty(
        name="Foo",
        authoritativeDefinitions=[AuthoritativeDefinition(type="definition", url="def.yaml")],
    )
    assert _definition_reference_url(prop) == "def.yaml"


def test_reference_url_ignores_other_types():
    # `semantics` is out of scope here; standard ODCS types must be ignored too.
    prop = SchemaProperty(
        name="Foo",
        authoritativeDefinitions=[
            AuthoritativeDefinition(type="semantics", url="s.yaml"),
            AuthoritativeDefinition(type="businessDefinition", url="b.html"),
        ],
    )
    assert _definition_reference_url(prop) is None


def test_reference_url_none_when_absent():
    assert _definition_reference_url(SchemaProperty(name="Foo")) is None


# ---------------------------------------------------------------------------
# _apply_definition_to_property -- field merge
# ---------------------------------------------------------------------------

FULL_DEFINITION = {
    "type": "string",
    "title": "Foo Bar",
    "description": "A reusable Foo Bar concept.",
    "example": "abc-123",
    "classification": "internal",
    "tags": ["pii:false"],
    "pattern": "^[a-z0-9-]+$",
    "maxLength": 32,
}


def test_apply_fills_unset_property_fields():
    prop = SchemaProperty(name="Foo")

    _apply_definition_to_property(prop, FULL_DEFINITION)

    assert prop.logicalType == "string"
    assert prop.businessName == "Foo Bar"
    assert prop.description == "A reusable Foo Bar concept."
    assert prop.classification == "internal"
    assert prop.tags == ["pii:false"]
    assert prop.examples == ["abc-123"]
    assert prop.logicalTypeOptions == {"pattern": "^[a-z0-9-]+$", "maxLength": 32}


def test_apply_preserves_author_set_fields_including_explicit_empty():
    # `description` is explicitly set to "" — model_fields_set marks it set,
    # so the definition must not overwrite it (a naive falsy check would).
    prop = SchemaProperty(name="Foo", logicalType="integer", description="")

    _apply_definition_to_property(prop, FULL_DEFINITION)

    assert prop.logicalType == "integer"
    assert prop.description == ""
    # Fields the author left unset are still filled.
    assert prop.businessName == "Foo Bar"


def test_apply_merges_logical_type_options_key_by_key():
    prop = SchemaProperty(name="Foo", logicalTypeOptions={"pattern": "^keep$"})

    _apply_definition_to_property(prop, FULL_DEFINITION)

    assert prop.logicalTypeOptions == {"pattern": "^keep$", "maxLength": 32}


def test_apply_maps_enum_to_quality_rule():
    prop = SchemaProperty(name="Foo")

    _apply_definition_to_property(prop, {"enum": ["A", "B"]})

    assert len(prop.quality) == 1
    rule = prop.quality[0]
    assert rule.metric == "invalidValues"
    assert rule.arguments == {"validValues": ["A", "B"]}
    assert rule.mustBe == 0


def test_apply_does_not_replace_author_quality():
    prop = SchemaProperty(name="Foo")
    prop.quality = []  # author touched `quality`
    _apply_definition_to_property(prop, {"enum": ["A", "B"]})
    assert prop.quality == []


def test_apply_maps_pii_precision_scale_to_custom_properties():
    prop = SchemaProperty(name="Foo")

    _apply_definition_to_property(prop, {"pii": True, "precision": 10, "scale": 2})

    by_name = {cp.property: cp.value for cp in prop.customProperties}
    assert by_name == {"pii": "True", "precision": "10", "scale": "2"}


# ---------------------------------------------------------------------------
# inline_definitions_into_data_contract -- end to end
# ---------------------------------------------------------------------------


def _contract(prop: SchemaProperty) -> OpenDataContractStandard:
    return OpenDataContractStandard(
        apiVersion="v3.1.0",
        kind="DataContract",
        id="c",
        name="c",
        version="1.0.0",
        status="active",
        schema=[SchemaObject(name="TBL", properties=[prop])],
    )


def test_inline_enriches_property_from_definition(tmp_path):
    url = _file_url(tmp_path)
    contract = _contract(
        SchemaProperty(name="Foo", authoritativeDefinitions=[AuthoritativeDefinition(type="definition", url=url)])
    )

    inline_definitions_into_data_contract(contract)

    foo = contract.schema_[0].properties[0]
    assert foo.logicalType == "string"
    assert foo.description == "A reusable Foo Bar concept."


def test_inline_recurses_into_nested_properties_and_items(tmp_path):
    ref = [AuthoritativeDefinition(type="definition", url=_file_url(tmp_path))]
    contract = OpenDataContractStandard(
        apiVersion="v3.1.0",
        kind="DataContract",
        id="c",
        name="c",
        version="1.0.0",
        status="active",
        schema=[
            SchemaObject(
                name="TBL",
                properties=[
                    SchemaProperty(
                        name="parent",
                        logicalType="object",
                        properties=[SchemaProperty(name="child", authoritativeDefinitions=ref)],
                    ),
                    SchemaProperty(
                        name="list",
                        logicalType="array",
                        items=SchemaProperty(name="item", authoritativeDefinitions=ref),
                    ),
                ],
            )
        ],
    )

    inline_definitions_into_data_contract(contract)

    assert contract.schema_[0].properties[0].properties[0].logicalType == "string"
    assert contract.schema_[0].properties[1].items.logicalType == "string"


def test_inline_skips_unresolvable_reference():
    # A broken reference must not fail the contract — the property is left as written.
    contract = _contract(
        SchemaProperty(
            name="Foo",
            authoritativeDefinitions=[
                AuthoritativeDefinition(type="definition", url="file:///missing/definition.yaml")
            ],
        )
    )
    inline_definitions_into_data_contract(contract)  # must not raise
    assert contract.schema_[0].properties[0].logicalType is None


def test_inline_ignores_semantics_references(tmp_path):
    # `type: semantics` is a separate concern — it must not be resolved here.
    contract = _contract(
        SchemaProperty(
            name="Foo", authoritativeDefinitions=[AuthoritativeDefinition(type="semantics", url=_file_url(tmp_path))]
        )
    )

    inline_definitions_into_data_contract(contract)

    assert contract.schema_[0].properties[0].logicalType is None


def test_inline_handles_contract_without_schema():
    contract = OpenDataContractStandard(
        apiVersion="v3.1.0", kind="DataContract", id="x", name="x", version="1.0.0", status="active"
    )
    inline_definitions_into_data_contract(contract)  # must not raise


# ---------------------------------------------------------------------------
# Integration: DataContract resolves definitions when it loads a contract
# ---------------------------------------------------------------------------


def test_data_contract_resolves_definition_on_load(tmp_path):
    definition_url = _file_url(tmp_path)
    contract_path = tmp_path / "contract.odcs.yaml"
    contract_path.write_text(
        "apiVersion: v3.1.0\n"
        "kind: DataContract\n"
        "id: definition-resolution-test\n"
        "name: Definition Resolution Test\n"
        "version: 1.0.0\n"
        "status: active\n"
        "schema:\n"
        "  - name: orders\n"
        "    properties:\n"
        "      - name: Foo\n"
        "        authoritativeDefinitions:\n"
        "          - type: definition\n"
        f"            url: {definition_url}\n"
    )

    resolved = DataContract(data_contract_file=str(contract_path)).get_data_contract()

    foo = resolved.schema_[0].properties[0]
    assert foo.logicalType == "string"
    assert foo.description == "A reusable Foo Bar concept."
