import os

from typer.testing import CliRunner

from datacontract.cli import app

runner = CliRunner()


def test_output_junit_test_result(tmp_path):
    runner.invoke(
        app,
        [
            "test",
            "--output",
            tmp_path / "TEST-datacontract.xml",
            "--output-format",
            "junit",
            "./fixtures/junit/datacontract.yaml",
        ],
    )
    assert os.path.exists(tmp_path / "TEST-datacontract.xml"), "Should write a JUnit test result file"
