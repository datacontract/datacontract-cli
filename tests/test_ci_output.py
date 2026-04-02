import json
import os
import tempfile
from unittest.mock import patch

from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.model.run import Check, ResultEnum, Run
from datacontract.output.ci_output import (
    _sanitize_annotation,
    _sanitize_md_cell,
    write_ci_output,
    write_ci_summary,
    write_json_results,
)

runner = CliRunner()


def _make_run(checks):
    run = Run.create_run()
    run.checks = checks
    run.finish()
    return run


# --- Annotation tests ---


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


def test_no_annotations_outside_ci(capsys):
    run = _make_run(
        [
            Check(type="schema", name="Check col types", result=ResultEnum.failed, reason="type mismatch"),
        ]
    )
    env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_ACTIONS", "TF_BUILD")}
    with patch.dict(os.environ, env, clear=True):
        write_ci_output(run, "datacontract.yaml")

    captured = capsys.readouterr()
    assert "::error" not in captured.out
    assert "##vso" not in captured.out


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


def test_azure_annotations_emitted(capsys):
    run = _make_run(
        [
            Check(type="schema", name="Check col types", result=ResultEnum.failed, reason="type mismatch"),
            Check(type="schema", name="Check nullability", result=ResultEnum.warning, reason="nullable changed"),
            Check(type="schema", name="Check row count", result=ResultEnum.passed, reason=None),
        ]
    )
    env = {k: v for k, v in os.environ.items() if k != "GITHUB_ACTIONS"}
    env["TF_BUILD"] = "True"
    with patch.dict(os.environ, env, clear=True):
        write_ci_output(run, "datacontract.yaml")

    captured = capsys.readouterr()
    assert "##vso[task.logissue type=error;sourcepath=datacontract.yaml]Check col types: type mismatch" in captured.out
    assert (
        "##vso[task.logissue type=warning;sourcepath=datacontract.yaml]Check nullability: nullable changed"
        in captured.out
    )
    assert "Check row count" not in captured.out


def test_azure_annotation_format_for_errors(capsys):
    run = _make_run(
        [
            Check(type="quality", name="freshness", result=ResultEnum.error, reason="connection timeout"),
        ]
    )
    env = {k: v for k, v in os.environ.items() if k != "GITHUB_ACTIONS"}
    env["TF_BUILD"] = "True"
    with patch.dict(os.environ, env, clear=True):
        write_ci_output(run, "my/contract.yaml")

    captured = capsys.readouterr()
    assert (
        captured.out.strip()
        == "##vso[task.logissue type=error;sourcepath=my/contract.yaml]freshness: connection timeout"
    )


# --- Step summary tests ---


def test_step_summary_single_contract():
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
            write_ci_summary([("datacontract.yaml", run)])

        with open(summary_path) as f:
            content = f.read()
        assert "## Data Contract CI: datacontract.yaml" in content
        assert "| Result | Check | Field | Details |" in content
        assert "Check types" in content
        assert "Check nulls" in content
        # Single contract should not have aggregate header
        assert "| Result | Contract |" not in content
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
            write_ci_summary([("datacontract.yaml", run)])

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
            write_ci_summary([("datacontract.yaml", run)])

        with open(summary_path) as f:
            content = f.read()
        assert "**Result: 🔴 failed**" in content
        assert "2 checks" in content
        assert "1 passed" in content
        assert "1 failed" in content
    finally:
        os.unlink(summary_path)


def test_sanitize_md_cell():
    assert _sanitize_md_cell("foo | bar\nbaz") == "foo \\| bar baz"
    assert _sanitize_md_cell("line1\r\nline2\rline3") == "line1 line2 line3"


def test_sanitize_annotation():
    assert _sanitize_annotation("error\non line 2\r\nand line 3") == "error on line 2 and line 3"
    assert _sanitize_annotation(None) == ""
    assert _sanitize_annotation("50% done") == "50%25 done"


def test_step_summary_multi_contract():
    run_passed = _make_run([Check(type="schema", name="Check types", result=ResultEnum.passed, reason=None)])
    run_failed = _make_run([Check(type="schema", name="Check nulls", result=ResultEnum.failed, reason="not nullable")])
    with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
        summary_path = f.name

    try:
        env = {k: v for k, v in os.environ.items() if k != "GITHUB_ACTIONS"}
        env["GITHUB_STEP_SUMMARY"] = summary_path
        with patch.dict(os.environ, env, clear=True):
            write_ci_summary([("orders.yaml", run_passed), ("customers.yaml", run_failed)])

        with open(summary_path) as f:
            content = f.read()
        # Aggregate header
        assert "## Data Contract CI" in content
        assert "1/2 contracts passed" in content
        assert "| Result | Contract |" in content
        assert "orders.yaml" in content
        assert "customers.yaml" in content
        # Per-contract detail sections use ### when multiple
        assert "### Data Contract CI: orders.yaml" in content
        assert "### Data Contract CI: customers.yaml" in content
    finally:
        os.unlink(summary_path)


# --- CLI integration tests ---


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


def test_ci_multiple_files():
    result = runner.invoke(
        app, ["ci", "fixtures/lint/valid_datacontract.yaml", "fixtures/lint/valid_datacontract.yaml"]
    )
    assert result.exit_code == 0


def test_ci_multiple_files_with_failure():
    result = runner.invoke(app, ["ci", "fixtures/lint/valid_datacontract.yaml", "nonexistent.yaml"])
    assert result.exit_code == 1


def test_ci_fail_on_never():
    result = runner.invoke(app, ["ci", "--fail-on", "never", "nonexistent.yaml"])
    assert result.exit_code == 0


def test_ci_fail_on_warning():
    # valid_datacontract.yaml produces a warning ("Schema block is missing")
    result = runner.invoke(app, ["ci", "--fail-on", "warning", "fixtures/lint/valid_datacontract.yaml"])
    assert result.exit_code == 1


def test_ci_fail_on_error_is_default():
    # valid_datacontract.yaml produces warnings but not errors/failures — should pass
    result = runner.invoke(app, ["ci", "fixtures/lint/valid_datacontract.yaml"])
    assert result.exit_code == 0


def test_ci_continues_after_failure():
    """CI should test all contracts even if one fails."""
    result = runner.invoke(app, ["ci", "nonexistent.yaml", "fixtures/lint/valid_datacontract.yaml"])
    # Should still report on the second file
    assert "fixtures/lint/valid_datacontract.yaml" in result.stdout
    # But exit 1 because the first failed
    assert result.exit_code == 1


def test_ci_output_rejects_multi_with_output():
    result = runner.invoke(
        app,
        [
            "ci",
            "--output",
            "results.xml",
            "--output-format",
            "junit",
            "fixtures/lint/valid_datacontract.yaml",
            "fixtures/lint/valid_datacontract.yaml",
        ],
    )
    assert result.exit_code == 1
    assert "cannot be used with multiple contracts" in result.stdout


# --- JSON output tests ---


def test_json_output_single(capsys):
    run = _make_run([Check(type="schema", name="Check types", result=ResultEnum.passed, reason=None)])
    write_json_results([("datacontract.yaml", run)])
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert data["result"] == "passed"
    assert data["location"] == "datacontract.yaml"
    assert len(data["checks"]) == 1


def test_json_output_multi(capsys):
    run1 = _make_run([Check(type="schema", name="Check types", result=ResultEnum.passed, reason=None)])
    run2 = _make_run([Check(type="schema", name="Check nulls", result=ResultEnum.failed, reason="not nullable")])
    write_json_results([("orders.yaml", run1), ("customers.yaml", run2)])
    captured = capsys.readouterr()
    data = json.loads(captured.out)
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["result"] == "passed"
    assert data[0]["location"] == "orders.yaml"
    assert data[1]["result"] == "failed"
    assert data[1]["location"] == "customers.yaml"


def test_ci_json_flag():
    env = {k: v for k, v in os.environ.items() if k not in ("GITHUB_ACTIONS", "TF_BUILD")}
    with patch.dict(os.environ, env, clear=True):
        result = runner.invoke(app, ["ci", "--json", "fixtures/lint/valid_datacontract.yaml"])
    assert result.exit_code == 0
    # With --json, stdout should be clean JSON (human output goes to stderr)
    data = json.loads(result.stdout)
    assert "result" in data
    assert "location" in data
    assert "checks" in data
