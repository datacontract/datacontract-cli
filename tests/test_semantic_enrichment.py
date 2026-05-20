"""Tests for resolving and applying semantic concepts to ODCS properties."""

from unittest.mock import MagicMock, patch

import pytest
from open_data_contract_standard.model import (
    AuthoritativeDefinition,
    OpenDataContractStandard,
    SchemaObject,
    SchemaProperty,
    Server,
)

from datacontract.engines.data_contract_checks import create_checks
from datacontract.integration.entropy_data import (
    _looks_like_entropy_data_host,
    _semantic_url_to_api,
    clear_semantic_cache,
    resolve_semantic_definition,
)
from datacontract.integration.semantic_enrichment import enrich_in_place

SEMANTIC_URL = "https://demo.entropy-data.com/org42/semantics/main/product.brand"
EXPECTED_API_URL = "https://demo.entropy-data.com/api/semantics/experimental/namespaces/main/concepts/product.brand"
SAMPLE_CONCEPT = {
    "id": "product.brand",
    "name": "brand",
    "kind": "property",
    "data_type": "string",
    "description": "Brand the product belongs to.",
    "business_name": "brand",
    "examples": ["EcoWear"],
}


@pytest.fixture(autouse=True)
def _clear_cache():
    clear_semantic_cache()
    yield
    clear_semantic_cache()


@pytest.fixture
def env_with_api_key(monkeypatch):
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "ed_test_key_abcdef")
    monkeypatch.delenv("ENTROPY_DATA_HOST", raising=False)
    monkeypatch.delenv("DATAMESH_MANAGER_HOST", raising=False)
    monkeypatch.delenv("DATACONTRACT_MANAGER_HOST", raising=False)
    return "ed_test_key_abcdef"


@pytest.fixture
def env_without_api_key(monkeypatch):
    monkeypatch.delenv("ENTROPY_DATA_API_KEY", raising=False)
    monkeypatch.delenv("DATAMESH_MANAGER_API_KEY", raising=False)
    monkeypatch.delenv("DATACONTRACT_MANAGER_API_KEY", raising=False)
    monkeypatch.delenv("ENTROPY_DATA_HOST", raising=False)
    monkeypatch.delenv("DATAMESH_MANAGER_HOST", raising=False)
    monkeypatch.delenv("DATACONTRACT_MANAGER_HOST", raising=False)


# ---------------------------------------------------------------------------
# URL translation
# ---------------------------------------------------------------------------


def test_semantic_url_to_api_translates_known_shape():
    assert _semantic_url_to_api(SEMANTIC_URL) == EXPECTED_API_URL


def test_semantic_url_to_api_strips_query_and_fragment():
    assert _semantic_url_to_api(SEMANTIC_URL + "?v=1#anchor") == EXPECTED_API_URL


@pytest.mark.parametrize(
    "url",
    [
        "",
        "not a url",
        "ftp://demo.entropy-data.com/org42/semantics/main/product.brand",
        "https://demo.entropy-data.com/missing-semantics-segment/main/product.brand",
        "https://demo.entropy-data.com/org42/semantics/main",  # missing externalId
    ],
)
def test_semantic_url_to_api_rejects_unknown_shape(url):
    assert _semantic_url_to_api(url) is None


# ---------------------------------------------------------------------------
# Host trust policy
# ---------------------------------------------------------------------------


def test_known_entropy_data_hosts_are_trusted(env_without_api_key):
    assert _looks_like_entropy_data_host("entropy-data.com")
    assert _looks_like_entropy_data_host("demo.entropy-data.com")
    assert _looks_like_entropy_data_host("api.entropy-data.com")


def test_arbitrary_host_is_not_trusted(env_without_api_key):
    assert not _looks_like_entropy_data_host("example.com")
    assert not _looks_like_entropy_data_host("evil.example.com")


def test_configured_host_is_trusted(monkeypatch):
    monkeypatch.setenv("ENTROPY_DATA_HOST", "https://datacontract.acme.internal:8443")
    assert _looks_like_entropy_data_host("datacontract.acme.internal")
    assert not _looks_like_entropy_data_host("other.acme.internal")


# ---------------------------------------------------------------------------
# resolve_semantic_definition
# ---------------------------------------------------------------------------


def _ok(json_body):
    response = MagicMock()
    response.status_code = 200
    response.json.return_value = json_body
    return response


@patch("datacontract.integration.entropy_data.requests.get")
def test_resolve_returns_concept_and_sends_api_key_for_entropy_host(mock_get, env_with_api_key):
    mock_get.return_value = _ok(SAMPLE_CONCEPT)

    concept = resolve_semantic_definition(SEMANTIC_URL)

    assert concept == SAMPLE_CONCEPT
    mock_get.assert_called_once()
    called_url, called_kwargs = mock_get.call_args.args[0], mock_get.call_args.kwargs
    assert called_url == EXPECTED_API_URL
    assert called_kwargs["headers"]["x-api-key"] == env_with_api_key
    assert called_kwargs["headers"]["Accept"] == "application/json"


@patch("datacontract.integration.entropy_data.requests.get")
def test_resolve_does_not_send_api_key_to_untrusted_hosts(mock_get, env_with_api_key):
    mock_get.return_value = _ok(SAMPLE_CONCEPT)
    foreign_url = "https://semantics.example.com/org/semantics/main/x"

    resolve_semantic_definition(foreign_url)

    headers = mock_get.call_args.kwargs["headers"]
    assert "x-api-key" not in headers
    assert headers["Accept"] == "application/json"


@patch("datacontract.integration.entropy_data.requests.get")
def test_resolve_caches_results_per_url(mock_get, env_with_api_key):
    mock_get.return_value = _ok(SAMPLE_CONCEPT)

    resolve_semantic_definition(SEMANTIC_URL)
    resolve_semantic_definition(SEMANTIC_URL)
    resolve_semantic_definition(SEMANTIC_URL)

    assert mock_get.call_count == 1


@patch("datacontract.integration.entropy_data.requests.get")
def test_resolve_caches_negative_results(mock_get, env_with_api_key):
    response = MagicMock()
    response.status_code = 404
    response.text = "not found"
    mock_get.return_value = response

    assert resolve_semantic_definition(SEMANTIC_URL) is None
    assert resolve_semantic_definition(SEMANTIC_URL) is None
    assert mock_get.call_count == 1


@patch("datacontract.integration.entropy_data.requests.get")
def test_resolve_returns_none_on_network_error(mock_get, env_with_api_key):
    import requests as _requests

    mock_get.side_effect = _requests.ConnectionError("boom")

    assert resolve_semantic_definition(SEMANTIC_URL) is None


@patch("datacontract.integration.entropy_data.requests.get")
def test_resolve_returns_none_for_unknown_url_shape_without_calling_http(mock_get, env_with_api_key):
    assert resolve_semantic_definition("not a url") is None
    mock_get.assert_not_called()


# ---------------------------------------------------------------------------
# enrich_in_place — property-level merge
# ---------------------------------------------------------------------------


def _contract_with_semantic_brand():
    return OpenDataContractStandard(
        apiVersion="v3.1.0",
        kind="DataContract",
        id="orders-contract",
        name="Orders",
        version="1.0.0",
        status="active",
        schema=[
            SchemaObject(
                name="ORDERS",
                physicalType="table",
                properties=[
                    SchemaProperty(name="ORDER_ID", logicalType="string", required=True, primaryKey=True),
                    # Bare semantic-only property — what the editor's
                    # "Add from definition" produces today.
                    SchemaProperty(
                        name="brand",
                        physicalName="BRAND",
                        authoritativeDefinitions=[AuthoritativeDefinition(type="semantics", url=SEMANTIC_URL)],
                    ),
                ],
            )
        ],
    )


@patch("datacontract.integration.entropy_data.requests.get")
def test_enrich_fills_missing_fields_from_concept(mock_get, env_with_api_key):
    mock_get.return_value = _ok(SAMPLE_CONCEPT)
    contract = _contract_with_semantic_brand()
    brand = contract.schema_[0].properties[1]
    assert brand.logicalType is None and brand.description is None

    enrich_in_place(contract)

    assert brand.logicalType == "string"
    assert brand.description == "Brand the product belongs to."
    assert brand.examples == ["EcoWear"]
    assert brand.businessName == "brand"
    # Already-set fields are untouched.
    assert brand.physicalName == "BRAND"


@patch("datacontract.integration.entropy_data.requests.get")
def test_enrich_does_not_overwrite_inline_fields(mock_get, env_with_api_key):
    mock_get.return_value = _ok({**SAMPLE_CONCEPT, "data_type": "number"})
    contract = _contract_with_semantic_brand()
    brand = contract.schema_[0].properties[1]
    brand.logicalType = "string"  # set inline by author — concept must not override

    enrich_in_place(contract)

    assert brand.logicalType == "string"


@patch("datacontract.integration.entropy_data.requests.get")
def test_enrich_is_a_noop_without_semantic_ref(mock_get, env_with_api_key):
    contract = _contract_with_semantic_brand()
    contract.schema_[0].properties[1].authoritativeDefinitions = []

    enrich_in_place(contract)

    mock_get.assert_not_called()


def test_enrich_handles_contract_without_schema(env_without_api_key):
    contract = OpenDataContractStandard(
        apiVersion="v3.1.0",
        kind="DataContract",
        id="x",
        name="x",
        version="1.0.0",
        status="active",
    )
    # Should not raise.
    enrich_in_place(contract)


# ---------------------------------------------------------------------------
# End-to-end: create_checks now emits a type check for the brand property
# ---------------------------------------------------------------------------


@patch("datacontract.integration.entropy_data.requests.get")
def test_create_checks_emits_type_check_after_enrichment(mock_get, env_with_api_key):
    mock_get.return_value = _ok(SAMPLE_CONCEPT)
    contract = _contract_with_semantic_brand()

    checks = create_checks(contract, Server(type="snowflake"))

    # Presence + type check now exist for BRAND (the physicalName), where
    # previously the type check was silently skipped because the property
    # had no inline logicalType/physicalType.
    fields = {(c.type, c.field) for c in checks}
    assert ("field_is_present", "BRAND") in fields
    assert ("field_type", "BRAND") in fields


@patch("datacontract.integration.entropy_data.requests.get")
def test_ssl_verification_default_true_propagates_to_http_call(mock_get, env_with_api_key):
    mock_get.return_value = _ok(SAMPLE_CONCEPT)
    contract = _contract_with_semantic_brand()

    create_checks(contract, Server(type="snowflake"))

    assert mock_get.call_args.kwargs["verify"] is True


@patch("datacontract.integration.entropy_data.requests.get")
def test_ssl_verification_false_propagates_through_create_checks(mock_get, env_with_api_key):
    """A self-hosted deployment with a self-signed certificate can pass
    --no-ssl-verification to `datacontract test`; the same value must
    reach the resolver's HTTP call so the concept can actually be
    fetched and used to enrich the contract."""
    mock_get.return_value = _ok(SAMPLE_CONCEPT)
    contract = _contract_with_semantic_brand()

    create_checks(contract, Server(type="snowflake"), ssl_verification=False)

    assert mock_get.call_args.kwargs["verify"] is False
