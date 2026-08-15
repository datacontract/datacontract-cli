import json

from datacontract.integration.entropy_data import publish_test_results_to_entropy_data
from datacontract.model.run import Check, ResultEnum, Run


class _Response:
    status_code = 200
    text = ""
    headers = {}


def test_publish_omits_skipped_checks(monkeypatch):
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    run = Run.create_run()
    run.dataContractId = "orders"
    run.checks = [
        Check(type="field_type", name="Check that field order_id has type string", result=ResultEnum.passed),
        Check(
            type="field_unique",
            name="Check that field order_id is unique",
            result=ResultEnum.skipped,
            reason="Row-value check disabled by --metadata-only",
        ),
    ]

    posted = {}

    def fake_post(url, data, headers, verify):
        posted["body"] = json.loads(data)
        return _Response()

    monkeypatch.setattr("datacontract.integration.entropy_data.requests.post", fake_post)

    assert publish_test_results_to_entropy_data(run, "https://api.entropy-data.com/api/test-results", True)

    assert [check["type"] for check in posted["body"]["checks"]] == ["field_type"]
    # the run itself keeps every check, so the local report still shows what was skipped
    assert [check.type for check in run.checks] == ["field_type", "field_unique"]
