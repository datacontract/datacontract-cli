import os

from datacontract.model.run import Run
from datacontract.output.test_results_writer import to_field


def write_ci_output(run: Run, data_contract_file: str):
    """Write CI-specific output: GitHub annotations and step summary."""
    _write_github_annotations(run, data_contract_file)
    _write_github_step_summary(run, data_contract_file)


def _write_github_annotations(run: Run, data_contract_file: str):
    if os.environ.get("GITHUB_ACTIONS") != "true":
        return

    for check in run.checks:
        if check.result in ("failed", "error"):
            print(f"::error file={data_contract_file}::{check.name}: {check.reason}")
        elif check.result == "warning":
            print(f"::warning file={data_contract_file}::{check.name}: {check.reason}")


def _write_github_step_summary(run: Run, data_contract_file: str):
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return

    result_emoji = {
        "passed": "passed",
        "warning": "warning",
        "failed": "failed",
        "error": "error",
    }
    result_str = run.result.value if hasattr(run.result, "value") else run.result
    result_display = result_emoji.get(result_str, result_str)

    total = len(run.checks) if run.checks else 0
    passed = sum(1 for c in run.checks if c.result == "passed") if run.checks else 0
    failed = sum(1 for c in run.checks if c.result == "failed") if run.checks else 0
    warnings = sum(1 for c in run.checks if c.result == "warning") if run.checks else 0
    errors = sum(1 for c in run.checks if c.result == "error") if run.checks else 0

    duration = (run.timestampEnd - run.timestampStart).total_seconds() if run.timestampStart and run.timestampEnd else 0

    lines = [
        f"## Data Contract CI: {data_contract_file}",
        "",
        f"**Result: {result_display}** | {total} checks | {passed} passed | {failed} failed | {warnings} warnings | {errors} errors | {duration:.1f}s",
        "",
    ]

    if run.checks:
        lines.append("| Result | Check | Field | Details |")
        lines.append("|--------|-------|-------|---------|")
        for check in sorted(run.checks, key=lambda c: (c.result or "", c.model or "", c.field or "")):
            field = to_field(run, check) or ""
            reason = check.reason or ""
            result_val = check.result.value if hasattr(check.result, "value") else check.result
            lines.append(f"| {result_val} | {check.name} | {field} | {reason} |")
        lines.append("")

    with open(summary_path, "a") as f:
        f.write("\n".join(lines) + "\n")
