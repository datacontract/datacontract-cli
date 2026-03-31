"""
test_reports_common_helpers — Unit tests for datacontract.reports.common.report_helpers
---------------------------------------------------------------------------------------------
Covers every public symbol in report_helpers.py:

    LIST_CONTAINERS  — the frozenset of ODCS container keys, derived from the
                       ODCS Pydantic models automatically
    _flatten_value() — recursive dict → [(label, str_value)] flattener

Test classes:
    TestListContainers  — shape and content of LIST_CONTAINERS
    TestFlattenValue    — _flatten_value() with flat, nested, and edge-case inputs
"""

from __future__ import annotations

from datacontract.reports.common.report_helpers import (
    LIST_CONTAINERS,
    _flatten_value,
)


class TestListContainers:
    def test_is_a_frozenset(self):
        assert isinstance(LIST_CONTAINERS, frozenset)

    def test_schema_present(self):
        assert "schema" in LIST_CONTAINERS

    def test_sla_properties_present(self):
        assert "slaProperties" in LIST_CONTAINERS

    def test_servers_present(self):
        assert "servers" in LIST_CONTAINERS

    def test_properties_present(self):
        assert "properties" in LIST_CONTAINERS

    def test_quality_present(self):
        assert "quality" in LIST_CONTAINERS

    def test_roles_present(self):
        assert "roles" in LIST_CONTAINERS

    def test_support_present(self):
        assert "support" in LIST_CONTAINERS

    def test_custom_properties_present(self):
        assert "customProperties" in LIST_CONTAINERS

    def test_members_present(self):
        assert "members" in LIST_CONTAINERS

    def test_authoritative_definitions_present(self):
        assert "authoritativeDefinitions" in LIST_CONTAINERS

    def test_relationships_present(self):
        assert "relationships" in LIST_CONTAINERS

    def test_team_present(self):
        assert "team" in LIST_CONTAINERS

    def test_no_empty_strings(self):
        assert "" not in LIST_CONTAINERS

    def test_all_strings(self):
        assert all(isinstance(k, str) for k in LIST_CONTAINERS)

    def test_non_odcs_key_absent(self):
        assert "fooBarBaz" not in LIST_CONTAINERS


class TestFlattenValue:
    # ── basic shapes ──────────────────────────────────────────────────────

    def test_flat_dict_returns_key_value_pairs(self):
        result = _flatten_value({"a": 1, "b": 2})
        assert ("a", "1") in result
        assert ("b", "2") in result

    def test_flat_dict_all_values_are_strings(self):
        result = _flatten_value({"x": 42, "y": True, "z": 3.14})
        assert all(isinstance(v, str) for _, v in result)

    def test_flat_dict_label_is_key(self):
        result = _flatten_value({"myKey": "myVal"})
        assert result == [("myKey", "myVal")]

    def test_non_dict_scalar_returns_empty(self):
        assert _flatten_value("string") == []
        assert _flatten_value(42) == []
        assert _flatten_value(True) == []
        assert _flatten_value(3.14) == []
        assert _flatten_value(None) == []

    def test_empty_dict_returns_empty(self):
        assert _flatten_value({}) == []

    # ── nesting ───────────────────────────────────────────────────────────

    def test_nested_dict_uses_dot_separator(self):
        result = _flatten_value({"outer": {"inner": "val"}})
        assert ("outer.inner", "val") in result

    def test_deeply_nested_dict(self):
        result = _flatten_value({"a": {"b": {"c": "deep"}}})
        assert ("a.b.c", "deep") in result

    def test_mixed_nested_and_flat(self):
        result = _flatten_value({"flat": "x", "nested": {"child": "y"}})
        assert ("flat", "x") in result
        assert ("nested.child", "y") in result

    def test_nested_parent_not_emitted_as_leaf(self):
        # The intermediate "outer" key should not appear as a standalone entry
        result = _flatten_value({"outer": {"inner": "val"}})
        labels = [lbl for lbl, _ in result]
        assert "outer" not in labels

    # ── prefix argument ───────────────────────────────────────────────────

    def test_prefix_prepended_to_all_labels(self):
        result = _flatten_value({"key": "val"}, prefix="root.")
        assert ("root.key", "val") in result

    def test_prefix_with_nested(self):
        result = _flatten_value({"a": {"b": "v"}}, prefix="top.")
        assert ("top.a.b", "v") in result

    # ── value coercion ────────────────────────────────────────────────────

    def test_integer_value_stringified(self):
        result = _flatten_value({"n": 99})
        assert ("n", "99") in result

    def test_bool_value_stringified(self):
        result = _flatten_value({"flag": False})
        assert ("flag", "False") in result

    def test_none_value_stringified(self):
        result = _flatten_value({"k": None})
        assert ("k", "None") in result

    # ── order ─────────────────────────────────────────────────────────────

    def test_flat_dict_preserves_insertion_order(self):
        result = _flatten_value({"z": "1", "a": "2", "m": "3"})
        assert [lbl for lbl, _ in result] == ["z", "a", "m"]
