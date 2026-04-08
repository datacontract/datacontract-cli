"""
test_changelog_normalize — Unit tests for normalize.py
-----------------------------------------------------------
Test classes:
    TestNormalizeBy                  — _normalize_by: key field extraction and positional fallback
    TestNormalizeProperties          — _normalize_properties: recursive SchemaProperty keying
    TestNormalize                    — normalize(): all natural-key paths and edge cases
    TestNormalizeAuthDefs            — _normalize_auth_defs: url/id/positional fallback
    TestNormalizeRelationships       — _normalize_relationships: schema-level and property-level
    TestNormalizeDescription         — normalize(): description.authDefs and customProperties
    TestNormalizeServerCustomProperties — normalize(): server customProperties
    TestNormalizeQualityNested       — _normalize_quality: nested customProperties and authDefs
    TestGeneratePriceDescriptionScalars — end-to-end normalize via diff() for price/desc fields
"""

import yaml

from datacontract.changelog.changelog import diff
from datacontract.changelog.normalize import (
    _normalize_auth_defs,
    _normalize_by,
    _normalize_properties,
    _normalize_relationships,
    normalize,
)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

MINIMAL_CONTRACT = {
    "apiVersion": "v3.0.2",
    "kind": "DataContract",
    "id": "test-001",
}


def _write_yaml(data: dict, path: str) -> None:
    with open(path, "w") as f:
        yaml.dump(data, f)


def _contract(**kwargs) -> dict:
    return {**MINIMAL_CONTRACT, **kwargs}


class TestNormalizeBy:
    def test_keys_by_named_field(self):
        items = [
            {"role": "admin", "access": "read"},
            {"role": "viewer", "access": "read"},
        ]
        result = _normalize_by(items, "role")
        assert set(result.keys()) == {"admin", "viewer"}
        assert result["admin"] == {"access": "read"}

    def test_key_field_omitted_from_value(self):
        items = [{"channel": "slack", "url": "https://slack.com"}]
        result = _normalize_by(items, "channel")
        assert "channel" not in result["slack"]

    def test_positional_fallback_when_key_absent(self):
        items = [{"type": "sql", "rule": "count > 0"}, {"type": "sql"}]
        result = _normalize_by(items, "name")
        assert "__pos_0__" in result
        assert "__pos_1__" in result

    def test_mixed_present_and_absent_key(self):
        items = [
            {"name": "row_count", "rule": "count > 0"},
            {"rule": "no_nulls"},  # name absent
        ]
        result = _normalize_by(items, "name")
        assert "row_count" in result
        assert "__pos_1__" in result

    def test_empty_list(self):
        assert _normalize_by([], "role") == {}


class TestNormalizeProperties:
    def test_flat_properties_keyed_by_name(self):
        props = [
            {"name": "order_id", "logicalType": "string"},
            {"name": "amount", "logicalType": "number"},
        ]
        result = _normalize_properties(props)
        assert set(result.keys()) == {"order_id", "amount"}
        assert result["order_id"]["logicalType"] == "string"
        assert "name" not in result["order_id"]

    def test_nested_properties_recursed(self):
        props = [
            {
                "name": "address",
                "logicalType": "object",
                "properties": [
                    {"name": "street", "logicalType": "string"},
                    {"name": "city", "logicalType": "string"},
                ],
            }
        ]
        result = _normalize_properties(props)
        assert isinstance(result["address"]["properties"], dict)
        assert "street" in result["address"]["properties"]
        assert "city" in result["address"]["properties"]

    def test_empty_properties(self):
        assert _normalize_properties([]) == {}


class TestNormalize:
    def test_schema_keyed_by_name(self):
        contract = _contract(
            schema=[
                {"name": "orders", "physicalName": "orders_tbl"},
                {"name": "customers", "physicalName": "customers_tbl"},
            ]
        )
        result = normalize(contract)
        assert isinstance(result["schema"], dict)
        assert set(result["schema"].keys()) == {"orders", "customers"}
        assert "name" not in result["schema"]["orders"]

    def test_schema_properties_keyed_by_name(self):
        contract = _contract(
            schema=[
                {
                    "name": "orders",
                    "properties": [
                        {"name": "order_id", "logicalType": "string"},
                    ],
                }
            ]
        )
        result = normalize(contract)
        assert isinstance(result["schema"]["orders"]["properties"], dict)
        assert "order_id" in result["schema"]["orders"]["properties"]

    def test_sla_properties_keyed_by_property(self):
        contract = _contract(
            slaProperties=[
                {"property": "availability", "value": "99.9%"},
                {"property": "latency", "value": "500ms"},
            ]
        )
        result = normalize(contract)
        assert isinstance(result["slaProperties"], dict)
        assert "availability" in result["slaProperties"]
        assert result["slaProperties"]["availability"] == {"value": "99.9%"}

    def test_servers_keyed_by_server(self):
        contract = _contract(
            servers=[
                {"server": "production", "type": "snowflake"},
                {"server": "staging", "type": "snowflake"},
            ]
        )
        result = normalize(contract)
        assert isinstance(result["servers"], dict)
        assert set(result["servers"].keys()) == {"production", "staging"}
        assert "server" not in result["servers"]["production"]

    def test_roles_keyed_by_role(self):
        contract = _contract(
            roles=[
                {"role": "admin", "access": "write"},
                {"role": "viewer", "access": "read"},
            ]
        )
        result = normalize(contract)
        assert isinstance(result["roles"], dict)
        assert "admin" in result["roles"]

    def test_support_keyed_by_channel(self):
        contract = _contract(
            support=[
                {"channel": "slack", "url": "https://slack.com"},
            ]
        )
        result = normalize(contract)
        assert "slack" in result["support"]

    def test_custom_properties_keyed_by_property(self):
        contract = _contract(
            customProperties=[
                {"property": "domain", "value": "sales"},
                {"property": "team_name", "value": "orders"},
            ]
        )
        result = normalize(contract)
        assert "domain" in result["customProperties"]
        assert "team_name" in result["customProperties"]

    def test_team_members_keyed_by_username(self):
        contract = _contract(
            team={
                "name": "Data Team",
                "members": [
                    {"username": "alice", "role": "lead"},
                    {"username": "bob", "role": "engineer"},
                ],
            }
        )
        result = normalize(contract)
        assert "alice" in result["team"]["members"]
        assert "bob" in result["team"]["members"]

    def test_team_deprecated_array_form(self):
        contract = _contract(
            team=[
                {"username": "alice", "role": "lead"},
            ]
        )
        result = normalize(contract)
        assert isinstance(result["team"], dict)
        assert "alice" in result["team"]

    def test_quality_keyed_by_name_with_positional_fallback(self):
        contract = _contract(
            schema=[
                {
                    "name": "orders",
                    "quality": [
                        {"name": "row_count", "metric": "rowCount"},
                        {"metric": "duplicateValues"},  # no name
                    ],
                }
            ]
        )
        result = normalize(contract)
        quality = result["schema"]["orders"]["quality"]
        assert "row_count" in quality
        assert "__pos_1__" in quality

    def test_non_list_fields_unchanged(self):
        contract = _contract(description="a contract")
        result = normalize(contract)
        assert result["description"] == "a contract"

    def test_schema_object_custom_properties_keyed_by_property(self):
        contract = _contract(
            schema=[
                {
                    "name": "orders",
                    "customProperties": [
                        {"property": "domain", "value": "sales"},
                        {"property": "team_name", "value": "orders"},
                    ],
                }
            ]
        )
        result = normalize(contract)
        cp = result["schema"]["orders"]["customProperties"]
        assert isinstance(cp, dict)
        assert "domain" in cp
        assert "team_name" in cp

    def test_schema_object_quality_keyed_by_name(self):
        contract = _contract(
            schema=[
                {
                    "name": "orders",
                    "quality": [
                        {"name": "row_count", "metric": "rowCount"},
                        {"name": "no_nulls", "metric": "nullValues"},
                    ],
                }
            ]
        )
        result = normalize(contract)
        quality = result["schema"]["orders"]["quality"]
        assert isinstance(quality, dict)
        assert "row_count" in quality
        assert "no_nulls" in quality

    def test_schema_property_quality_keyed_by_name(self):
        contract = _contract(
            schema=[
                {
                    "name": "orders",
                    "properties": [
                        {
                            "name": "amount",
                            "logicalType": "number",
                            "quality": [
                                {"name": "positive", "metric": "rowCount"},
                            ],
                        }
                    ],
                }
            ]
        )
        result = normalize(contract)
        quality = result["schema"]["orders"]["properties"]["amount"]["quality"]
        assert isinstance(quality, dict)
        assert "positive" in quality

    def test_schema_property_custom_properties_keyed_by_property(self):
        contract = _contract(
            schema=[
                {
                    "name": "orders",
                    "properties": [
                        {
                            "name": "amount",
                            "logicalType": "number",
                            "customProperties": [
                                {"property": "sensitivity", "value": "high"},
                            ],
                        }
                    ],
                }
            ]
        )
        result = normalize(contract)
        cp = result["schema"]["orders"]["properties"]["amount"]["customProperties"]
        assert isinstance(cp, dict)
        assert "sensitivity" in cp

    def test_server_roles_keyed_by_role(self):
        contract = _contract(
            servers=[
                {
                    "server": "production",
                    "type": "snowflake",
                    "roles": [
                        {"role": "admin", "access": "write"},
                        {"role": "reader", "access": "read"},
                    ],
                }
            ]
        )
        result = normalize(contract)
        roles = result["servers"]["production"]["roles"]
        assert isinstance(roles, dict)
        assert "admin" in roles
        assert "reader" in roles

    def test_server_without_server_key_skipped(self):
        contract = _contract(
            servers=[
                {"type": "snowflake"},  # no "server" key — skip
                {"server": "production", "type": "snowflake"},  # valid — retain
            ]
        )
        result = normalize(contract)
        assert isinstance(result["servers"], dict)
        assert "production" in result["servers"]
        assert len(result["servers"]) == 1

    def test_no_mutation_of_input(self):
        contract = _contract(schema=[{"name": "orders"}])
        original = _contract(schema=[{"name": "orders"}])
        normalize(contract)
        assert contract == original


# ---------------------------------------------------------------------------
# _diff — semantic correctness
# ---------------------------------------------------------------------------


class TestNormalizeAuthDefs:
    def test_keys_by_url(self):
        items = [
            {"url": "https://example.com/wiki", "type": "definition"},
            {"url": "https://example.com/slack", "type": "support"},
        ]
        result = _normalize_auth_defs(items)
        assert set(result.keys()) == {"https://example.com/wiki", "https://example.com/slack"}

    def test_all_fields_preserved_in_value(self):
        items = [{"url": "https://example.com/wiki", "type": "definition", "description": "main ref"}]
        result = _normalize_auth_defs(items)
        assert result["https://example.com/wiki"]["type"] == "definition"
        assert result["https://example.com/wiki"]["description"] == "main ref"

    def test_id_fallback_when_url_absent(self):
        items = [{"id": "def-001", "type": "definition"}]
        result = _normalize_auth_defs(items)
        assert "def-001" in result

    def test_positional_fallback_when_url_and_id_absent(self):
        items = [{"type": "definition"}, {"type": "support"}]
        result = _normalize_auth_defs(items)
        assert "__pos_0__" in result
        assert "__pos_1__" in result

    def test_empty_list_returns_empty_dict(self):
        assert _normalize_auth_defs([]) == {}

    def test_reorder_produces_no_diff(self):
        v1 = _contract(
            authoritativeDefinitions=[
                {"url": "https://example.com/wiki", "type": "definition"},
                {"url": "https://example.com/slack", "type": "support"},
            ]
        )
        v2 = _contract(
            authoritativeDefinitions=[
                {"url": "https://example.com/slack", "type": "support"},
                {"url": "https://example.com/wiki", "type": "definition"},
            ]
        )
        assert diff(v1, v2) == {}

    def test_url_change_detected(self):
        v1 = _contract(authoritativeDefinitions=[{"url": "https://example.com/wiki", "type": "definition"}])
        v2 = _contract(authoritativeDefinitions=[{"url": "https://example.com/NEW", "type": "definition"}])
        result = diff(v1, v2)
        # Changing a url changes the dict key — DeepDiff reports this as
        # dictionary_item_added + dictionary_item_removed or values_changed
        assert result != {}

    def test_type_change_detected(self):
        v1 = _contract(authoritativeDefinitions=[{"url": "https://example.com/wiki", "type": "definition"}])
        v2 = _contract(authoritativeDefinitions=[{"url": "https://example.com/wiki", "type": "policy"}])
        result = diff(v1, v2)
        assert "values_changed" in result

    def test_schema_object_auth_defs_reorder_no_diff(self):
        def contract(defs):
            return _contract(schema=[{"name": "orders", "authoritativeDefinitions": defs}])

        v1 = contract(
            [
                {"url": "https://a.com", "type": "definition"},
                {"url": "https://b.com", "type": "support"},
            ]
        )
        v2 = contract(
            [
                {"url": "https://b.com", "type": "support"},
                {"url": "https://a.com", "type": "definition"},
            ]
        )
        assert diff(v1, v2) == {}

    def test_schema_property_auth_defs_reorder_no_diff(self):
        def contract(defs):
            return _contract(
                schema=[
                    {
                        "name": "orders",
                        "properties": [
                            {
                                "name": "order_id",
                                "logicalType": "string",
                                "authoritativeDefinitions": defs,
                            }
                        ],
                    }
                ]
            )

        v1 = contract(
            [
                {"url": "https://a.com", "type": "definition"},
                {"url": "https://b.com", "type": "support"},
            ]
        )
        v2 = contract(
            [
                {"url": "https://b.com", "type": "support"},
                {"url": "https://a.com", "type": "definition"},
            ]
        )
        assert diff(v1, v2) == {}

    def test_description_auth_defs_reorder_no_diff(self):
        v1 = _contract(
            **{
                "description": {
                    "purpose": "test",
                    "authoritativeDefinitions": [
                        {"url": "https://a.com", "type": "policy"},
                        {"url": "https://b.com", "type": "definition"},
                    ],
                }
            }
        )
        v2 = _contract(
            **{
                "description": {
                    "purpose": "test",
                    "authoritativeDefinitions": [
                        {"url": "https://b.com", "type": "definition"},
                        {"url": "https://a.com", "type": "policy"},
                    ],
                }
            }
        )
        assert diff(v1, v2) == {}


class TestNormalizeRelationships:
    def test_schema_level_keyed_by_from_to(self):
        items = [
            {"from": "orders.order_id", "to": "line_items.order_id", "type": "foreignKey"},
            {"from": "orders.customer_id", "to": "customers.customer_id", "type": "foreignKey"},
        ]
        result = _normalize_relationships(items, schema_level=True)
        assert "orders.order_id:line_items.order_id" in result
        assert "orders.customer_id:customers.customer_id" in result

    def test_property_level_keyed_by_to(self):
        items = [
            {"to": "customers.customer_id", "type": "foreignKey"},
        ]
        result = _normalize_relationships(items, schema_level=False)
        assert "customers.customer_id" in result

    def test_positional_fallback_when_fields_absent(self):
        items = [{"type": "foreignKey"}]
        result = _normalize_relationships(items, schema_level=True)
        assert "__pos_0__" in result

    def test_empty_list_returns_empty_dict(self):
        assert _normalize_relationships([], schema_level=True) == {}

    def test_schema_relationships_reorder_no_diff(self):
        def contract(rels):
            return _contract(schema=[{"name": "orders", "relationships": rels}])

        v1 = contract(
            [
                {"from": "orders.order_id", "to": "line_items.order_id", "type": "foreignKey"},
                {"from": "orders.customer_id", "to": "customers.customer_id", "type": "foreignKey"},
            ]
        )
        v2 = contract(
            [
                {"from": "orders.customer_id", "to": "customers.customer_id", "type": "foreignKey"},
                {"from": "orders.order_id", "to": "line_items.order_id", "type": "foreignKey"},
            ]
        )
        assert diff(v1, v2) == {}

    def test_property_relationships_reorder_no_diff(self):
        def contract(rels):
            return _contract(
                schema=[
                    {
                        "name": "orders",
                        "properties": [
                            {
                                "name": "order_id",
                                "logicalType": "string",
                                "relationships": rels,
                            }
                        ],
                    }
                ]
            )

        v1 = contract(
            [
                {"to": "line_items.order_id", "type": "foreignKey"},
                {"to": "audit_log.order_id", "type": "reference"},
            ]
        )
        v2 = contract(
            [
                {"to": "audit_log.order_id", "type": "reference"},
                {"to": "line_items.order_id", "type": "foreignKey"},
            ]
        )
        assert diff(v1, v2) == {}

    def test_relationship_added_detected(self):
        v1 = _contract(
            schema=[
                {
                    "name": "orders",
                    "relationships": [
                        {"from": "orders.order_id", "to": "line_items.order_id", "type": "foreignKey"},
                    ],
                }
            ]
        )
        v2 = _contract(
            schema=[
                {
                    "name": "orders",
                    "relationships": [
                        {"from": "orders.order_id", "to": "line_items.order_id", "type": "foreignKey"},
                        {"from": "orders.customer_id", "to": "customers.customer_id", "type": "foreignKey"},
                    ],
                }
            ]
        )
        result = diff(v1, v2)
        added = result.get("dictionary_item_added", {})
        assert any("customer_id" in k for k in added)

    def test_relationship_type_change_detected(self):
        def contract(t):
            return _contract(
                schema=[
                    {
                        "name": "orders",
                        "relationships": [
                            {"from": "orders.order_id", "to": "line_items.order_id", "type": t},
                        ],
                    }
                ]
            )

        result = diff(contract("foreignKey"), contract("reference"))
        assert "values_changed" in result


class TestNormalizeDescription:
    def test_description_purpose_change_detected(self):
        v1 = _contract(**{"description": {"purpose": "Provides order data"}})
        v2 = _contract(**{"description": {"purpose": "Provides order and line item data"}})
        result = diff(v1, v2)
        assert "values_changed" in result
        changed = result["values_changed"]
        assert any("purpose" in k for k in changed)

    def test_description_custom_property_change_detected(self):
        v1 = _contract(
            **{
                "description": {
                    "purpose": "test",
                    "customProperties": [
                        {"property": "sensitivity", "value": "internal"},
                    ],
                }
            }
        )
        v2 = _contract(
            **{
                "description": {
                    "purpose": "test",
                    "customProperties": [
                        {"property": "sensitivity", "value": "confidential"},
                    ],
                }
            }
        )
        result = diff(v1, v2)
        changed = result.get("values_changed", {})
        assert any("sensitivity" in k for k in changed)

    def test_description_custom_property_reorder_no_diff(self):
        v1 = _contract(
            **{
                "description": {
                    "purpose": "test",
                    "customProperties": [
                        {"property": "sensitivity", "value": "internal"},
                        {"property": "owner", "value": "data-team"},
                    ],
                }
            }
        )
        v2 = _contract(
            **{
                "description": {
                    "purpose": "test",
                    "customProperties": [
                        {"property": "owner", "value": "data-team"},
                        {"property": "sensitivity", "value": "internal"},
                    ],
                }
            }
        )
        assert diff(v1, v2) == {}

    def test_description_custom_property_added(self):
        v1 = _contract(
            **{
                "description": {
                    "purpose": "test",
                    "customProperties": [
                        {"property": "sensitivity", "value": "internal"},
                    ],
                }
            }
        )
        v2 = _contract(
            **{
                "description": {
                    "purpose": "test",
                    "customProperties": [
                        {"property": "sensitivity", "value": "internal"},
                        {"property": "owner", "value": "data-team"},
                    ],
                }
            }
        )
        result = diff(v1, v2)
        added = result.get("dictionary_item_added", {})
        assert any("owner" in k for k in added)

    def test_description_auth_defs_reorder_no_diff(self):
        v1 = _contract(
            **{
                "description": {
                    "purpose": "test",
                    "authoritativeDefinitions": [
                        {"url": "https://a.com", "type": "policy"},
                        {"url": "https://b.com", "type": "definition"},
                    ],
                }
            }
        )
        v2 = _contract(
            **{
                "description": {
                    "purpose": "test",
                    "authoritativeDefinitions": [
                        {"url": "https://b.com", "type": "definition"},
                        {"url": "https://a.com", "type": "policy"},
                    ],
                }
            }
        )
        assert diff(v1, v2) == {}

    def test_description_scalar_fields_all_detected(self):
        """purpose, usage, and limitations are all plain strings — changes must be detected."""
        for field in ("purpose", "usage", "limitations"):
            v1 = _contract(**{"description": {field: "original value"}})
            v2 = _contract(**{"description": {field: "updated value"}})
            result = diff(v1, v2)
            assert "values_changed" in result, f"change in {field} not detected"
            assert any(field in k for k in result["values_changed"])


class TestNormalizeServerCustomProperties:
    def _server(self, custom_props):
        return _contract(
            servers=[
                {
                    "server": "production",
                    "type": "snowflake",
                    "customProperties": custom_props,
                }
            ]
        )

    def test_custom_property_change_detected(self):
        v1 = self._server([{"property": "cost-center", "value": "eng-001"}])
        v2 = self._server([{"property": "cost-center", "value": "eng-999"}])
        result = diff(v1, v2)
        changed = result.get("values_changed", {})
        assert any("cost-center" in k for k in changed)

    def test_reorder_no_diff(self):
        v1 = self._server(
            [
                {"property": "team", "value": "data-platform"},
                {"property": "cost-center", "value": "eng-001"},
            ]
        )
        v2 = self._server(
            [
                {"property": "cost-center", "value": "eng-001"},
                {"property": "team", "value": "data-platform"},
            ]
        )
        assert diff(v1, v2) == {}

    def test_change_with_reorder_path_includes_property_name(self):
        """When value changes and list is simultaneously reordered, the path
        must name the property (not use a positional index)."""
        v1 = self._server(
            [
                {"property": "team", "value": "data-platform"},
                {"property": "cost-center", "value": "eng-001"},
                {"property": "env", "value": "prod"},
            ]
        )
        v2 = self._server(
            [
                {"property": "env", "value": "prod"},
                {"property": "team", "value": "data-platform"},
                {"property": "cost-center", "value": "eng-999"},
            ]
        )
        raw = diff(v1, v2)
        changed = raw.get("values_changed", {})
        assert any("cost-center" in k for k in changed)
        assert not any(k.endswith("][0]") or k.endswith("][1]") or k.endswith("][2]") for k in changed)

    def test_custom_property_added(self):
        v1 = self._server([{"property": "team", "value": "data-platform"}])
        v2 = self._server(
            [
                {"property": "team", "value": "data-platform"},
                {"property": "owner", "value": "alice"},
            ]
        )
        result = diff(v1, v2)
        added = result.get("dictionary_item_added", {})
        assert any("owner" in k for k in added)

    def test_custom_property_removed(self):
        v1 = self._server(
            [
                {"property": "team", "value": "data-platform"},
                {"property": "owner", "value": "alice"},
            ]
        )
        v2 = self._server([{"property": "team", "value": "data-platform"}])
        result = diff(v1, v2)
        removed = result.get("dictionary_item_removed", {})
        assert any("owner" in k for k in removed)

    def test_multiple_servers_independent(self):
        """customProperties on two different servers are normalized independently."""
        v1 = _contract(
            servers=[
                {"server": "prod", "type": "snowflake", "customProperties": [{"property": "env", "value": "prod"}]},
                {
                    "server": "staging",
                    "type": "snowflake",
                    "customProperties": [{"property": "env", "value": "staging"}],
                },
            ]
        )
        v2 = _contract(
            servers=[
                {"server": "prod", "type": "snowflake", "customProperties": [{"property": "env", "value": "prod"}]},
                {
                    "server": "staging",
                    "type": "snowflake",
                    "customProperties": [{"property": "env", "value": "staging-new"}],
                },
            ]
        )
        result = diff(v1, v2)
        changed = result.get("values_changed", {})
        assert any("staging" in k for k in changed)
        assert not any("prod" in k and "customProperties" in k for k in changed)


class TestNormalizeQualityNested:
    def _schema_quality(self, quality_items):
        return _contract(
            schema=[
                {
                    "name": "orders",
                    "physicalName": "orders_tbl",
                    "quality": quality_items,
                }
            ]
        )

    def _property_quality(self, quality_items):
        return _contract(
            schema=[
                {
                    "name": "orders",
                    "physicalName": "orders_tbl",
                    "properties": [
                        {
                            "name": "amount",
                            "logicalType": "number",
                            "quality": quality_items,
                        }
                    ],
                }
            ]
        )

    def test_schema_quality_custom_property_change_detected(self):
        v1 = self._schema_quality(
            [{"name": "row_count", "type": "sql", "customProperties": [{"property": "severity", "value": "high"}]}]
        )
        v2 = self._schema_quality(
            [{"name": "row_count", "type": "sql", "customProperties": [{"property": "severity", "value": "critical"}]}]
        )
        result = diff(v1, v2)
        changed = result.get("values_changed", {})
        assert any("severity" in k for k in changed)

    def test_schema_quality_custom_property_reorder_no_diff(self):
        v1 = self._schema_quality(
            [
                {
                    "name": "row_count",
                    "type": "sql",
                    "customProperties": [
                        {"property": "severity", "value": "high"},
                        {"property": "owner", "value": "data-team"},
                    ],
                }
            ]
        )
        v2 = self._schema_quality(
            [
                {
                    "name": "row_count",
                    "type": "sql",
                    "customProperties": [
                        {"property": "owner", "value": "data-team"},
                        {"property": "severity", "value": "high"},
                    ],
                }
            ]
        )
        assert diff(v1, v2) == {}

    def test_schema_quality_change_with_reorder_path_has_property_name(self):
        """Path must name the property, not use a positional index."""
        v1 = self._schema_quality(
            [
                {
                    "name": "row_count",
                    "type": "sql",
                    "customProperties": [
                        {"property": "severity", "value": "high"},
                        {"property": "owner", "value": "data-team"},
                        {"property": "env", "value": "prod"},
                    ],
                }
            ]
        )
        v2 = self._schema_quality(
            [
                {
                    "name": "row_count",
                    "type": "sql",
                    "customProperties": [
                        {"property": "env", "value": "prod"},
                        {"property": "severity", "value": "critical"},
                        {"property": "owner", "value": "data-team"},
                    ],
                }
            ]
        )
        raw = diff(v1, v2)
        changed = raw.get("values_changed", {})
        assert any("severity" in k for k in changed)
        assert not any("][0]" in k or "][1]" in k or "][2]" in k for k in changed)

    def test_schema_quality_auth_defs_reorder_no_diff(self):
        v1 = self._schema_quality(
            [
                {
                    "name": "row_count",
                    "type": "sql",
                    "authoritativeDefinitions": [
                        {"url": "https://a.com", "type": "definition"},
                        {"url": "https://b.com", "type": "support"},
                    ],
                }
            ]
        )
        v2 = self._schema_quality(
            [
                {
                    "name": "row_count",
                    "type": "sql",
                    "authoritativeDefinitions": [
                        {"url": "https://b.com", "type": "support"},
                        {"url": "https://a.com", "type": "definition"},
                    ],
                }
            ]
        )
        assert diff(v1, v2) == {}

    def test_schema_quality_auth_def_change_detected(self):
        v1 = self._schema_quality(
            [
                {
                    "name": "row_count",
                    "type": "sql",
                    "authoritativeDefinitions": [{"url": "https://a.com", "type": "definition"}],
                }
            ]
        )
        v2 = self._schema_quality(
            [
                {
                    "name": "row_count",
                    "type": "sql",
                    "authoritativeDefinitions": [{"url": "https://a.com", "type": "policy"}],
                }
            ]
        )
        result = diff(v1, v2)
        assert result != {}

    def test_property_quality_custom_property_change_detected(self):
        v1 = self._property_quality(
            [{"name": "positive", "type": "sql", "customProperties": [{"property": "priority", "value": "p1"}]}]
        )
        v2 = self._property_quality(
            [{"name": "positive", "type": "sql", "customProperties": [{"property": "priority", "value": "p2"}]}]
        )
        result = diff(v1, v2)
        changed = result.get("values_changed", {})
        assert any("priority" in k for k in changed)

    def test_property_quality_custom_property_reorder_no_diff(self):
        v1 = self._property_quality(
            [
                {
                    "name": "positive",
                    "type": "sql",
                    "customProperties": [
                        {"property": "priority", "value": "p1"},
                        {"property": "team", "value": "data"},
                    ],
                }
            ]
        )
        v2 = self._property_quality(
            [
                {
                    "name": "positive",
                    "type": "sql",
                    "customProperties": [
                        {"property": "team", "value": "data"},
                        {"property": "priority", "value": "p1"},
                    ],
                }
            ]
        )
        assert diff(v1, v2) == {}

    def test_property_quality_auth_defs_reorder_no_diff(self):
        v1 = self._property_quality(
            [
                {
                    "name": "positive",
                    "type": "sql",
                    "authoritativeDefinitions": [
                        {"url": "https://a.com", "type": "definition"},
                        {"url": "https://b.com", "type": "support"},
                    ],
                }
            ]
        )
        v2 = self._property_quality(
            [
                {
                    "name": "positive",
                    "type": "sql",
                    "authoritativeDefinitions": [
                        {"url": "https://b.com", "type": "support"},
                        {"url": "https://a.com", "type": "definition"},
                    ],
                }
            ]
        )
        assert diff(v1, v2) == {}
