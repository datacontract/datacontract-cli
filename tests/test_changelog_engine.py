"""
test_changelog_engine — Unit tests for changelog.py
-------------------------------------------------------------------
Test classes:
    TestBuildReportDataStructure          — _build_changelog_from_diff() output shape and empty-diff
    TestBuildReportDataAdded              — Added change entries (scalar and dict payloads)
    TestBuildReportDataRemoved            — Removed change entries
    TestBuildReportDataChanged            — Changed entries and scalar rollup to parent
    TestBuildReportDataSummaryRollup      — summary deduplication and count consistency
    TestBuildReportDataTags               — tag field changes
    TestSummaryRollupScalarLeaves         — scalar leaf rollup behaviour
    TestDiff                              — diff(): semantic correctness (added/removed/changed/mid-list)
    TestDiffFixtures                      — diff(): end-to-end using fixtures/changelog/unit/
    TestDiffFixturesPriceDescriptionScalars — diff(): price, description, and top-level scalar fields
    TestBuildChangelog                    — build_changelog() with OpenDataContractStandard objects
"""

import os
import tempfile

import yaml
from open_data_contract_standard.model import OpenDataContractStandard

from datacontract.changelog.changelog import _build_changelog_from_diff, build_changelog, diff

REPORT = _build_changelog_from_diff


def _added(path: str, payload) -> dict:
    return {"dictionary_item_added": {f"root['{path}']": payload}}


def _added_double_quotes(path: str, payload) -> dict:
    return {"dictionary_item_added": {f'root["{path}"]': payload}}


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
        rd = _build_changelog_from_diff({})
        assert set(rd.keys()) == {"source_label", "target_label", "header", "summary", "detail"}

    def test_header_contains_title_and_subtitle(self):
        rd = _build_changelog_from_diff({}, source_label="v1.yaml", target_label="v2.yaml")
        assert rd["header"]["title"] == "ODCS Data Contract Changelog"
        assert "v1.yaml" in rd["header"]["subtitle"]
        assert "v2.yaml" in rd["header"]["subtitle"]

    def test_source_and_target_labels_stored(self):
        rd = _build_changelog_from_diff({}, source_label="before.yaml", target_label="after.yaml")
        assert rd["source_label"] == "before.yaml"
        assert rd["target_label"] == "after.yaml"

    def test_empty_diff_produces_zero_counts(self):
        rd = _build_changelog_from_diff({})
        assert rd["summary"]["counts"] == {"added": 0, "removed": 0, "updated": 0}
        assert rd["detail"]["counts"] == {"added": 0, "removed": 0, "updated": 0}

    def test_empty_diff_produces_empty_changes(self):
        rd = _build_changelog_from_diff({})
        assert rd["summary"]["changes"] == []
        assert rd["detail"]["changes"] == []

    def test_unknown_deepdiff_keys_ignored(self):
        rd = _build_changelog_from_diff({"unknown_key": {"root['x']": 1}})
        assert rd["summary"]["changes"] == []


class TestBuildReportDataAdded:
    def test_added_scalar_appears_in_detail(self):
        rd = _build_changelog_from_diff(_added("schema']['orders", "v"))
        paths = [c["path"] for c in rd["detail"]["changes"]]
        assert any("orders" in p for p in paths)

    def test_added_scalar_change_type(self):
        rd = _build_changelog_from_diff(_added("schema']['orders", "val"))
        match = next(c for c in rd["detail"]["changes"] if "orders" in c["path"])
        assert match["changeType"] == "Added"

    def test_added_scalar_has_new_value(self):
        rd = _build_changelog_from_diff(_added("schema']['orders", "val"))
        match = next(c for c in rd["detail"]["changes"] if c["path"] == "schema.orders")
        assert match.get("new_value") == "val"

    def test_added_dict_expands_to_leaf_entries(self):
        payload = {"physicalName": "orders_tbl", "description": "Orders"}
        rd = _build_changelog_from_diff(_added("schema']['orders", payload))
        paths = [c["path"] for c in rd["detail"]["changes"]]
        assert "schema.orders.physicalName" in paths
        assert "schema.orders.description" in paths

    def test_added_dict_parent_entry_included(self):
        payload = {"physicalName": "orders_tbl"}
        rd = _build_changelog_from_diff(_added("schema']['orders", payload))
        paths = [c["path"] for c in rd["detail"]["changes"]]
        assert "schema.orders" in paths

    def test_added_count_incremented(self):
        rd = _build_changelog_from_diff(_added("schema']['orders", "v"))
        assert rd["detail"]["counts"]["added"] >= 1

    def test_added_appears_in_summary(self):
        # Scalar Added rolls up to parent — use a 2-level path so it lands at schema.orders
        rd = _build_changelog_from_diff(_added("schema']['orders']['physicalName", "v"))
        paths = [c["path"] for c in rd["summary"]["changes"]]
        assert any("orders" in p for p in paths)

    def test_added_double_quotes_path_parsing(self):
        """Test that double-quoted paths are parsed correctly in both detail and summary"""
        rd = _build_changelog_from_diff(_added_double_quotes('schema"]["orders"]["physicalName', "v"))
        detail_paths = [c["path"] for c in rd["detail"]["changes"]]
        assert "schema.orders.physicalName" in detail_paths
        summary_paths = [c["path"] for c in rd["summary"]["changes"]]
        assert any("orders" in p for p in summary_paths)


class TestBuildReportDataRemoved:
    def test_removed_scalar_appears_in_detail(self):
        rd = _build_changelog_from_diff(_removed("schema']['orders", "v"))
        paths = [c["path"] for c in rd["detail"]["changes"]]
        assert any("orders" in p for p in paths)

    def test_removed_scalar_has_old_value(self):
        rd = _build_changelog_from_diff(_removed("schema']['orders", "val"))
        match = next(c for c in rd["detail"]["changes"] if c["path"] == "schema.orders")
        assert match.get("old_value") == "val"

    def test_removed_dict_expands_to_leaf_entries(self):
        payload = {"logicalType": "string", "required": True}
        rd = _build_changelog_from_diff(_removed("schema']['orders']['properties']['amount", payload))
        paths = [c["path"] for c in rd["detail"]["changes"]]
        assert "schema.orders.properties.amount.logicalType" in paths

    def test_removed_count_incremented(self):
        rd = _build_changelog_from_diff(_removed("schema']['orders", "v"))
        assert rd["detail"]["counts"]["removed"] >= 1


class TestBuildReportDataChanged:
    def test_changed_scalar_in_detail(self):
        rd = _build_changelog_from_diff(
            _changed("schema']['orders']['properties']['order_date']['logicalType", "string", "date")
        )
        match = next((c for c in rd["detail"]["changes"] if "logicalType" in c["path"]), None)
        assert match is not None
        assert match["changeType"] == "Updated"
        assert match["old_value"] == "string"
        assert match["new_value"] == "date"

    def test_changed_count_incremented(self):
        rd = _build_changelog_from_diff(_changed("slaProperties']['availability']['value", "99.9%", "99.5%"))
        assert rd["detail"]["counts"]["updated"] == 1

    def test_changed_scalar_rolled_up_to_parent_in_summary(self):
        rd = _build_changelog_from_diff(
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
        rd = _build_changelog_from_diff(diff)
        order_date_entries = [c for c in rd["summary"]["changes"] if c["path"] == "schema.orders.properties.order_date"]
        assert len(order_date_entries) == 1

    def test_summary_change_type_is_changed_when_field_both_added_and_removed(self):
        # Scalar Added + Removed on the same parent path collapse to Changed.
        # Use a 3-level path so rollup lands at schema.orders.properties.order_id
        diff = _merge(
            _added("schema']['orders']['properties']['order_id']['businessName", "Order ID"),
            _removed("schema']['orders']['properties']['order_id']['description", "Old desc"),
        )
        rd = _build_changelog_from_diff(diff)
        match = next(c for c in rd["summary"]["changes"] if c["path"] == "schema.orders.properties.order_id")
        assert match["changeType"] == "Updated"

    def test_summary_counts_match_summary_changes(self):
        diff = _merge(
            _added("schema']['customers", {"physicalName": "c"}),
            _removed("schema']['orders']['properties']['customer_id", {"logicalType": "string"}),
            _changed("slaProperties']['availability']['value", "99.9%", "99.5%"),
        )
        rd = _build_changelog_from_diff(diff)
        counts = rd["summary"]["counts"]
        changes = rd["summary"]["changes"]
        assert counts["added"] == sum(1 for c in changes if c["changeType"] == "Added")
        assert counts["removed"] == sum(1 for c in changes if c["changeType"] == "Removed")
        assert counts["updated"] == sum(1 for c in changes if c["changeType"] == "Updated")

    def test_detail_counts_match_detail_changes(self):
        diff = _merge(
            _added("schema']['customers", {"physicalName": "c"}),
            _changed("slaProperties']['availability']['value", "99.9%", "99.5%"),
        )
        rd = _build_changelog_from_diff(diff)
        counts = rd["summary"]["counts"]
        changes = rd["summary"]["changes"]
        assert counts["added"] == sum(1 for c in changes if c["changeType"] == "Added")
        assert counts["updated"] == sum(1 for c in changes if c["changeType"] == "Updated")

    def test_detail_changes_sorted_by_path(self):
        diff = _merge(
            _added("schema']['orders", "v"),
            _added("schema']['customers", "v"),
        )
        rd = _build_changelog_from_diff(diff)
        paths = [c["path"] for c in rd["detail"]["changes"]]
        assert paths == sorted(paths)


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
        from datacontract.changelog.changelog import diff

        raw = diff(v1, v2)
        return _build_changelog_from_diff(raw)

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
        return _build_changelog_from_diff(_merge(*diffs))

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

    def test_mixed_add_remove_same_parent_collapses_to_updated(self):
        rd = self._rd(
            _added("schema']['orders']['businessName", "Orders"),
            _removed("schema']['orders']['description", "old desc"),
        )
        match = next(c for c in rd["summary"]["changes"] if c["path"] == "schema.orders")
        assert match["changeType"] == "Updated"
        paths = [c["path"] for c in rd["summary"]["changes"]]
        assert "schema.orders.businessName" not in paths
        assert "schema.orders.description" not in paths

    def test_mixed_add_scalar_changed_same_parent_collapses_to_updated(self):
        rd = self._rd(
            _added("schema']['orders']['businessName", "Orders"),
            _changed("schema']['orders']['logicalType", "string", "integer"),
        )
        match = next(c for c in rd["summary"]["changes"] if c["path"] == "schema.orders")
        assert match["changeType"] == "Updated"

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
        assert counts["updated"] == sum(1 for c in changes if c["changeType"] == "Updated")

    def test_detail_still_shows_full_leaf_paths(self):
        """Rollup only affects summary — detail must still show the full leaf paths."""
        rd = self._rd(
            _added("schema']['orders']['businessName", "Orders"),
            _removed("schema']['orders']['description", "old desc"),
        )
        detail_paths = [c["path"] for c in rd["detail"]["changes"]]
        assert "schema.orders.businessName" in detail_paths
        assert "schema.orders.description" in detail_paths


# ---------------------------------------------------------------------------
# Helpers for diff() tests
# ---------------------------------------------------------------------------

MINIMAL_CONTRACT = {
    "apiVersion": "v3.0.2",
    "kind": "DataContract",
    "id": "test-001",
}


def _load_contract(path: str) -> dict:
    with open(path, encoding="utf-8") as f:
        raw = yaml.safe_load(f)
    return OpenDataContractStandard.model_validate(raw).model_dump(exclude_none=True, by_alias=True)


def _write_yaml(data: dict, path: str) -> None:
    with open(path, "w") as f:
        yaml.dump(data, f)


def _contract(**kwargs) -> dict:
    return {**MINIMAL_CONTRACT, **kwargs}


class TestDiff:
    def _base(self) -> dict:
        return _contract(
            schema=[
                {
                    "name": "orders",
                    "properties": [
                        {"name": "order_id", "logicalType": "string", "required": True},
                        {"name": "amount", "logicalType": "number", "required": False},
                    ],
                }
            ]
        )

    def test_identical_contracts_produce_no_diff(self):
        c = self._base()
        result = diff(c, c)
        assert result == {}

    def test_field_added(self):
        v1 = self._base()
        v2 = self._base()
        v2["schema"][0]["properties"].append({"name": "region", "logicalType": "string"})
        result = diff(v1, v2)
        assert "dictionary_item_added" in result

    def test_field_removed(self):
        v1 = self._base()
        v2 = self._base()
        v2["schema"][0]["properties"] = [v2["schema"][0]["properties"][0]]  # remove amount
        result = diff(v1, v2)
        assert "dictionary_item_removed" in result

    def test_field_type_changed(self):
        v1 = self._base()
        v2 = self._base()
        v2["schema"][0]["properties"][0]["logicalType"] = "integer"
        result = diff(v1, v2)
        assert "values_changed" in result

    def test_schema_removed_mid_list_is_not_misreported_as_change(self):
        v1 = _contract(
            schema=[
                {"name": "orders", "physicalName": "orders_tbl"},
                {"name": "customers", "physicalName": "customers_tbl"},
            ]
        )
        v2 = _contract(
            schema=[
                {"name": "customers", "physicalName": "customers_tbl"},
            ]
        )
        result = diff(v1, v2)
        removed = result.get("dictionary_item_removed", {})
        changed = result.get("values_changed", {})
        assert any("orders" in k for k in removed)
        assert not any("customers" in k for k in changed)
        assert not any("customers" in k for k in removed)

    def test_sla_value_changed(self):
        v1 = _contract(slaProperties=[{"property": "availability", "value": "99.9%"}])
        v2 = _contract(slaProperties=[{"property": "availability", "value": "99.5%"}])
        result = diff(v1, v2)
        assert "values_changed" in result

    def test_server_added(self):
        v1 = _contract(servers=[{"server": "production", "type": "snowflake"}])
        v2 = _contract(
            servers=[
                {"server": "production", "type": "snowflake"},
                {"server": "staging", "type": "snowflake"},
            ]
        )
        result = diff(v1, v2)
        assert "dictionary_item_added" in result

    def test_server_role_added(self):
        v1 = _contract(
            servers=[
                {
                    "server": "production",
                    "type": "snowflake",
                    "roles": [
                        {"role": "reader", "access": "read"},
                    ],
                }
            ]
        )
        v2 = _contract(
            servers=[
                {
                    "server": "production",
                    "type": "snowflake",
                    "roles": [
                        {"role": "reader", "access": "read"},
                        {"role": "writer", "access": "write"},
                    ],
                }
            ]
        )
        result = diff(v1, v2)
        added = result.get("dictionary_item_added", {})
        assert any("writer" in k for k in added)

    def test_server_role_removed(self):
        v1 = _contract(
            servers=[
                {
                    "server": "production",
                    "type": "snowflake",
                    "roles": [
                        {"role": "reader", "access": "read"},
                        {"role": "writer", "access": "write"},
                    ],
                }
            ]
        )
        v2 = _contract(
            servers=[
                {
                    "server": "production",
                    "type": "snowflake",
                    "roles": [
                        {"role": "reader", "access": "read"},
                    ],
                }
            ]
        )
        result = diff(v1, v2)
        removed = result.get("dictionary_item_removed", {})
        assert any("writer" in k for k in removed)

    def test_schema_object_custom_property_changed(self):
        v1 = _contract(
            schema=[
                {
                    "name": "orders",
                    "customProperties": [
                        {"property": "domain", "value": "sales"},
                    ],
                }
            ]
        )
        v2 = _contract(
            schema=[
                {
                    "name": "orders",
                    "customProperties": [
                        {"property": "domain", "value": "finance"},
                    ],
                }
            ]
        )
        result = diff(v1, v2)
        changed = result.get("values_changed", {})
        assert any("domain" in k for k in changed)

    def test_schema_property_quality_rule_changed(self):
        v1 = _contract(
            schema=[
                {
                    "name": "orders",
                    "properties": [
                        {
                            "name": "amount",
                            "logicalType": "number",
                            "quality": [{"name": "positive", "metric": "rowCount", "mustBeGreaterThan": 0}],
                        }
                    ],
                }
            ]
        )
        v2 = _contract(
            schema=[
                {
                    "name": "orders",
                    "properties": [
                        {
                            "name": "amount",
                            "logicalType": "number",
                            "quality": [{"name": "positive", "metric": "rowCount", "mustBeGreaterThan": 100}],
                        }
                    ],
                }
            ]
        )
        result = diff(v1, v2)
        changed = result.get("values_changed", {})
        assert any("positive" in k for k in changed)

    def test_schema_property_custom_property_added(self):
        v1 = _contract(
            schema=[
                {
                    "name": "orders",
                    "properties": [
                        {
                            "name": "amount",
                            "logicalType": "number",
                        }
                    ],
                }
            ]
        )
        v2 = _contract(
            schema=[
                {
                    "name": "orders",
                    "properties": [
                        {
                            "name": "amount",
                            "logicalType": "number",
                            "customProperties": [{"property": "sensitivity", "value": "high"}],
                        }
                    ],
                }
            ]
        )
        result = diff(v1, v2)
        assert "dictionary_item_added" in result


class TestDiffFixtures:
    FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "changelog", "unit")

    def _generate(self):
        v1 = _load_contract(os.path.join(self.FIXTURE_DIR, "changelog_unit_v1.yaml"))
        v2 = _load_contract(os.path.join(self.FIXTURE_DIR, "changelog_unit_v2.yaml"))
        return diff(v1, v2)

    def test_diff_returns_dict(self):
        assert isinstance(self._generate(), dict)

    def test_diff_detects_known_changes(self):
        result = self._generate()
        added = result.get("dictionary_item_added", {})
        removed = result.get("dictionary_item_removed", {})
        changed = result.get("values_changed", {})
        assert any("customers" in k for k in added)
        assert any("customer_id" in k for k in removed)
        assert any("availability" in k for k in changed)

    def test_diff_identical_files_no_diff(self):
        v1_path = os.path.join(self.FIXTURE_DIR, "changelog_unit_v1.yaml")
        v = _load_contract(v1_path)
        assert diff(v, v) == {}

    def test_diff_with_temp_files(self):
        contract = _contract(schema=[{"name": "orders", "physicalName": "orders_tbl"}])
        with (
            tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f1,
            tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f2,
        ):
            yaml.dump(contract, f1)
            yaml.dump(contract, f2)
        try:
            v1 = _load_contract(f1.name)
            v2 = _load_contract(f2.name)
            assert diff(v1, v2) == {}
        finally:
            os.unlink(f1.name)
            os.unlink(f2.name)

    def test_schema_object_custom_property_changed(self):
        changed = self._generate().get("values_changed", {})
        assert any("domain" in k for k in changed)

    def test_schema_object_quality_changed(self):
        changed = self._generate().get("values_changed", {})
        assert any("row_count" in k for k in changed)

    def test_schema_property_quality_changed(self):
        changed = self._generate().get("values_changed", {})
        assert any("positive" in k for k in changed)

    def test_schema_property_custom_property_changed(self):
        changed = self._generate().get("values_changed", {})
        assert any("pii" in k for k in changed)

    def test_server_role_removed(self):
        removed = self._generate().get("dictionary_item_removed", {})
        assert any("writer" in k for k in removed)

    def test_top_level_role_added(self):
        added = self._generate().get("dictionary_item_added", {})
        assert any("viewer" in k for k in added)

    def test_support_channel_added(self):
        added = self._generate().get("dictionary_item_added", {})
        assert any("email" in k for k in added)

    def test_top_level_custom_property_changed(self):
        changed = self._generate().get("values_changed", {})
        assert any("classification" in k for k in changed)

    def test_team_member_role_changed(self):
        changed = self._generate().get("values_changed", {})
        assert any("bob" in k for k in changed)

    def test_team_member_added(self):
        added = self._generate().get("dictionary_item_added", {})
        assert any("carol" in k for k in added)


class TestDiffFixturesPriceDescriptionScalars(TestDiffFixtures):
    """Extends the end-to-end fixture tests to cover price, description, and
    top-level scalar fields that were previously absent from the unit fixtures."""

    def test_price_amount_changed(self):
        changed = self._generate().get("values_changed", {})
        assert any("priceAmount" in k for k in changed)

    def test_description_purpose_changed(self):
        changed = self._generate().get("values_changed", {})
        assert any("purpose" in k for k in changed)

    def test_description_custom_property_changed(self):
        changed = self._generate().get("values_changed", {})
        assert any("sensitivity" in k for k in changed)

    def test_description_custom_property_reorder_stable(self):
        """The description.customProperties reorder in v2 must not produce
        a false positive — only the sensitivity value change should appear."""
        changed = self._generate().get("values_changed", {})
        # data-owner is unchanged and reordered — must not appear
        assert not any("data-owner" in k for k in changed)

    def test_top_level_version_changed(self):
        changed = self._generate().get("values_changed", {})
        assert any("version" in k for k in changed)

    def test_top_level_name_changed(self):
        changed = self._generate().get("values_changed", {})
        assert any("'name'" in k for k in changed)

    def test_top_level_status_changed(self):
        changed = self._generate().get("values_changed", {})
        assert any("status" in k for k in changed)

    def test_top_level_domain_changed(self):
        changed = self._generate().get("values_changed", {})
        assert any("'domain'" in k for k in changed)


V1_YAML = "fixtures/changelog/integration/changelog_integration_v1.yaml"
V2_YAML = "fixtures/changelog/integration/changelog_integration_v2.yaml"


class TestBuildChangelog:
    def _load(self, path: str) -> OpenDataContractStandard:
        import yaml
        from open_data_contract_standard.model import OpenDataContractStandard

        with open(os.path.join(os.path.dirname(__file__), path)) as f:
            return OpenDataContractStandard.model_validate(yaml.safe_load(f))

    def test_returns_expected_top_level_keys(self):
        v1 = self._load(V1_YAML)
        v2 = self._load(V2_YAML)
        result = build_changelog(v1, V1_YAML, v2, V2_YAML)
        assert set(result.keys()) == {"source_label", "target_label", "header", "summary", "detail"}

    def test_source_and_target_labels_from_files(self):
        v1 = self._load(V1_YAML)
        v2 = self._load(V2_YAML)
        result = build_changelog(v1, V1_YAML, v2, V2_YAML)
        assert result["source_label"] == V1_YAML
        assert result["target_label"] == V2_YAML

    def test_fallback_labels_when_file_is_none(self):
        v1 = self._load(V1_YAML)
        result = build_changelog(v1, None, v1, None)
        assert result["source_label"] == "v1"
        assert result["target_label"] == "v2"

    def test_no_changes_on_identical_contracts(self):
        v1 = self._load(V1_YAML)
        result = build_changelog(v1, V1_YAML, v1, V1_YAML)
        assert result["detail"]["changes"] == []

    def test_detects_changes_between_versions(self):
        v1 = self._load(V1_YAML)
        v2 = self._load(V2_YAML)
        result = build_changelog(v1, V1_YAML, v2, V2_YAML)
        assert (
            result["detail"]["counts"]["added"]
            + result["detail"]["counts"]["removed"]
            + result["detail"]["counts"]["updated"]
            > 0
        )
