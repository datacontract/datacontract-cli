from fastapi.testclient import TestClient

from datacontract.api import app

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
    assert "Invalid YAML" in response.json()["detail"]


def test_changelog_invalid_data_contract():
    invalid_contract = """
    apiVersion: '1.0'
    servers:
      - type: invalid_type
    """
    response = client.post(url="/changelog", json={"v1": invalid_contract, "v2": "valid: yaml"})
    assert response.status_code == 422
    assert "Invalid data contract" in response.json()["detail"]
