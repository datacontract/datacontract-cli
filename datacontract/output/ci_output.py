import json
import os
import sys
from typing import List, Tuple

from datacontract.model.run import Run
from datacontract.output.test_results_writer import to_field


def _sanitize_md_cell(text: str) -> str:
    """Escape pipe characters and collapse newlines for use in markdown table cells."""
    return text.replace("|", "\\|").replace("\r\n", " ").replace("\r", " ").replace("\n", " ").strip()


def write_ci_output(run: Run, data_contract_file: str, json_mode: bool = False):
    """Write CI-specific output for a single contract: annotations only."""
    out = sys.stderr if json_mode else sys.stdout
    if os.environ.get("GITHUB_ACTIONS") == "true":
        _write_github_annotations(run, data_contract_file, out)
    elif os.environ.get("TF_BUILD") == "True":
        _write_azure_annotations(run, data_contract_file, out)


def write_ci_summary(results: List[Tuple[str, Run]]):
    """Write aggregated CI step summary for all contracts."""
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return
    _write_github_step_summary(results, summary_path)


def _sanitize_annotation(text: str | None) -> str:
    """Collapse newlines and trim text for use in CI annotations."""
    if not text:
        return ""
    return text.replace("%", "%25").replace("\r\n", " ").replace("\r", " ").replace("\n", " ").strip()


def _write_github_annotations(run: Run, data_contract_file: str, out=sys.stdout):
    for check in run.checks:
        name = _sanitize_annotation(check.name)
        reason = _sanitize_annotation(check.reason)
        if check.result in ("failed", "error"):
            print(f"::error file={data_contract_file}::{name}: {reason}", file=out)
        elif check.result == "warning":
            print(f"::warning file={data_contract_file}::{name}: {reason}", file=out)


def _write_azure_annotations(run: Run, data_contract_file: str, out=sys.stdout):
    for check in run.checks:
        name = _sanitize_annotation(check.name)
        reason = _sanitize_annotation(check.reason)
        if check.result in ("failed", "error"):
            print(f"##vso[task.logissue type=error;sourcepath={data_contract_file}]{name}: {reason}", file=out)
        elif check.result == "warning":
            print(f"##vso[task.logissue type=warning;sourcepath={data_contract_file}]{name}: {reason}", file=out)


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
        result_values = [run.result for _, run in results]
        has_failures = any(r in ("failed", "error") for r in result_values)
        has_warnings = any(r == "warning" for r in result_values)
        if has_failures:
            overall = "🔴 failed"
        elif has_warnings:
            overall = "🟠 warning"
        else:
            overall = "🟢 passed"
        lines.append("## Data Contract CI")
        lines.append("")
        n_passed = sum(1 for r in result_values if r == "passed")
        lines.append(f"**{overall}** — {n_passed}/{n_total} contracts passed")
        lines.append("")
        lines.append("| Result | Contract |")
        lines.append("|--------|----------|")
        for data_contract_file, run in results:
            result = RESULT_EMOJI.get(run.result, run.result.value if hasattr(run.result, "value") else str(run.result))
            lines.append(f"| {result} | {data_contract_file} |")
        lines.append("")

    # Per-contract detail sections
    for data_contract_file, run in results:
        result_display = RESULT_EMOJI.get(
            run.result, run.result.value if hasattr(run.result, "value") else str(run.result)
        )

        n_total = len(run.checks) if run.checks else 0
        n_passed = sum(1 for c in run.checks if c.result == "passed") if run.checks else 0
        n_failed = sum(1 for c in run.checks if c.result == "failed") if run.checks else 0
        n_warnings = sum(1 for c in run.checks if c.result == "warning") if run.checks else 0
        n_errors = sum(1 for c in run.checks if c.result == "error") if run.checks else 0

        duration = (
            (run.timestampEnd - run.timestampStart).total_seconds() if run.timestampStart and run.timestampEnd else 0
        )

        heading_level = "###" if len(results) > 1 else "##"
        lines.append(f"{heading_level} Data Contract CI: {data_contract_file}")
        lines.append("")
        lines.append(
            f"**Result: {result_display}** | {n_total} checks | {n_passed} passed | {n_failed} failed | {n_warnings} warnings | {n_errors} errors | {duration:.1f}s"
        )
        lines.append("")

        if run.checks:
            lines.append("| Result | Check | Field | Details |")
            lines.append("|--------|-------|-------|---------|")
            for check in sorted(
                run.checks,
                key=lambda c: (
                    c.result.value if hasattr(c.result, "value") else str(c.result or ""),
                    c.model or "",
                    c.field or "",
                ),
            ):
                field = _sanitize_md_cell(to_field(run, check) or "")
                reason = _sanitize_md_cell(check.reason or "")
                name = _sanitize_md_cell(check.name or "")
                result = check.result.value if hasattr(check.result, "value") else str(check.result)
                lines.append(f"| {result} | {name} | {field} | {reason} |")
            lines.append("")

    with open(summary_path, "a", encoding="utf-8") as f:
        f.write("\n".join(lines) + "\n")


def write_json_results(results: List[Tuple[str, Run]]):
    """Print test results as JSON to stdout."""
    if len(results) == 1:
        location, run = results[0]
        obj = json.loads(run.model_dump_json(exclude_none=True))
        obj["location"] = location
        print(json.dumps(obj, indent=2))
    else:
        output = []
        for location, run in results:
            obj = json.loads(run.model_dump_json(exclude_none=True))
            obj["location"] = location
            output.append(obj)
        print(json.dumps(output, indent=2))
