"""
test_text_report_renderer — Unit tests for TextContractDiffRenderer
------------------------------------------------------------------
Test classes:
    TestRender       — render(): header, sections, no-changes path
    TestBadges       — _badges(): count formatting and ordering
    TestValStrs      — _val_strs(): scalar, dict, mixed, absent values
    TestSummaryTable — _summary_table(): column headers, rows, width
    TestDetailTable  — _detail_table(): ancestor inference, indentation, truncation
"""

from datacontract.reports.diff.text_contract_diff_renderer import TextContractDiffRenderer

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _report_data(
    summary_changes=None,
    detail_changes=None,
    summary_counts=None,
    detail_counts=None,
    source_label="v1.yaml",
    target_label="v2.yaml",
):
    summary_changes = summary_changes or []
    detail_changes = detail_changes or []

    def _counts(changes):
        return {
            "added": sum(1 for c in changes if c.get("changeType") == "Added"),
            "removed": sum(1 for c in changes if c.get("changeType") == "Removed"),
            "changed": sum(1 for c in changes if c.get("changeType") == "Changed"),
        }

    return {
        "source_label": source_label,
        "target_label": target_label,
        "header": {
            "title": "ODCS Data Contract Diff",
            "subtitle": f"{source_label} → {target_label}",
        },
        "summary": {
            "counts": summary_counts or _counts(summary_changes),
            "changes": summary_changes,
        },
        "detail": {
            "counts": detail_counts or _counts(detail_changes),
            "changes": detail_changes,
        },
    }


RENDERER = TextContractDiffRenderer


# ---------------------------------------------------------------------------
# render — top-level
# ---------------------------------------------------------------------------


class TestRender:
    def test_no_changes_returns_no_changes_message(self):
        result = RENDERER(_report_data()).render()
        assert result == "No changes detected."

    def test_contains_header_title(self):
        rd = _report_data(summary_changes=[{"path": "schema.orders", "changeType": "Added"}])
        result = RENDERER(rd).render()
        assert "ODCS Data Contract Diff" in result

    def test_contains_subtitle_with_labels(self):
        rd = _report_data(
            summary_changes=[{"path": "schema.orders", "changeType": "Added"}],
            source_label="before.yaml",
            target_label="after.yaml",
        )
        result = RENDERER(rd).render()
        assert "before.yaml" in result
        assert "after.yaml" in result

    def test_contains_change_summary_section(self):
        rd = _report_data(summary_changes=[{"path": "schema.orders", "changeType": "Added"}])
        result = RENDERER(rd).render()
        assert "CHANGE SUMMARY" in result

    def test_contains_change_details_section(self):
        rd = _report_data(
            summary_changes=[{"path": "schema.orders", "changeType": "Added"}],
            detail_changes=[{"path": "schema.orders", "changeType": "Added"}],
        )
        result = RENDERER(rd).render()
        assert "CHANGE DETAILS" in result

    def test_header_framed_by_equals(self):
        rd = _report_data(summary_changes=[{"path": "schema.orders", "changeType": "Added"}])
        lines = RENDERER(rd).render().splitlines()
        assert lines[0] == "=" * 100
        assert lines[5] == "=" * 100  # Updated due to blank lines after title and before timestamp

    def test_total_count_shown_in_summary_header(self):
        rd = _report_data(
            summary_changes=[
                {"path": "schema.orders", "changeType": "Added"},
                {"path": "schema.customers", "changeType": "Removed"},
            ]
        )
        result = RENDERER(rd).render()
        assert "2 change(s)" in result



class TestBadges:
    def _renderer(self):
        return RENDERER(_report_data())

    def test_removed_badge(self):
        result = self._renderer()._badges({"removed": 2, "changed": 0, "added": 0})
        assert "2 Removed" in result

    def test_changed_badge(self):
        result = self._renderer()._badges({"removed": 0, "changed": 3, "added": 0})
        assert "3 Changed" in result

    def test_added_badge(self):
        result = self._renderer()._badges({"removed": 0, "changed": 0, "added": 1})
        assert "1 Added" in result

    def test_zero_counts_omitted(self):
        result = self._renderer()._badges({"removed": 0, "changed": 0, "added": 0})
        assert result == ""

    def test_multiple_badges_all_present(self):
        result = self._renderer()._badges({"removed": 1, "changed": 2, "added": 3})
        assert "Removed" in result
        assert "Changed" in result
        assert "Added" in result

    def test_order_is_removed_changed_added(self):
        result = self._renderer()._badges({"removed": 1, "changed": 1, "added": 1})
        assert result.index("Removed") < result.index("Changed") < result.index("Added")


class TestValStrs:
    def _renderer(self):
        return RENDERER(_report_data())

    def test_scalar_values(self):
        new_str, old_str = self._renderer()._val_strs(
            {"changeType": "Changed", "new_value": "date", "old_value": "string"}
        )
        assert new_str == "date"
        assert old_str == "string"

    def test_absent_values_return_empty_strings(self):
        new_str, old_str = self._renderer()._val_strs({"changeType": "Added"})
        assert new_str == ""
        assert old_str == ""

    def test_added_has_new_only(self):
        new_str, old_str = self._renderer()._val_strs({"changeType": "Added", "new_value": "customers_tbl"})
        assert new_str == "customers_tbl"
        assert old_str == ""

    def test_removed_has_old_only(self):
        new_str, old_str = self._renderer()._val_strs({"changeType": "Removed", "old_value": "orders_tbl"})
        assert new_str == ""
        assert old_str == "orders_tbl"

    def test_dict_value_flattened_to_key_value_pairs(self):
        new_str, old_str = self._renderer()._val_strs(
            {
                "changeType": "Added",
                "new_value": {"logicalType": "string", "required": True},
            }
        )
        assert "logicalType: string" in new_str
        assert "required: True" in new_str

    def test_dict_old_value_flattened(self):
        new_str, old_str = self._renderer()._val_strs(
            {
                "changeType": "Removed",
                "old_value": {"logicalType": "string"},
            }
        )
        assert "logicalType: string" in old_str

    def test_dict_old_scalar_new_not_lost(self):
        new_str, old_str = self._renderer()._val_strs(
            {
                "changeType": "Changed",
                "old_value": {"a": 1},
                "new_value": "hello",
            }
        )
        assert new_str == "hello"
        assert "a: 1" in old_str

    def test_scalar_old_dict_new_not_lost(self):
        new_str, old_str = self._renderer()._val_strs(
            {
                "changeType": "Changed",
                "old_value": "hello",
                "new_value": {"a": 1},
            }
        )
        assert old_str == "hello"
        assert "a: 1" in new_str


class TestSummaryTable:
    def _renderer(self):
        return RENDERER(_report_data())

    def test_header_row_contains_field_and_change(self):
        rows = self._renderer()._summary_table(
            [
                {"path": "schema.orders", "changeType": "Added"},
            ]
        )
        assert "Field" in rows[0]
        assert "Change" in rows[0]

    def test_separator_row_present(self):
        rows = self._renderer()._summary_table(
            [
                {"path": "schema.orders", "changeType": "Added"},
            ]
        )
        assert set(rows[1]) <= {"-", " "}

    def test_change_path_and_type_in_row(self):
        rows = self._renderer()._summary_table(
            [
                {"path": "schema.orders", "changeType": "Removed"},
            ]
        )
        data_rows = rows[2:]
        assert any("schema.orders" in r for r in data_rows)
        assert any("Removed" in r for r in data_rows)

    def test_multiple_changes_produce_multiple_rows(self):
        rows = self._renderer()._summary_table(
            [
                {"path": "schema.orders", "changeType": "Removed"},
                {"path": "schema.customers", "changeType": "Added"},
            ]
        )
        data_rows = rows[2:]
        assert len(data_rows) == 2


class TestDetailTable:
    def _renderer(self):
        return RENDERER(_report_data())

    def test_header_row_contains_all_columns(self):
        rows = self._renderer()._detail_table(
            [
                {"path": "schema.orders", "changeType": "Added"},
            ]
        )
        assert "Field" in rows[0]
        assert "Change" in rows[0]
        assert "New" in rows[0]
        assert "Old" in rows[0]

    def test_ancestor_rows_inferred(self):
        rows = self._renderer()._detail_table(
            [
                {"path": "schema.orders.properties.amount", "changeType": "Added"},
            ]
        )
        combined = "\n".join(rows)
        assert "schema" in combined
        assert "orders" in combined
        assert "amount" in combined

    def test_list_item_prefix_for_list_container_children(self):
        rows = self._renderer()._detail_table(
            [
                {"path": "schema.orders", "changeType": "Added"},
            ]
        )
        assert any("- orders" in r for r in rows)

    def test_changed_row_includes_old_and_new(self):
        rows = self._renderer()._detail_table(
            [
                {
                    "path": "slaProperties.availability.value",
                    "changeType": "Changed",
                    "old_value": "99.9%",
                    "new_value": "99.5%",
                },
            ]
        )
        combined = "\n".join(rows)
        assert "99.9%" in combined
        assert "99.5%" in combined

    def test_long_values_wrapped(self):
        long_val = "x" * 100
        rows = self._renderer()._detail_table(
            [
                {"path": "schema.orders.description", "changeType": "Added", "new_value": long_val},
            ],
            val_w=20,
        )
        combined = "\n".join(rows)
        # Should be wrapped across multiple lines, not truncated
        assert len(combined.split("\n")) > 2  # Header + delimiter + at least 2 content lines

    def test_ancestor_row_has_no_change_type(self):
        rows = self._renderer()._detail_table(
            [
                {"path": "schema.orders.properties.amount", "changeType": "Added", "new_value": "1"},
            ]
        )
        ancestor_rows = [r for r in rows if r.strip() in ("schema", "  - orders", "    properties")]
        for r in ancestor_rows:
            assert "Added" not in r
            assert "Removed" not in r
            assert "Changed" not in r


