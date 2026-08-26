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

    def fake_post(url, json, headers, verify):  # noqa: A002 -- the requests keyword
        posted["body"] = json
        return _Response()

    monkeypatch.setattr("datacontract.integration.entropy_data.requests.post", fake_post)

    assert publish_test_results_to_entropy_data(run, "https://api.entropy-data.com/api/test-results", True)

    assert [check["type"] for check in posted["body"]["checks"]] == ["field_type"]
    # the run itself keeps every check, so the local report still shows what was skipped
    assert [check.type for check in run.checks] == ["field_type", "field_unique"]


def _publish_and_capture(monkeypatch, publish_url: str) -> dict:
    """Publish a minimal run to `publish_url` and return the headers it was sent with."""
    run = Run.create_run()
    run.dataContractId = "orders"
    sent = {}

    def fake_post(url, json, headers, verify):  # noqa: A002 -- the requests keyword
        sent.update(headers)
        return _Response()

    monkeypatch.setattr("datacontract.integration.entropy_data.requests.post", fake_post)
    assert publish_test_results_to_entropy_data(run, publish_url, True)
    return sent


def test_publish_does_not_send_the_api_key_to_a_foreign_host(monkeypatch):
    """`--publish` is arbitrary input, and a query parameter on the API server's
    /test endpoint, so a URL that is not the Entropy Data host must not receive
    the key the CLI holds for it."""
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    monkeypatch.delenv("ENTROPY_DATA_HOST", raising=False)

    assert "x-api-key" not in _publish_and_capture(monkeypatch, "https://attacker.example/api/test-results")


def test_publish_sends_the_api_key_to_the_platform(monkeypatch):
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")

    sent = _publish_and_capture(monkeypatch, "https://api.entropy-data.com/api/test-results")

    assert sent["x-api-key"] == "test-key"


def test_publish_sends_the_api_key_to_a_configured_self_hosted_deployment(monkeypatch):
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")
    monkeypatch.setenv("ENTROPY_DATA_HOST", "https://entropy.internal.example")

    sent = _publish_and_capture(monkeypatch, "https://entropy.internal.example/api/test-results")

    assert sent["x-api-key"] == "test-key"


def test_cli_shows_publish_failure_and_exits_1(monkeypatch):
    """A publish that was asked for and failed must be visible without --debug and fail the command."""
    from typer.testing import CliRunner

    from datacontract.cli import app

    for var in ("ENTROPY_DATA_HOST", "DATAMESH_MANAGER_HOST", "DATACONTRACT_MANAGER_HOST"):
        monkeypatch.delenv(var, raising=False)
    monkeypatch.setenv("ENTROPY_DATA_API_KEY", "test-key")

    class _Unauthorized:
        status_code = 401
        text = '{"error": "Unauthorized"}'
        headers = {}

    monkeypatch.setattr("datacontract.integration.entropy_data.requests.post", lambda *args, **kwargs: _Unauthorized())

    result = CliRunner().invoke(
        app,
        [
            "test",
            "fixtures/local-json/datacontract.yaml",
            "--publish",
            "https://dcm.mycompany.example/api/test-results",
        ],
    )
    assert result.exit_code == 1
    assert "Error publishing test results to dcm.mycompany.example" in result.output
    assert "Set ENTROPY_DATA_HOST" in result.output
