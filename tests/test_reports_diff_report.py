"""
test_reports_diff_report — Unit tests for ContractDiffReport
-------------------------------------------------------------------
Test classes:
    TestBuildReportDataStructure   — build_report_data() output shape and empty-diff
    TestBuildReportDataAdded       — Added change entries (scalar and dict payloads)
    TestBuildReportDataRemoved     — Removed change entries
    TestBuildReportDataChanged     — Changed entries and scalar rollup to parent
    TestBuildReportDataSummaryRollup — summary deduplication and count consistency
    TestGenerate                   — generate(): fmt routing, output_path, error handling
"""

import os

import pytest

from datacontract.reports.diff.contract_diff_report import ContractDiffReport

REPORT = ContractDiffReport()


def _added(path: str, payload) -> dict:
    return {"dictionary_item_added": {f"root['{path}']": payload}}


def _removed(path: str, payload) -> dict:
    return {"dictionary_item_removed": {f"root['{path}']": payload}}


def _changed(path: str, old, new) -> dict:
    return {"values_changed": {f"root['{path}']": {"old_value": old, "new_value": new}}}


def _merge(*diffs: dict) -> dict:
    """Merge multiple single-key DeepDiff dicts into one."""
    merged = {}
    for d in diffs:
        for k, v in d.items():
            merged.setdefault(k, {}).update(v)
    return merged


class TestBuildReportDataStructure:
    def test_returns_expected_top_level_keys(self):
        rd = REPORT.build_report_data({})
        assert set(rd.keys()) == {"source_label", "target_label", "header", "summary", "detail"}

    def test_header_contains_title_and_subtitle(self):
        rd = REPORT.build_report_data({}, source_label="v1.yaml", target_label="v2.yaml")
        assert rd["header"]["title"] == "ODCS Data Contract Diff"
        assert "v1.yaml" in rd["header"]["subtitle"]
        assert "v2.yaml" in rd["header"]["subtitle"]

    def test_source_and_target_labels_stored(self):
        rd = REPORT.build_report_data({}, source_label="before.yaml", target_label="after.yaml")
        assert rd["source_label"] == "before.yaml"
        assert rd["target_label"] == "after.yaml"

    def test_empty_diff_produces_zero_counts(self):
        rd = REPORT.build_report_data({})
        assert rd["summary"]["counts"] == {"added": 0, "removed": 0, "changed": 0}
        assert rd["detail"]["counts"] == {"added": 0, "removed": 0, "changed": 0}

    def test_empty_diff_produces_empty_changes(self):
        rd = REPORT.build_report_data({})
        assert rd["summary"]["changes"] == []
        assert rd["detail"]["changes"] == []

    def test_unknown_deepdiff_keys_ignored(self):
        rd = REPORT.build_report_data({"unknown_key": {"root['x']": 1}})
        assert rd["summary"]["changes"] == []


class TestBuildReportDataAdded:
    def test_added_scalar_appears_in_detail(self):
        rd = REPORT.build_report_data(_added("schema']['orders", "v"))
        paths = [c["path"] for c in rd["detail"]["changes"]]
        assert any("orders" in p for p in paths)

    def test_added_scalar_change_type(self):
        rd = REPORT.build_report_data(_added("schema']['orders", "val"))
        match = next(c for c in rd["detail"]["changes"] if "orders" in c["path"])
        assert match["changeType"] == "Added"

    def test_added_scalar_has_new_value(self):
        rd = REPORT.build_report_data(_added("schema']['orders", "val"))
        match = next(c for c in rd["detail"]["changes"] if c["path"] == "schema.orders")
        assert match.get("new_value") == "val"

    def test_added_dict_expands_to_leaf_entries(self):
        payload = {"physicalName": "orders_tbl", "description": "Orders"}
        rd = REPORT.build_report_data(_added("schema']['orders", payload))
        paths = [c["path"] for c in rd["detail"]["changes"]]
        assert "schema.orders.physicalName" in paths
        assert "schema.orders.description" in paths

    def test_added_dict_parent_entry_included(self):
        payload = {"physicalName": "orders_tbl"}
        rd = REPORT.build_report_data(_added("schema']['orders", payload))
        paths = [c["path"] for c in rd["detail"]["changes"]]
        assert "schema.orders" in paths

    def test_added_count_incremented(self):
        rd = REPORT.build_report_data(_added("schema']['orders", "v"))
        assert rd["detail"]["counts"]["added"] >= 1

    def test_added_appears_in_summary(self):
        # Scalar Added rolls up to parent — use a 2-level path so it lands at schema.orders
        rd = REPORT.build_report_data(_added("schema']['orders']['physicalName", "v"))
        paths = [c["path"] for c in rd["summary"]["changes"]]
        assert any("orders" in p for p in paths)


class TestBuildReportDataRemoved:
    def test_removed_scalar_appears_in_detail(self):
        rd = REPORT.build_report_data(_removed("schema']['orders", "v"))
        paths = [c["path"] for c in rd["detail"]["changes"]]
        assert any("orders" in p for p in paths)

    def test_removed_scalar_has_old_value(self):
        rd = REPORT.build_report_data(_removed("schema']['orders", "val"))
        match = next(c for c in rd["detail"]["changes"] if c["path"] == "schema.orders")
        assert match.get("old_value") == "val"

    def test_removed_dict_expands_to_leaf_entries(self):
        payload = {"logicalType": "string", "required": True}
        rd = REPORT.build_report_data(_removed("schema']['orders']['properties']['amount", payload))
        paths = [c["path"] for c in rd["detail"]["changes"]]
        assert "schema.orders.properties.amount.logicalType" in paths

    def test_removed_count_incremented(self):
        rd = REPORT.build_report_data(_removed("schema']['orders", "v"))
        assert rd["detail"]["counts"]["removed"] >= 1


class TestBuildReportDataChanged:
    def test_changed_scalar_in_detail(self):
        rd = REPORT.build_report_data(
            _changed("schema']['orders']['properties']['order_date']['logicalType", "string", "date")
        )
        match = next((c for c in rd["detail"]["changes"] if "logicalType" in c["path"]), None)
        assert match is not None
        assert match["changeType"] == "Changed"
        assert match["old_value"] == "string"
        assert match["new_value"] == "date"

    def test_changed_count_incremented(self):
        rd = REPORT.build_report_data(_changed("slaProperties']['availability']['value", "99.9%", "99.5%"))
        assert rd["detail"]["counts"]["changed"] == 1

    def test_changed_scalar_rolled_up_to_parent_in_summary(self):
        rd = REPORT.build_report_data(
            _changed("schema']['orders']['properties']['order_date']['logicalType", "string", "date")
        )
        summary_paths = [c["path"] for c in rd["summary"]["changes"]]
        assert not any("logicalType" in p for p in summary_paths)
        assert any("order_date" in p for p in summary_paths)


class TestBuildReportDataSummaryRollup:
    def test_multiple_scalar_changes_on_same_parent_produce_one_summary_entry(self):
        diff = _merge(
            _changed("schema']['orders']['properties']['order_date']['logicalType", "string", "date"),
            _changed("schema']['orders']['properties']['order_date']['description", "old desc", "new desc"),
        )
        rd = REPORT.build_report_data(diff)
        order_date_entries = [c for c in rd["summary"]["changes"] if c["path"] == "schema.orders.properties.order_date"]
        assert len(order_date_entries) == 1

    def test_summary_change_type_is_changed_when_field_both_added_and_removed(self):
        # Scalar Added + Removed on the same parent path collapse to Changed.
        # Use a 3-level path so rollup lands at schema.orders.properties.order_id
        diff = _merge(
            _added("schema']['orders']['properties']['order_id']['businessName", "Order ID"),
            _removed("schema']['orders']['properties']['order_id']['description", "Old desc"),
        )
        rd = REPORT.build_report_data(diff)
        match = next(c for c in rd["summary"]["changes"] if c["path"] == "schema.orders.properties.order_id")
        assert match["changeType"] == "Changed"

    def test_summary_counts_match_summary_changes(self):
        diff = _merge(
            _added("schema']['customers", {"physicalName": "c"}),
            _removed("schema']['orders']['properties']['customer_id", {"logicalType": "string"}),
            _changed("slaProperties']['availability']['value", "99.9%", "99.5%"),
        )
        rd = REPORT.build_report_data(diff)
        counts = rd["summary"]["counts"]
        changes = rd["summary"]["changes"]
        assert counts["added"] == sum(1 for c in changes if c["changeType"] == "Added")
        assert counts["removed"] == sum(1 for c in changes if c["changeType"] == "Removed")
        assert counts["changed"] == sum(1 for c in changes if c["changeType"] == "Changed")

    def test_detail_counts_match_detail_changes(self):
        diff = _merge(
            _added("schema']['customers", {"physicalName": "c"}),
            _changed("slaProperties']['availability']['value", "99.9%", "99.5%"),
        )
        rd = REPORT.build_report_data(diff)
        counts = rd["summary"]["counts"]
        changes = rd["summary"]["changes"]
        assert counts["added"] == sum(1 for c in changes if c["changeType"] == "Added")
        assert counts["changed"] == sum(1 for c in changes if c["changeType"] == "Changed")

    def test_detail_changes_sorted_by_path(self):
        diff = _merge(
            _added("schema']['orders", "v"),
            _added("schema']['customers", "v"),
        )
        rd = REPORT.build_report_data(diff)
        paths = [c["path"] for c in rd["detail"]["changes"]]
        assert paths == sorted(paths)


class TestGenerate:
    FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "diff", "unit")

    def _v1(self):
        return os.path.join(self.FIXTURE_DIR, "report_renderer_unit_v1.yaml")

    def _v2(self):
        return os.path.join(self.FIXTURE_DIR, "report_renderer_unit_v2.yaml")

    def test_text_format_written_to_stdout(self, capsys):
        ContractDiffReport().generate(self._v1(), self._v2(), fmt="text")
        out = capsys.readouterr().out
        assert "ODCS Data Contract Diff" in out
        assert "<html" not in out

    def test_html_format_written_to_stdout(self, capsys):
        ContractDiffReport().generate(self._v1(), self._v2(), fmt="html")
        out = capsys.readouterr().out
        assert "<!DOCTYPE html>" in out
        assert "ODCS Data Contract Diff" in out

    def test_output_path_writes_file(self, tmp_path):
        out_file = tmp_path / "report.txt"
        ContractDiffReport().generate(self._v1(), self._v2(), fmt="text", output_path=str(out_file))
        assert out_file.exists()
        assert "ODCS Data Contract Diff" in out_file.read_text()

    def test_output_path_nothing_to_stdout(self, tmp_path, capsys):
        out_file = tmp_path / "report.txt"
        ContractDiffReport().generate(self._v1(), self._v2(), fmt="text", output_path=str(out_file))
        assert capsys.readouterr().out == ""

    def test_html_written_to_file(self, tmp_path):
        out_file = tmp_path / "report.html"
        ContractDiffReport().generate(self._v1(), self._v2(), fmt="html", output_path=str(out_file))
        content = out_file.read_text()
        assert "<!DOCTYPE html>" in content
        assert "ODCS Data Contract Diff" in content

    def test_invalid_fmt_raises_value_error(self):
        with pytest.raises(ValueError, match="Invalid format"):
            ContractDiffReport().generate(self._v1(), self._v2(), fmt="pdf")

    def test_invalid_fmt_names_the_bad_value(self):
        with pytest.raises(ValueError, match="'xml'"):
            ContractDiffReport().generate(self._v1(), self._v2(), fmt="xml")

    def test_invalid_fmt_lists_valid_options(self):
        with pytest.raises(ValueError, match="text") as exc:
            ContractDiffReport().generate(self._v1(), self._v2(), fmt="csv")
        assert "html" in str(exc.value)

    def test_empty_fmt_raises_value_error(self):
        with pytest.raises(ValueError):
            ContractDiffReport().generate(self._v1(), self._v2(), fmt="")

    def test_missing_v1_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError, match="v1_path"):
            ContractDiffReport().generate("/nonexistent/v1.yaml", self._v2())

    def test_missing_v2_raises_file_not_found(self):
        with pytest.raises(FileNotFoundError, match="v2_path"):
            ContractDiffReport().generate(self._v1(), "/nonexistent/v2.yaml")

    def test_missing_file_error_includes_path(self):
        bad_path = "/nonexistent/contract.yaml"
        with pytest.raises(FileNotFoundError, match="contract.yaml"):
            ContractDiffReport().generate(bad_path, self._v2())

    def test_fmt_validated_before_file_io(self):
        with pytest.raises(ValueError):
            ContractDiffReport().generate("/nonexistent/v1.yaml", self._v2(), fmt="pdf")


class TestBuildReportDataTags:
    """Tags (list[str]) — added/removed tags should surface as path segments,
    not as new_value/old_value on the parent path."""

    def _tag_diff(self, v1_tags, v2_tags, location="top"):
        """Build report_data from a synthetic tags diff at the given location."""
        if location == "top":
            v1 = {"apiVersion": "v3.0.2", "kind": "DataContract", "id": "t", "tags": v1_tags}
            v2 = {"apiVersion": "v3.0.2", "kind": "DataContract", "id": "t", "tags": v2_tags}
        elif location == "schema":
            v1 = {
                "apiVersion": "v3.0.2",
                "kind": "DataContract",
                "id": "t",
                "schema": [{"name": "orders", "physicalName": "orders_tbl", "tags": v1_tags}],
            }
            v2 = {
                "apiVersion": "v3.0.2",
                "kind": "DataContract",
                "id": "t",
                "schema": [{"name": "orders", "physicalName": "orders_tbl", "tags": v2_tags}],
            }
        else:
            v1 = {
                "apiVersion": "v3.0.2",
                "kind": "DataContract",
                "id": "t",
                "schema": [
                    {
                        "name": "orders",
                        "physicalName": "orders_tbl",
                        "properties": [{"name": "order_id", "logicalType": "string", "tags": v1_tags}],
                    }
                ],
            }
            v2 = {
                "apiVersion": "v3.0.2",
                "kind": "DataContract",
                "id": "t",
                "schema": [
                    {
                        "name": "orders",
                        "physicalName": "orders_tbl",
                        "properties": [{"name": "order_id", "logicalType": "string", "tags": v2_tags}],
                    }
                ],
            }
        from datacontract.reports.diff.diff import ContractDiff

        raw = ContractDiff()._diff(v1, v2)
        return ContractDiffReport().build_report_data(raw)

    def test_added_tag_path_includes_tag_value(self):
        rd = self._tag_diff(["analytics"], ["analytics", "pii"])
        paths = [c["path"] for c in rd["detail"]["changes"]]
        assert "tags.pii" in paths

    def test_removed_tag_path_includes_tag_value(self):
        rd = self._tag_diff(["analytics", "pii"], ["analytics"])
        paths = [c["path"] for c in rd["detail"]["changes"]]
        assert "tags.pii" in paths

    def test_added_tag_has_no_new_value_field(self):
        rd = self._tag_diff(["analytics"], ["analytics", "pii"])
        tag_change = next(c for c in rd["detail"]["changes"] if c["path"] == "tags.pii")
        assert "new_value" not in tag_change
        assert "old_value" not in tag_change

    def test_added_tag_change_type_is_added(self):
        rd = self._tag_diff(["analytics"], ["analytics", "pii"])
        tag_change = next(c for c in rd["detail"]["changes"] if c["path"] == "tags.pii")
        assert tag_change["changeType"] == "Added"

    def test_removed_tag_change_type_is_removed(self):
        rd = self._tag_diff(["analytics", "pii"], ["analytics"])
        tag_change = next(c for c in rd["detail"]["changes"] if c["path"] == "tags.pii")
        assert tag_change["changeType"] == "Removed"

    def test_summary_rolls_up_to_tags_parent(self):
        rd = self._tag_diff(["analytics"], ["analytics", "pii", "transactions"])
        summary_paths = [c["path"] for c in rd["summary"]["changes"]]
        assert "tags" in summary_paths
        assert "tags.pii" not in summary_paths
        assert "tags.transactions" not in summary_paths

    def test_schema_object_tag_uses_value_as_path_segment(self):
        rd = self._tag_diff(["e-commerce"], ["e-commerce", "reporting"], location="schema")
        paths = [c["path"] for c in rd["detail"]["changes"]]
        assert "schema.orders.tags.reporting" in paths

    def test_schema_property_tag_uses_value_as_path_segment(self):
        rd = self._tag_diff(["primary-key"], ["primary-key", "required"], location="property")
        paths = [c["path"] for c in rd["detail"]["changes"]]
        assert "schema.orders.properties.order_id.tags.required" in paths

    def test_unchanged_tags_produce_no_diff(self):
        rd = self._tag_diff(["analytics", "pii"], ["analytics", "pii"])
        assert rd["detail"]["changes"] == []

    def test_reordered_tags_produce_no_diff(self):
        rd = self._tag_diff(["analytics", "pii"], ["pii", "analytics"])
        assert rd["detail"]["changes"] == []


class TestSummaryRollupScalarLeaves:
    """Scalar Added/Removed leaf fields roll up to their parent in the summary,
    consistent with how scalar Changed fields behave."""

    def _rd(self, *diffs):
        return REPORT.build_report_data(_merge(*diffs))

    def test_scalar_added_rolls_up_to_parent(self):
        rd = self._rd(_added("schema']['orders']['businessName", "Orders"))
        paths = [c["path"] for c in rd["summary"]["changes"]]
        assert "schema.orders" in paths
        assert "schema.orders.businessName" not in paths

    def test_scalar_removed_rolls_up_to_parent(self):
        rd = self._rd(_removed("schema']['orders']['description", "old desc"))
        paths = [c["path"] for c in rd["summary"]["changes"]]
        assert "schema.orders" in paths
        assert "schema.orders.description" not in paths

    def test_scalar_added_parent_change_type_is_added(self):
        rd = self._rd(_added("schema']['orders']['businessName", "Orders"))
        match = next(c for c in rd["summary"]["changes"] if c["path"] == "schema.orders")
        assert match["changeType"] == "Added"

    def test_scalar_removed_parent_change_type_is_removed(self):
        rd = self._rd(_removed("schema']['orders']['description", "old"))
        match = next(c for c in rd["summary"]["changes"] if c["path"] == "schema.orders")
        assert match["changeType"] == "Removed"

    def test_mixed_add_remove_same_parent_collapses_to_changed(self):
        rd = self._rd(
            _added("schema']['orders']['businessName", "Orders"),
            _removed("schema']['orders']['description", "old desc"),
        )
        match = next(c for c in rd["summary"]["changes"] if c["path"] == "schema.orders")
        assert match["changeType"] == "Changed"
        paths = [c["path"] for c in rd["summary"]["changes"]]
        assert "schema.orders.businessName" not in paths
        assert "schema.orders.description" not in paths

    def test_mixed_add_scalar_changed_same_parent_collapses_to_changed(self):
        rd = self._rd(
            _added("schema']['orders']['businessName", "Orders"),
            _changed("schema']['orders']['logicalType", "string", "integer"),
        )
        match = next(c for c in rd["summary"]["changes"] if c["path"] == "schema.orders")
        assert match["changeType"] == "Changed"

    def test_dict_added_does_not_roll_up(self):
        """A whole dict payload (e.g. a new schema object) should not roll up —
        only scalar leafs do."""
        rd = self._rd(_added("schema']['customers", {"physicalName": "customers_tbl"}))
        paths = [c["path"] for c in rd["summary"]["changes"]]
        assert "schema.customers" in paths
        assert "schema" not in paths

    def test_top_level_scalar_added_stays_at_top_level(self):
        """A scalar at depth 1 (e.g. root['version']) has no parent to roll up to."""
        rd = self._rd(_added("version", "2.0.0"))
        paths = [c["path"] for c in rd["summary"]["changes"]]
        assert "version" in paths

    def test_summary_counts_consistent_after_rollup(self):
        rd = self._rd(
            _added("schema']['orders']['businessName", "Orders"),
            _removed("schema']['orders']['description", "old"),
        )
        counts = rd["summary"]["counts"]
        changes = rd["summary"]["changes"]
        assert counts["added"] == sum(1 for c in changes if c["changeType"] == "Added")
        assert counts["removed"] == sum(1 for c in changes if c["changeType"] == "Removed")
        assert counts["changed"] == sum(1 for c in changes if c["changeType"] == "Changed")

    def test_detail_still_shows_full_leaf_paths(self):
        """Rollup only affects summary — detail must still show the full leaf paths."""
        rd = self._rd(
            _added("schema']['orders']['businessName", "Orders"),
            _removed("schema']['orders']['description", "old desc"),
        )
        detail_paths = [c["path"] for c in rd["detail"]["changes"]]
        assert "schema.orders.businessName" in detail_paths
        assert "schema.orders.description" in detail_paths
