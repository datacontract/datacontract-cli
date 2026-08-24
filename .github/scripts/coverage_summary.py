"""Render coverage.json as a GitHub Actions run-summary table.

Run by the `coverage` job in .github/workflows/ci.yaml. The overall number plus
the least-covered modules is the whole point: with ~40 exporters and importers
registered through a factory, a module whose last test went away still passes
CI, and nothing else in the run would say so.

Reporting only — there is no `fail_under` in pyproject.toml and this script
always exits 0, so coverage cannot block a pull request.
"""

import json
from pathlib import Path

# Enough rows to show the untested corners without burying the total.
LEAST_COVERED = 25


def main() -> None:
    report = Path("coverage.json")
    if not report.is_file():
        print("No coverage.json — the test step did not get far enough to write one.")
        return

    data = json.loads(report.read_text(encoding="utf-8"))
    totals = data["totals"]

    print(f"## Coverage: {totals['percent_covered_display']}%")
    print()
    print(f"`{totals['covered_lines']}` of `{totals['num_statements']}` statements covered.")
    print()

    files = sorted(data["files"].items(), key=lambda item: item[1]["summary"]["percent_covered"])
    uncovered = [(path, summary) for path, summary in files if summary["summary"]["missing_lines"]]
    if not uncovered:
        print("Every module is fully covered.")
        return

    print(f"### {min(len(uncovered), LEAST_COVERED)} least-covered modules")
    print()
    print("| Module | Coverage | Missing |")
    print("| --- | --: | --: |")
    for path, info in uncovered[:LEAST_COVERED]:
        summary = info["summary"]
        print(f"| `{path}` | {summary['percent_covered']:.0f}% | {summary['missing_lines']} |")
    print()
    print(f"_{len(uncovered)} modules have uncovered lines. Reported for visibility; not a gate._")


if __name__ == "__main__":
    main()
