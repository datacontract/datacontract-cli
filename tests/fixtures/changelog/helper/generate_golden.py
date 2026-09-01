"""
generate_golden.py — Regenerate changelog golden fixtures
----------------------------------------------------------
Run this script whenever the changelog text output intentionally changes and the
golden file in tests/fixtures/changelog/ needs to be updated.

Usage (from the repo root):
    python tests/fixtures/changelog/helper/generate_golden.py

Golden files written:
    tests/fixtures/changelog/golden_changelog_text.txt
    tests/fixtures/changelog/golden_breaking_text.txt

After running, review the diff with git and commit if the changes are expected:
    git diff tests/fixtures/changelog/
"""

import io
import os
import sys

from rich.console import Console

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "..")
REPO_ROOT = os.path.join(os.path.dirname(__file__), "..", "..", "..", "..")

V1 = os.path.normpath(os.path.join(REPO_ROOT, "tests/fixtures/changelog/integration/changelog_integration_v1.yaml"))
V2 = os.path.normpath(os.path.join(REPO_ROOT, "tests/fixtures/changelog/integration/changelog_integration_v2.yaml"))


def _render(write, result) -> str:
    buf = io.StringIO()
    con = Console(file=buf, width=300, highlight=False, no_color=True)
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        write(result, con)
    finally:
        sys.stdout = old_stdout
    return buf.getvalue()


def generate():
    # Import here so the script can be run from the repo root with venv activated
    from datacontract.data_contract import DataContract
    from datacontract.output.text_breaking_results import write_text_breaking_results
    from datacontract.output.text_changelog_results import write_text_changelog_results

    v1 = DataContract(data_contract_file=V1)
    outputs = {
        "golden_changelog_text.txt": _render(
            write_text_changelog_results, v1.changelog(DataContract(data_contract_file=V2))
        ),
        "golden_breaking_text.txt": _render(
            write_text_breaking_results, v1.breaking(DataContract(data_contract_file=V2))
        ),
    }

    for name, text in outputs.items():
        text_path = os.path.normpath(os.path.join(FIXTURE_DIR, name))
        with open(text_path, "w", encoding="utf-8") as f:
            f.write(text)
        print(f"Written: {text_path}")
    print("\nDone. Review changes with: git diff tests/fixtures/changelog/")


if __name__ == "__main__":
    generate()
