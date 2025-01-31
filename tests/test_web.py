from fastapi.testclient import TestClient

from datacontract.web import app

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
    assert len(response.json()["checks"]) == 8
    assert all([check["result"] == "passed" for check in response.json()["checks"]])


def test_export_jsonschema():
    with open("fixtures/local-json/datacontract.yaml", "r") as f:
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
