"""Tests for resolving `authoritativeDefinitions[type=definition]` references
against the configured entropy-data host.

The contract under test: the resolver fetches the referenced ODCS property
from entropy-data, inlines its fields where the contract author left them
unset, never silently swallows a failure, and never leaks the API key to a
third-party host.
"""

import json

import pytest
import responses
from open_data_contract_standard.model import (
    AuthoritativeDefinition,
    OpenDataContractStandard,
    SchemaObject,
    SchemaProperty,
)

from datacontract.lint.resolve import (
    clear_definition_cache,
    inline_definitions_into_data_contract,
)
from datacontract.model.exceptions import DataContractException

_HOST = "https://api.entropy-data.com"
_API_KEY = "test-key"


@pytest.fixture(autouse=True)
def _isolated_cache():
    """The resolver caches by URL across the process; clear it before each test
    so cases that reuse URLs don't see each other."""
    clear_definition_cache()
    yield
    clear_definition_cache()


@pytest.fixture
def env(monkeypatch):
    """Set the env vars the resolver looks at. Tests that need to vary these
    override individual vars on top of this fixture."""
    monkeypatch.setenv("ENTROPY_DATA_HOST", _HOST)
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", _API_KEY)
    monkeypatch.delenv("DATAMESH_MANAGER_HOST", raising=False)
    monkeypatch.delenv("DATAMESH_MANAGER_API_KEY", raising=False)
    monkeypatch.delenv("DATACONTRACT_MANAGER_HOST", raising=False)
    monkeypatch.delenv("DATACONTRACT_MANAGER_API_KEY", raising=False)


def _definition_body(**fields) -> bytes:
    """A definition-response body. The server sends a SchemaProperty-shaped
    JSON document; `name`/`url` are present but ignored by the resolver."""
    body = {"name": "fulfillment/shipment_id", "url": "/demo/definitions/fulfillment/shipment_id"}
    body.update(fields)
    return json.dumps(body).encode()


def _contract(*properties: SchemaProperty) -> OpenDataContractStandard:
    return OpenDataContractStandard(
        apiVersion="v3.0.2",
        kind="DataContract",
        id="test",
        version="1.0.0",
        status="draft",
        schema=[SchemaObject(name="t", properties=list(properties))],
    )


def _prop_referencing(url: str, **inline) -> SchemaProperty:
    return SchemaProperty(
        name=inline.pop("name", "shipment_id"),
        authoritativeDefinitions=[AuthoritativeDefinition(type="definition", url=url)],
        **inline,
    )


# --- URL shapes & API-key scoping ----------------------------------------


@responses.activate
def test_relative_url_is_joined_to_configured_host_with_api_key(env):
    """A relative `url:` (the shape entropy-data writes) is joined onto
    ENTROPY_DATA_HOST and the API key is sent."""
    responses.add(
        responses.GET,
        f"{_HOST}/demo/definitions/fulfillment/shipment_id",
        body=_definition_body(logicalType="string", description="Unique shipment id"),
        status=200,
    )

    prop = _prop_referencing("/demo/definitions/fulfillment/shipment_id")
    inline_definitions_into_data_contract(_contract(prop))

    assert prop.logicalType == "string"
    assert prop.description == "Unique shipment id"
    assert responses.calls[0].request.headers["x-api-key"] == _API_KEY


@responses.activate
def test_absolute_url_matching_host_sends_api_key(env):
    """An absolute URL whose host matches ENTROPY_DATA_HOST still gets the
    API key -- the rule is host-based, not relative-path-based."""
    responses.add(
        responses.GET,
        f"{_HOST}/demo/definitions/foo",
        body=_definition_body(logicalType="string"),
        status=200,
    )

    prop = _prop_referencing(f"{_HOST}/demo/definitions/foo")
    inline_definitions_into_data_contract(_contract(prop))

    assert responses.calls[0].request.headers.get("x-api-key") == _API_KEY


@responses.activate
def test_absolute_url_other_host_does_not_send_api_key(env):
    """A URL pointing at a host other than the configured one is fetched
    anonymously; the user's key must never leak to a third party."""
    other_host_url = "https://datamesh-manager-demo.azurecontainerapps.io/x/definitions/y"
    responses.add(
        responses.GET,
        other_host_url,
        body=_definition_body(logicalType="string"),
        status=200,
    )

    prop = _prop_referencing(other_host_url)
    inline_definitions_into_data_contract(_contract(prop))

    assert "x-api-key" not in responses.calls[0].request.headers


@responses.activate
def test_other_host_rejecting_anonymous_request_raises(env):
    """The typical consequence of fetching a foreign host anonymously is a
    401 -- which must surface as a contract error, not a silent skip."""
    other_host_url = "https://datamesh-manager-demo.azurecontainerapps.io/x/definitions/y"
    responses.add(responses.GET, other_host_url, status=401)

    prop = _prop_referencing(other_host_url)

    with pytest.raises(DataContractException) as exc:
        inline_definitions_into_data_contract(_contract(prop))
    assert "401" in str(exc.value)


@responses.activate
def test_relative_url_without_api_key_set_is_fetched_anonymously(env, monkeypatch):
    """The API key is optional: if none is configured, the resolver still
    tries -- the server then decides whether to accept the request."""
    monkeypatch.delenv("ENTROPY_DATA_API_KEY", raising=False)
    responses.add(
        responses.GET,
        f"{_HOST}/demo/definitions/foo",
        body=_definition_body(logicalType="string"),
        status=200,
    )

    prop = _prop_referencing("/demo/definitions/foo")
    inline_definitions_into_data_contract(_contract(prop))

    assert "x-api-key" not in responses.calls[0].request.headers
    assert prop.logicalType == "string"


# --- Field merging -------------------------------------------------------


@responses.activate
def test_author_inline_values_win_over_definition(env):
    """The contract author owns the final shape: a field the author wrote
    is never replaced by the definition's value, even when the author's
    value is 'less informative' (an empty string, here)."""
    responses.add(
        responses.GET,
        f"{_HOST}/d",
        body=_definition_body(logicalType="integer", description="From definition"),
        status=200,
    )

    prop = _prop_referencing(
        "/d",
        logicalType="string",  # author set
        description="",  # author set, empty
    )
    inline_definitions_into_data_contract(_contract(prop))

    assert prop.logicalType == "string"
    assert prop.description == ""


@responses.activate
def test_unset_fields_are_filled_from_definition(env):
    """Every ODCS SchemaProperty field the author left unset is taken from
    the definition's response."""
    responses.add(
        responses.GET,
        f"{_HOST}/d",
        body=_definition_body(
            logicalType="string",
            description="A description",
            classification="internal",
            tags=["pii"],
            examples=["abc"],
            physicalType="text",
        ),
        status=200,
    )

    prop = _prop_referencing("/d")
    inline_definitions_into_data_contract(_contract(prop))

    assert prop.logicalType == "string"
    assert prop.description == "A description"
    assert prop.classification == "internal"
    assert prop.tags == ["pii"]
    assert prop.examples == ["abc"]
    assert prop.physicalType == "text"


@responses.activate
def test_property_identity_fields_are_never_overwritten(env):
    """`name` identifies the property in its containing schema, and
    `authoritativeDefinitions` is the link itself; both must survive
    resolution unchanged even when the response carries them."""
    responses.add(
        responses.GET,
        f"{_HOST}/d",
        body=_definition_body(
            name="definition_side_name",
            authoritativeDefinitions=[{"type": "other", "url": "/other"}],
            logicalType="string",
        ),
        status=200,
    )

    original_links = [AuthoritativeDefinition(type="definition", url="/d")]
    prop = SchemaProperty(name="shipment_id", authoritativeDefinitions=original_links)
    inline_definitions_into_data_contract(_contract(prop))

    assert prop.name == "shipment_id"
    assert [(ad.type, ad.url) for ad in prop.authoritativeDefinitions] == [("definition", "/d")]
    assert prop.logicalType == "string"


# --- Recursion: nested properties and array items -----------------------


@responses.activate
def test_nested_property_is_resolved(env):
    """A definition reference on a nested property resolves the same way as
    on a top-level one."""
    responses.add(
        responses.GET,
        f"{_HOST}/nested",
        body=_definition_body(logicalType="string"),
        status=200,
    )

    nested = _prop_referencing("/nested", name="city")
    parent = SchemaProperty(name="address", properties=[nested])
    inline_definitions_into_data_contract(_contract(parent))

    assert nested.logicalType == "string"


@responses.activate
def test_array_item_is_resolved(env):
    """An array property's `items` shape can itself reference a definition."""
    responses.add(
        responses.GET,
        f"{_HOST}/item",
        body=_definition_body(logicalType="string"),
        status=200,
    )

    item = _prop_referencing("/item", name="tag")
    arr = SchemaProperty(name="tags", logicalType="array", items=item)
    inline_definitions_into_data_contract(_contract(arr))

    assert item.logicalType == "string"


# --- Type filter & cache --------------------------------------------------


@responses.activate
def test_non_definition_authoritative_type_is_ignored(env):
    """Only `type: definition` triggers resolution; other ODCS types --
    `businessDefinition`, `documentation`, etc. -- are informational links
    only and must not cause an HTTP request."""
    prop = SchemaProperty(
        name="shipment_id",
        authoritativeDefinitions=[AuthoritativeDefinition(type="businessDefinition", url=f"{_HOST}/anything")],
    )

    inline_definitions_into_data_contract(_contract(prop))

    assert len(responses.calls) == 0
    assert prop.logicalType is None


@responses.activate
def test_shared_definition_is_fetched_once(env):
    """When many properties reference the same definition, it is fetched
    once and reused -- a common entropy-data pattern (one canonical
    customer-id definition referenced from every contract)."""
    responses.add(
        responses.GET,
        f"{_HOST}/shared",
        body=_definition_body(logicalType="string"),
        status=200,
    )

    prop_a = _prop_referencing("/shared", name="a")
    prop_b = _prop_referencing("/shared", name="b")
    inline_definitions_into_data_contract(_contract(prop_a, prop_b))

    assert len(responses.calls) == 1
    assert prop_a.logicalType == "string"
    assert prop_b.logicalType == "string"


@responses.activate
def test_failed_resolution_is_not_cached(env):
    """A transient failure must not poison later runs: the second attempt
    refetches and succeeds."""
    responses.add(responses.GET, f"{_HOST}/flaky", status=500)
    responses.add(
        responses.GET,
        f"{_HOST}/flaky",
        body=_definition_body(logicalType="string"),
        status=200,
    )

    failing_prop = _prop_referencing("/flaky", name="a")
    with pytest.raises(DataContractException):
        inline_definitions_into_data_contract(_contract(failing_prop))

    retried_prop = _prop_referencing("/flaky", name="b")
    inline_definitions_into_data_contract(_contract(retried_prop))
    assert retried_prop.logicalType == "string"


# --- Failure modes -------------------------------------------------------


@responses.activate
def test_404_raises(env):
    responses.add(responses.GET, f"{_HOST}/missing", status=404)

    prop = _prop_referencing("/missing")
    with pytest.raises(DataContractException) as exc:
        inline_definitions_into_data_contract(_contract(prop))
    assert "404" in str(exc.value)
    assert "/missing" in str(exc.value)


@responses.activate
def test_network_error_raises(env):
    """Any request-level error (DNS, connection refused, timeout) surfaces
    as a contract error -- `responses` raises `ConnectionError` for any
    URL that wasn't registered."""
    prop = _prop_referencing("/unreachable")

    with pytest.raises(DataContractException):
        inline_definitions_into_data_contract(_contract(prop))


@responses.activate
def test_malformed_body_raises(env):
    """A 200 response whose body is not a valid ODCS property is treated
    as a server bug, not silently ignored."""
    responses.add(responses.GET, f"{_HOST}/bad", body=b"not json", status=200)

    prop = _prop_referencing("/bad")
    with pytest.raises(DataContractException) as exc:
        inline_definitions_into_data_contract(_contract(prop))
    assert "/bad" in str(exc.value)


# --- Semantics ------------------------------------------------------------
#
# `authoritativeDefinitions[type=semantics].url` resolves via the same path
# as `type=definition` when the URL points at the configured entropy-data
# host (REST URL). When the URL's host differs, it's treated as an IRI and
# routed through `/api/semantics?iri=...` instead.


def _semantics_prop(url: str, type_: str = "semantics", **inline) -> SchemaProperty:
    return SchemaProperty(
        name=inline.pop("name", "brand"),
        authoritativeDefinitions=[AuthoritativeDefinition(type=type_, url=url)],
        **inline,
    )


@responses.activate
def test_semantics_rest_url_resolves_against_configured_host(env):
    responses.add(
        responses.GET,
        f"{_HOST}/demo/semantics/main/product.brand",
        body=_definition_body(logicalType="string", businessName="brand"),
        status=200,
    )

    prop = _semantics_prop("/demo/semantics/main/product.brand")
    inline_definitions_into_data_contract(_contract(prop))

    assert prop.logicalType == "string"
    assert prop.businessName == "brand"
    assert responses.calls[0].request.headers["x-api-key"] == _API_KEY


@responses.activate
def test_semantics_iri_routes_through_api_semantics_lookup(env):
    """An IRI is not directly fetchable; the resolver translates it to the
    `/api/semantics?iri=...` lookup endpoint on the configured host."""
    iri = "http://www.entropy-data.com/ns/main/Article"
    responses.add(
        responses.GET,
        f"{_HOST}/api/semantics",
        body=_definition_body(logicalType="string", businessName="Article"),
        status=200,
    )

    prop = _semantics_prop(iri)
    inline_definitions_into_data_contract(_contract(prop))

    assert prop.logicalType == "string"
    assert prop.businessName == "Article"
    # The request must hit the configured host's lookup endpoint, NOT the
    # IRI's host -- the latter doesn't serve this content.
    call = responses.calls[0]
    assert call.request.url.startswith(f"{_HOST}/api/semantics")
    assert "iri=http" in call.request.url
    assert call.request.headers["x-api-key"] == _API_KEY


@responses.activate
def test_semantics_iri_without_api_key_raises(env, monkeypatch):
    """Resolving an IRI requires an API key; the lookup endpoint is API-key only."""
    monkeypatch.delenv("ENTROPY_DATA_API_KEY", raising=False)
    iri = "http://www.entropy-data.com/ns/main/Article"

    prop = _semantics_prop(iri)
    with pytest.raises(DataContractException) as exc:
        inline_definitions_into_data_contract(_contract(prop))
    msg = str(exc.value)
    assert "API key" in msg
    # The host mismatch is the likely root cause, so the fix is named explicitly.
    assert "ENTROPY_DATA_HOST=http://www.entropy-data.com" in msg
    assert len(responses.calls) == 0


@responses.activate
def test_semantics_iri_403_suggests_setting_host(env):
    """A 403 from the lookup usually means the configured host is the wrong
    deployment for this IRI; the error must name the ENTROPY_DATA_HOST fix
    instead of leaving the user to suspect their API key."""
    iri = "http://www.entropy-data.com/ns/main/Article"
    responses.add(responses.GET, f"{_HOST}/api/semantics", status=403)

    prop = _semantics_prop(iri)
    with pytest.raises(DataContractException) as exc:
        inline_definitions_into_data_contract(_contract(prop))
    msg = str(exc.value)
    assert "HTTP 403" in msg
    assert "ENTROPY_DATA_HOST=http://www.entropy-data.com" in msg


@responses.activate
def test_semantics_legacy_singular_type_is_resolved(env):
    """Contracts written before the entropy-data type migration from
    `"semantic"` to `"semantics"` still resolve."""
    responses.add(
        responses.GET,
        f"{_HOST}/demo/semantics/main/x",
        body=_definition_body(logicalType="string"),
        status=200,
    )

    prop = _semantics_prop("/demo/semantics/main/x", type_="semantic")
    inline_definitions_into_data_contract(_contract(prop))

    assert prop.logicalType == "string"


@responses.activate
def test_semantics_wins_over_definition_when_both_present(env):
    """Matches the editor's `useInheritedDefinition` convention: a property
    that links to both a semantic concept and a definition resolves through
    the semantic concept; only that one is fetched."""
    responses.add(
        responses.GET,
        f"{_HOST}/sem",
        body=_definition_body(logicalType="string", businessName="from-semantics"),
        status=200,
    )
    # Definition URL not registered -- if the resolver picks it, the test
    # fails with ConnectionError.

    prop = SchemaProperty(
        name="brand",
        authoritativeDefinitions=[
            AuthoritativeDefinition(type="definition", url="/def"),
            AuthoritativeDefinition(type="semantics", url="/sem"),
        ],
    )
    inline_definitions_into_data_contract(_contract(prop))

    assert prop.businessName == "from-semantics"
    assert len(responses.calls) == 1


# --- CLI integration: --no-inline-references -----------------------------


@responses.activate
def test_cli_no_inline_references_skips_resolution(env, tmp_path):
    """`datacontract lint --no-inline-references` must not make any HTTP
    request, even when the contract contains a definition reference that
    would otherwise be resolved (and fail, since no responder is registered)."""
    from typer.testing import CliRunner

    from datacontract.cli import app

    contract_path = tmp_path / "contract.odcs.yaml"
    contract_path.write_text(
        "apiVersion: v3.0.2\n"
        "kind: DataContract\n"
        "id: cli-skip-test\n"
        "version: 1.0.0\n"
        "status: draft\n"
        "schema:\n"
        "  - name: t\n"
        "    properties:\n"
        "      - name: shipment_id\n"
        "        authoritativeDefinitions:\n"
        "          - type: definition\n"
        "            url: /demo/definitions/missing\n"
    )

    result = CliRunner().invoke(app, ["lint", str(contract_path), "--no-inline-references"])

    assert result.exit_code == 0, result.stdout
    assert len(responses.calls) == 0
