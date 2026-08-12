"""The OpenAPI document the API serves.

It is the only description of the API that clients and code generators see, so
the metadata that makes it usable — a real version, documented parameters,
typed responses, and the security scheme on every endpoint — is asserted here.
"""

from importlib import metadata

import pytest
from openapi_spec_validator import validate

from datacontract.api import app

PATHS = ["/test", "/lint", "/export", "/changelog"]


@pytest.fixture(scope="module")
def openapi() -> dict:
    return app.openapi()


def test_the_document_is_a_valid_openapi_31_document(openapi):
    validate(openapi)


def test_the_version_is_the_cli_version(openapi):
    """Not FastAPI's 0.1.0 placeholder, so a client can tell which CLI answers."""
    assert openapi["info"]["version"] == metadata.version("datacontract-cli")


def test_the_info_block_is_complete(openapi):
    info = openapi["info"]

    assert info["title"] and info["summary"] and info["description"]
    assert info["contact"]["url"] and info["license"]["name"]
    assert openapi["externalDocs"]["url"]


def test_the_server_is_relative_so_the_document_works_for_any_deployment(openapi):
    assert [server["url"] for server in openapi["servers"]] == ["/"]


def test_every_tag_is_declared_with_a_description(openapi):
    declared = {tag["name"]: tag for tag in openapi["tags"]}
    used = {tag for path in PATHS for tag in openapi["paths"][path]["post"]["tags"]}

    assert used <= declared.keys()
    for tag in declared.values():
        assert tag["description"]
        assert tag["externalDocs"]["url"]


def test_every_operation_has_a_readable_operation_id(openapi):
    """Code generators name their client methods after it, so not `lint_lint_post`."""
    operation_ids = {path: openapi["paths"][path]["post"]["operationId"] for path in PATHS}

    assert operation_ids == {
        "/test": "testDataContract",
        "/lint": "lintDataContract",
        "/export": "exportDataContract",
        "/changelog": "changelogBetweenDataContracts",
    }


def test_every_operation_is_documented(openapi):
    for path in PATHS:
        operation = openapi["paths"][path]["post"]
        assert operation["summary"], path
        assert operation["description"], path
        assert operation["responses"]["200"]["description"] != "Successful Response", path


def test_every_query_parameter_is_documented(openapi):
    for path in PATHS:
        for parameter in openapi["paths"][path]["post"].get("parameters", []):
            assert parameter.get("description"), f"{path} {parameter['name']}"


def test_every_endpoint_declares_the_api_key_security_scheme(openapi):
    """The API key protects all of them, so the document has to say so for all of them."""
    for path in PATHS:
        assert openapi["paths"][path]["post"]["security"] == [{"APIKeyHeader": []}], path

    assert openapi["components"]["securitySchemes"]["APIKeyHeader"]["description"]


def test_every_endpoint_documents_its_authentication_errors(openapi):
    for path in PATHS:
        responses = openapi["paths"][path]["post"]["responses"]
        for status_code in ("401", "403", "422"):
            assert status_code in responses, f"{path} {status_code}"
            assert responses[status_code]["description"], f"{path} {status_code}"


def test_errors_are_documented_as_json_even_where_the_success_body_is_not(openapi):
    """/export answers text/plain, but its error bodies are still JSON."""
    responses = openapi["paths"]["/export"]["post"]["responses"]

    assert set(responses["200"]["content"]) == {"text/plain"}
    for status_code in ("401", "403", "422"):
        assert set(responses[status_code]["content"]) == {"application/json"}


def test_the_success_responses_are_typed(openapi):
    """An untyped `{}` schema tells a client nothing about what it gets back."""
    schemas = {
        "/test": "#/components/schemas/Run",
        "/lint": "#/components/schemas/LintResponse",
        "/changelog": "#/components/schemas/ChangelogResponse",
    }

    for path, ref in schemas.items():
        content = openapi["paths"][path]["post"]["responses"]["200"]["content"]
        assert content["application/json"]["schema"] == {"$ref": ref}, path


def test_the_response_models_describe_their_fields(openapi):
    for name in ("Run", "Check", "Log", "LintResponse", "ChangelogResponse", "ChangelogEntry"):
        schema = openapi["components"]["schemas"][name]
        assert schema["description"], name
        undocumented = [field for field, spec in schema["properties"].items() if not spec.get("description")]
        assert not undocumented, f"{name}: {undocumented}"
