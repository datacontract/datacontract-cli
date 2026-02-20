import json
import os

from typer.testing import CliRunner

from datacontract.cli import app

runner = CliRunner()


def test_output_json_test_result(tmp_path):
    runner.invoke(
        app,
        [
            "test",
            "--output",
            str(tmp_path / "test-results.json"),
            "--output-format",
            "json",
            "./fixtures/junit/datacontract.yaml",
        ],
    )
    output_file = tmp_path / "test-results.json"
    assert os.path.exists(output_file), "Should write a JSON test result file"
    with open(output_file) as f:
        data = json.load(f)
    assert "runId" in data
    assert "checks" in data
    assert "result" in data
    assert data["result"] in ("passed", "warning", "failed", "error")
