import os
from pathlib import Path
from unittest.mock import patch

from rich.console import Console
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.model.run import Check, ResultEnum, Run
from datacontract.output.junit_test_results import write_junit_test_results

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


def test_write_junit_handles_mkdir_file_exists_error(tmp_path):
    """Test that write_junit_test_results handles FileExistsError from mkdir.

    This covers the TOCTOU race condition in pathlib.Path.mkdir(exist_ok=True)
    documented in python/cpython#142916, where mkdir can raise FileExistsError
    even with exist_ok=True in concurrent environments like GitHub Actions.
    """
    run = Run.create_run()
    run.checks = [
        Check(type="schema", name="test_check", result=ResultEnum.passed),
    ]
    run.finish()

    output_path = tmp_path / "subdir" / "TEST-results.xml"
    console = Console()

    original_mkdir = Path.mkdir

    def mkdir_raising_file_exists(self, *args, **kwargs):
        # First call creates the directory normally
        original_mkdir(self, *args, **kwargs)
        # Then raise FileExistsError to simulate the TOCTOU race
        raise FileExistsError(f"Simulated TOCTOU race for {self}")

    with patch.object(Path, "mkdir", mkdir_raising_file_exists):
        write_junit_test_results(run, console, output_path)

    assert output_path.exists(), "JUnit file should be written despite FileExistsError from mkdir"
    content = output_path.read_text()
    assert "test_check" in content
