"""
test_html_report_renderer — Unit tests for HtmlContractDiffRenderer
------------------------------------------------------------------
Test classes:
    TestHtmlEscape       — e(): HTML escaping
    TestFormatValue      — format_value(): dict summary, truncation, escaping
    TestRenderDetailRows — _render_detail_rows(): ancestor inference, sorting, values
"""

from datacontract.reports.diff.html_contract_diff_renderer import (
    _render_detail_rows,
    e,
    format_value,
    path_td,
    pill,
)


class TestHtmlEscape:
    def test_escapes_angle_brackets(self):
        assert e("<b>") == "&lt;b&gt;"

    def test_escapes_ampersand(self):
        assert e("a & b") == "a &amp; b"

    def test_passes_plain_string(self):
        assert e("hello") == "hello"

    def test_converts_non_string(self):
        assert e(42) == "42"


class TestFormatValue:
    def test_none_returns_empty(self):
        assert format_value(None) == ""

    def test_plain_string(self):
        assert format_value("hello") == "hello"

    def test_dict_shows_key_summary(self):
        result = format_value({"a": 1, "b": 2})
        assert result == '<span class="obj">{ a, b }</span>'
        assert "b" in result
        assert "obj" in result  # CSS class

    def test_dict_with_more_than_4_keys_truncates(self):
        result = format_value({"a": 1, "b": 2, "c": 3, "d": 4, "e": 5})
        assert "..." in result

    def test_long_string_not_truncated(self):
        long = "x" * 200
        result = format_value(long)
        assert "…" not in result
        assert len(result) == 200

    def test_html_escapes_value(self):
        result = format_value("<script>")
        assert "&lt;script&gt;" in result


class TestPill:
    def test_added(self):
        result = pill("added")
        assert "Added" in result
        assert 'class="pill added"' in result

    def test_removed(self):
        result = pill("removed")
        assert "Removed" in result
        assert 'class="pill removed"' in result

    def test_changed(self):
        result = pill("changed")
        assert "Changed" in result
        assert 'class="pill changed"' in result

    def test_unknown_type_capitalised(self):
        result = pill("deprecated")
        assert "Deprecated" in result


class TestPathTd:
    def test_depth_zero_no_indent(self):
        result = path_td("field", 0, False)
        assert "padding-left:calc(14px + 0ch)" in result

    def test_depth_adds_padding(self):
        result = path_td("orders", 2, False)
        assert "4ch" in result

    def test_list_item_prefix(self):
        result = path_td("orders", 1, True)
        assert "- orders" in result

    def test_non_list_item_no_prefix(self):
        result = path_td("orders", 1, False)
        assert "- " not in result


class TestRenderDetailRows:
    def test_empty_changes(self):
        assert _render_detail_rows([]) == []

    def test_single_added_row(self):
        rows = _render_detail_rows([{"path": "schema.orders", "changeType": "Added"}])
        assert any("orders" in r for r in rows)
        assert any("Added" in r for r in rows)

    def test_ancestor_rows_inferred(self):
        rows = _render_detail_rows(
            [
                {
                    "path": "schema.orders.properties.amount",
                    "changeType": "Added",
                }
            ]
        )
        combined = "\n".join(rows)
        assert "schema" in combined
        assert "orders" in combined
        assert "amount" in combined

    def test_list_item_prefix_for_list_container_children(self):
        rows = _render_detail_rows([{"path": "schema.orders", "changeType": "Added"}])
        assert any("- orders" in r for r in rows)

    def test_changed_row_includes_old_and_new(self):
        rows = _render_detail_rows(
            [
                {
                    "path": "slaProperties.availability.value",
                    "changeType": "Changed",
                    "old_value": "99.9%",
                    "new_value": "99.5%",
                }
            ]
        )
        combined = "\n".join(rows)
        assert "99.9%" in combined
        assert "99.5%" in combined

    def test_rows_sorted_by_path(self):
        rows = _render_detail_rows(
            [
                {"path": "schema.orders", "changeType": "Removed"},
                {"path": "schema.customers", "changeType": "Added"},
            ]
        )
        combined = "\n".join(rows)
        assert combined.index("customers") < combined.index("orders")


