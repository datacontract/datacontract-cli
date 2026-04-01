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
    _write_annotations(run, data_contract_file)


def write_ci_summary(results: List[Tuple[str, Run]]):
    """Write aggregated CI step summary for all contracts."""
    _write_github_step_summary(results)


def _write_annotations(run: Run, data_contract_file: str):
    if os.environ.get("GITHUB_ACTIONS") == "true":
        _write_github_annotations(run, data_contract_file)
    elif os.environ.get("TF_BUILD") == "True":
        _write_azure_annotations(run, data_contract_file)


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


def _result_str(run: Run) -> str:
    return run.result.value if hasattr(run.result, "value") else run.result


RESULT_EMOJI = {
    "passed": "🟢 passed",
    "warning": "🟠 warning",
    "failed": "🔴 failed",
    "error": "🔴 error",
}


def _write_github_step_summary(results: List[Tuple[str, Run]]):
    summary_path = os.environ.get("GITHUB_STEP_SUMMARY")
    if not summary_path:
        return

    lines = []

    # Aggregate header (only when multiple contracts)
    if len(results) > 1:
        total_contracts = len(results)
        passed_contracts = sum(1 for _, run in results if _result_str(run) == "passed")
        failed_contracts = total_contracts - passed_contracts
        overall = "🟢 passed" if failed_contracts == 0 else "🔴 failed"
        lines.append("## Data Contract CI")
        lines.append("")
        lines.append(f"**{overall}** | {total_contracts} contracts | {passed_contracts} passed | {failed_contracts} failed")
        lines.append("")
        lines.append("| Result | Contract |")
        lines.append("|--------|----------|")
        for data_contract_file, run in results:
            result = RESULT_EMOJI.get(_result_str(run), _result_str(run))
            lines.append(f"| {result} | {data_contract_file} |")
        lines.append("")

    # Per-contract detail sections
    for data_contract_file, run in results:
        result_display = RESULT_EMOJI.get(_result_str(run), _result_str(run))

        total = len(run.checks) if run.checks else 0
        passed = sum(1 for c in run.checks if c.result == "passed") if run.checks else 0
        failed = sum(1 for c in run.checks if c.result == "failed") if run.checks else 0
        warnings = sum(1 for c in run.checks if c.result == "warning") if run.checks else 0
        errors = sum(1 for c in run.checks if c.result == "error") if run.checks else 0

        duration = (run.timestampEnd - run.timestampStart).total_seconds() if run.timestampStart and run.timestampEnd else 0

        heading_level = "###" if len(results) > 1 else "##"
        lines.append(f"{heading_level} Data Contract CI: {data_contract_file}")
        lines.append("")
        lines.append(f"**Result: {result_display}** | {total} checks | {passed} passed | {failed} failed | {warnings} warnings | {errors} errors | {duration:.1f}s")
        lines.append("")

        if run.checks:
            lines.append("| Result | Check | Field | Details |")
            lines.append("|--------|-------|-------|---------|")
            for check in sorted(run.checks, key=lambda c: (c.result or "", c.model or "", c.field or "")):
                field = _sanitize_md_cell(to_field(run, check) or "")
                reason = _sanitize_md_cell(check.reason or "")
                name = _sanitize_md_cell(check.name or "")
                result_val = check.result.value if hasattr(check.result, "value") else check.result
                lines.append(f"| {result_val} | {name} | {field} | {reason} |")
            lines.append("")

    with open(summary_path, "a") as f:
        f.write("\n".join(lines) + "\n")


def write_json_results(results: List[Tuple[str, Run]]):
    """Print test results as JSON to stdout."""
    if len(results) == 1:
        print(results[0][1].model_dump_json(indent=2))
    else:
        output = [json.loads(run.model_dump_json()) for _, run in results]
        print(json.dumps(output, indent=2))
