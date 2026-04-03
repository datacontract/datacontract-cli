"""
generate_golden.py — Regenerate integration golden fixtures
------------------------------------------------------------
Run this script whenever the diff/report output intentionally changes and the
golden files in tests/fixtures/diff/integration/ need to be updated.

Usage (from the repo root):
    python tests/fixtures/diff/integration/helper/generate_golden.py

The script uses the same fixed timestamp as the integration tests so the
generated files are deterministic and can be committed without spurious diffs.

Golden files written:
    tests/fixtures/diff/integration/golden_integration_text.txt
    tests/fixtures/diff/integration/golden_integration_html.html

After running, review the diff with git and commit if the changes are expected:
    git diff tests/fixtures/diff/integration/
"""

import os
from unittest.mock import patch

from datacontract.reports.diff.contract_diff_report import ContractDiffReport
from datacontract.reports.diff.diff import ContractDiff
from datacontract.reports.diff.html_contract_diff_renderer import HtmlContractDiffRenderer
from datacontract.reports.diff.text_contract_diff_renderer import TextContractDiffRenderer

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "..")
V1 = os.path.join(FIXTURE_DIR, "report_renderer_integration_v1.yaml")
V2 = os.path.join(FIXTURE_DIR, "report_renderer_integration_v2.yaml")

FIXED_TS = "2025-01-01 00:00:00 UTC"


def _build_report_data():
    contracts_diff = ContractDiff().generate(V1, V2)
    v1_rel = os.path.relpath(V1, os.path.dirname(os.path.dirname(__file__)))
    v2_rel = os.path.relpath(V2, os.path.dirname(os.path.dirname(__file__)))
    return ContractDiffReport().build_report_data(
        diff_result=contracts_diff,
        source_label=v1_rel,
        target_label=v2_rel,
    )


def generate():
    with patch("datacontract.reports.diff.contract_diff_report.datetime") as mock_dt:
        mock_dt.now.return_value.strftime.return_value = FIXED_TS
        rd = _build_report_data()

    text_path = os.path.join(FIXTURE_DIR, "golden_integration_text.txt")
    html_path = os.path.join(FIXTURE_DIR, "golden_integration_html.html")

    text_content = TextContractDiffRenderer(report_data=rd).render()
    html_content = HtmlContractDiffRenderer(report_data=rd).render()

    with open(text_path, "w", encoding="utf-8") as f:
        f.write(text_content)
    print(f"Written: {text_path}")

    with open(html_path, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Written: {html_path}")

    print("\nDone. Review changes with: git diff tests/fixtures/diff/integration/")


if __name__ == "__main__":
    generate()