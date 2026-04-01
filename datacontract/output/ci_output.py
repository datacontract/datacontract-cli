import json
import os
from typing import List, Tuple

from datacontract.model.run import Run
from datacontract.output.test_results_writer import to_field


def _sanitize_md_cell(text: str) -> str:
    """Escape pipe characters and collapse newlines for use in markdown table cells."""
    return text.replace("|", "\\|").replace("\n", " ").strip()


def write_ci_output(run: Run, data_contract_file: str):
    """Write CI-specific output for a single contract: annotations only."""
    if os.environ.get("GITHUB_ACTIONS") == "true":
        _write_github_annotations(run, data_contract_file)
    elif os.environ.get("TF_BUILD") == "True":
        _write_azure_annotations(run, data_contract_file)


def write_ci_summary(results: List[Tuple[str, Run]]):
    """Write aggregated CI step summary for all contracts."""
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    _write_github_step_summary(results, summary_path)


def _write_github_annotations(run: Run, data_contract_file: str):
    for check in run.checks:
        if check.result in ("failed", "error"):
            print(f"::error file={data_contract_file}::{check.name}: {check.reason}")
        elif check.result == "warning":
            print(f"::warning file={data_contract_file}::{check.name}: {check.reason}")


def _write_azure_annotations(run: Run, data_contract_file: str):
    for check in run.checks:
        if check.result in ("failed", "error"):
            print(f"##vso[task.logissue type=error;sourcepath={data_contract_file}]{check.name}: {check.reason}")
        elif check.result == "warning":
            print(f"##vso[task.logissue type=warning;sourcepath={data_contract_file}]{check.name}: {check.reason}")


RESULT_EMOJI = {
    "passed": "🟢 passed",
    "warning": "🟠 warning",
    "failed": "🔴 failed",
    "error": "🔴 error",
}


def _write_github_step_summary(results: List[Tuple[str, Run]], summary_path: str):
    lines = []

    # Aggregate header (only when multiple contracts)
    if len(results) > 1:
        n_total = len(results)
        n_passed = sum(1 for _, run in results if run.result == "passed")
        overall = "🟢 passed" if n_passed == n_total else "🔴 failed"
        lines.append("## Data Contract CI")
        lines.append("")
        lines.append(f"**{overall}** — {n_passed}/{n_total} contracts successful")
        lines.append("")
        lines.append("| Result | Contract |")
        lines.append("|--------|----------|")
        for data_contract_file, run in results:
            result = RESULT_EMOJI.get(run.result, run.result)
            lines.append(f"| {result} | {data_contract_file} |")
        lines.append("")

    # Per-contract detail sections
    for data_contract_file, run in results:
        result_display = RESULT_EMOJI.get(run.result, run.result)

        n_total = len(run.checks) if run.checks else 0
        n_passed = sum(1 for c in run.checks if c.result == "passed") if run.checks else 0
        n_failed = sum(1 for c in run.checks if c.result == "failed") if run.checks else 0
        n_warnings = sum(1 for c in run.checks if c.result == "warning") if run.checks else 0
        n_errors = sum(1 for c in run.checks if c.result == "error") if run.checks else 0

        duration = (run.timestampEnd - run.timestampStart).total_seconds() if run.timestampStart and run.timestampEnd else 0

        heading_level = "###" if len(results) > 1 else "##"
        lines.append(f"{heading_level} Data Contract CI: {data_contract_file}")
        lines.append("")
        lines.append(f"**Result: {result_display}** | {n_total} checks | {n_passed} passed | {n_failed} failed | {n_warnings} warnings | {n_errors} errors | {duration:.1f}s")
        lines.append("")

        if run.checks:
            lines.append("| Result | Check | Field | Details |")
            lines.append("|--------|-------|-------|---------|")
            for check in sorted(run.checks, key=lambda c: (c.result or "", c.model or "", c.field or "")):
                field = _sanitize_md_cell(to_field(run, check) or "")
                reason = _sanitize_md_cell(check.reason or "")
                name = _sanitize_md_cell(check.name or "")
                lines.append(f"| {check.result} | {name} | {field} | {reason} |")
            lines.append("")

    with open(summary_path, "a") as f:
        f.write("\n".join(lines) + "\n")


def write_json_results(results: List[Tuple[str, Run]]):
    """Print test results as JSON to stdout."""
    if len(results) == 1:
        print(results[0][1].model_dump_json(indent=2, exclude_none=True))
    else:
        output = [json.loads(run.model_dump_json(exclude_none=True)) for _, run in results]
        print(json.dumps(output, indent=2))
