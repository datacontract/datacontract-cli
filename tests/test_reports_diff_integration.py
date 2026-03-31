"""
Integration tests — full pipeline
-----------------------------------
To regenerate the golden fixtures after an intentional output change, run:

    python tests/fixtures/diff/integration/helper/generate_golden.py

Then review with `git diff tests/fixtures/diff/integration/` and commit if correct.
"""

import os
import re

from datacontract.reports.diff.contract_diff_report import ContractDiffReport
from datacontract.reports.diff.diff import ContractDiff
from datacontract.reports.diff.html_contract_diff_renderer import HtmlContractDiffRenderer
from datacontract.reports.diff.text_contract_diff_renderer import TextContractDiffRenderer

FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "diff", "integration")
V1 = os.path.join(FIXTURE_DIR, "report_renderer_integration_v1.yaml")
V2 = os.path.join(FIXTURE_DIR, "report_renderer_integration_v2.yaml")


def _build_report_data():
    contracts_diff = ContractDiff().generate(V1, V2)
    # Use relative paths from the test fixtures directory
    v1_rel = os.path.relpath(V1, os.path.dirname(os.path.dirname(__file__)))
    v2_rel = os.path.relpath(V2, os.path.dirname(os.path.dirname(__file__)))
    return ContractDiffReport().build_report_data(
        diff_result=contracts_diff,
        source_label=v1_rel,
        target_label=v2_rel,
    )


def _strip_style(html: str) -> str:
    return re.sub(r"<style>.*?</style>", "<style>...</style>", html, flags=re.DOTALL)


class TestIntegrationSmoke:
    """Fast sanity checks: known changes present, correct counts."""

    def test_customers_schema_added(self):
        rd = _build_report_data()
        paths = [c["path"] for c in rd["summary"]["changes"]]
        assert any("customers" in p for p in paths)

    def test_customer_id_field_removed(self):
        rd = _build_report_data()
        paths = [c["path"] for c in rd["summary"]["changes"]]
        assert any("customer_id" in p for p in paths)

    def test_availability_sla_changed(self):
        rd = _build_report_data()
        paths = [c["path"] for c in rd["summary"]["changes"]]
        assert any("availability" in p for p in paths)

    def test_summary_counts(self):
        rd = _build_report_data()
        counts = rd["summary"]["counts"]
        assert counts["added"] == 2
        assert counts["removed"] == 1
        assert counts["changed"] == 4

    def test_detail_has_old_and_new_values_for_sla(self):
        rd = _build_report_data()
        match = next(
            (c for c in rd["detail"]["changes"] if "value" in c["path"] and "availability" in c["path"]),
            None,
        )
        assert match is not None
        assert match["old_value"] == "99.9%"
        assert match["new_value"] == "99.5%"


FIXED_TS = "2025-01-01 00:00:00 UTC"


class TestIntegrationGoldenText:
    def test_exact_text_output(self):
        from unittest.mock import patch

        golden_path = os.path.join(FIXTURE_DIR, "golden_integration_text.txt")
        expected = open(golden_path).read()
        with patch("datacontract.reports.diff.contract_diff_report.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = FIXED_TS
            rd = _build_report_data()
        actual = TextContractDiffRenderer(report_data=rd).render()
        assert actual == expected, (
            "Integration text output has changed. If intentional, regenerate "
            "golden_integration_text.txt (see module docstring for command)."
        )


class TestIntegrationGoldenHtml:
    def test_exact_html_structure(self):
        from unittest.mock import patch

        golden_path = os.path.join(FIXTURE_DIR, "golden_integration_html.html")
        expected = open(golden_path).read()
        with patch("datacontract.reports.diff.contract_diff_report.datetime") as mock_dt:
            mock_dt.now.return_value.strftime.return_value = FIXED_TS
            rd = _build_report_data()
        actual = HtmlContractDiffRenderer(report_data=rd).render()
        assert actual == expected, (
            "Integration HTML structure has changed. If intentional, regenerate "
            "golden_integration_html.html (see module docstring for command)."
        )