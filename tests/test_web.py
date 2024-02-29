from fastapi.testclient import TestClient
from datacontract.web import app

client = TestClient(app)


def test_lint():
    with open("examples/lint/valid_datacontract.yaml", "rb") as f:
        response = client.post(url="/lint",
                               files={"file": ("datacontract.yaml", f, "application/yaml")})
        assert response.status_code == 200
        assert response.json() == {
            "result": "passed",
            "checks": [
                {
                    "type": "lint",
                    "name": "Data contract is syntactically valid",
                    "result": "passed",
                    "engine": "datacontract",
                    "reason": None,
                    "model": None,
                    "field": None,
                    "details": None
                },
                {
                    "type": "lint",
                    "name": "Linter 'Example(s) match model'",
                    "result": "passed",
                    "engine": "datacontract",
                    "reason": None,
                    "model": None,
                    "field": None,
                    "details": None
                }
            ]
        }
