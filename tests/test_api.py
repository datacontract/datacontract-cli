from unittest.mock import patch

from fastapi.testclient import TestClient

from datacontract.api import app
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


def test_test_endpoint_uses_config_from_headers():
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


def _row_filter_contract():
    with open("fixtures/row-filter/datacontract.yaml", "r", encoding="utf-8") as f:
        return f.read()


def test_test_endpoint_filter_param():
    response = client.post(
        url="/test?filter=order_id <= 2",
        content=_row_filter_contract(),
        headers={"Content-Type": "application/yaml"},
    )

    assert response.status_code == 200
    assert response.json()["result"] == "passed"
    assert response.json()["filters"] == {"orders": "order_id <= 2"}


def test_test_endpoint_filters_param():
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
