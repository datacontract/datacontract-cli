from fastapi.testclient import TestClient
from datacontract.web import app

client = TestClient(app)


def test_lint():
    with open("examples/lint/valid_datacontract.yaml", "rb") as f:
        response = client.post(url="/lint",
                               files={"file": ("datacontract.yaml", f, "application/yaml")})
        assert response.status_code == 200
        print(response.json())
        assert response.json()['result'] == 'passed'
        assert len(response.json()['checks']) == 7
        assert all([check['result'] == 'passed' for check in response.json()['checks']])
