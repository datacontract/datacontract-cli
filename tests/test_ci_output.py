import os
import tempfile
from unittest.mock import patch

from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.model.run import Check, ResultEnum, Run
from datacontract.output.ci_output import write_ci_output

runner = CliRunner()


def _make_run(checks):
    run = Run.create_run()
    run.checks = checks
    run.finish()
    return run


def test_github_annotations_emitted(capsys):
    run = _make_run(
        [
            Check(type="schema", name="Check col types", result=ResultEnum.failed, reason="type mismatch"),
            Check(type="schema", name="Check nullability", result=ResultEnum.warning, reason="nullable changed"),
            Check(type="schema", name="Check row count", result=ResultEnum.passed, reason=None),
        ]
    )
    with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
        write_ci_output(run, "datacontract.yaml")

    captured = capsys.readouterr()
    assert "::error file=datacontract.yaml::Check col types: type mismatch" in captured.out
    assert "::warning file=datacontract.yaml::Check nullability: nullable changed" in captured.out
    assert "Check row count" not in captured.out


def test_no_annotations_outside_github(capsys):
    run = _make_run(
        [
            Check(type="schema", name="Check col types", result=ResultEnum.failed, reason="type mismatch"),
        ]
    )
    env = {k: v for k, v in os.environ.items() if k != "GITHUB_ACTIONS"}
    with patch.dict(os.environ, env, clear=True):
        write_ci_output(run, "datacontract.yaml")

    captured = capsys.readouterr()
    assert "::error" not in captured.out


def test_annotation_format_for_errors(capsys):
    run = _make_run(
        [
            Check(type="quality", name="freshness", result=ResultEnum.error, reason="connection timeout"),
        ]
    )
    with patch.dict(os.environ, {"GITHUB_ACTIONS": "true"}):
        write_ci_output(run, "my/contract.yaml")

    captured = capsys.readouterr()
    assert captured.out.strip() == "::error file=my/contract.yaml::freshness: connection timeout"


def test_step_summary_written():
    run = _make_run(
        [
            Check(type="schema", name="Check types", result=ResultEnum.passed, reason=None),
            Check(type="schema", name="Check nulls", result=ResultEnum.failed, reason="not nullable"),
        ]
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        summary_path = f.name

    try:
        env = {k: v for k, v in os.environ.items() if k != "GITHUB_ACTIONS"}
        env["GITHUB_STEP_SUMMARY"] = summary_path
        with patch.dict(os.environ, env, clear=True):
            write_ci_output(run, "datacontract.yaml")

        with open(summary_path) as f:
            content = f.read()
        assert "## Data Contract CI: datacontract.yaml" in content
        assert "| Result | Check | Field | Details |" in content
        assert "Check types" in content
        assert "Check nulls" in content
    finally:
        os.unlink(summary_path)


def test_no_summary_without_env():
    run = _make_run(
        [
            Check(type="schema", name="Check types", result=ResultEnum.passed, reason=None),
        ]
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        summary_path = f.name

    try:
        env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_ACTIONS", "GITHUB_STEP_SUMMARY")}
        with patch.dict(os.environ, env, clear=True):
            write_ci_output(run, "datacontract.yaml")

        with open(summary_path) as f:
            content = f.read()
        assert content == ""
    finally:
        os.unlink(summary_path)


def test_step_summary_markdown_structure():
    run = _make_run(
        [
            Check(type="schema", name="Check types", model="orders", field="id", result=ResultEnum.passed, reason=None),
            Check(type="quality", name="Row count", model="orders", result=ResultEnum.failed, reason="0 rows"),
        ]
    )
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        summary_path = f.name

    try:
        env = {k: v for k, v in os.environ.items() if k != "GITHUB_ACTIONS"}
        env["GITHUB_STEP_SUMMARY"] = summary_path
        with patch.dict(os.environ, env, clear=True):
            write_ci_output(run, "datacontract.yaml")

        with open(summary_path) as f:
            content = f.read()
        assert "**Result: failed**" in content
        assert "2 checks" in content
        assert "1 passed" in content
        assert "1 failed" in content
    finally:
        os.unlink(summary_path)


def test_ci_help():
    result = runner.invoke(app, ["ci", "--help"])
    assert result.exit_code == 0
    assert "CI/CD" in result.stdout


def test_ci_with_valid_contract():
    result = runner.invoke(app, ["ci", "fixtures/lint/valid_datacontract.yaml"])
    assert result.exit_code == 0


def test_ci_with_missing_file():
    result = runner.invoke(app, ["ci", "nonexistent.yaml"])
    assert result.exit_code == 1
