"""
test_diff — Unit tests for ContractDiff
-------------------------------------------------
Test classes:
    TestNormalizeBy        — _normalize_by: key field extraction and positional fallback
    TestNormalizeProperties — _normalize_properties: recursive SchemaProperty keying
    TestNormalize          — _normalize: all 13 natural-key paths and edge cases
    TestDiff               — _diff: semantic correctness (added/removed/changed/mid-list)
    TestGenerate           — generate(): end-to-end using fixtures/diff/unit/
"""

import os
import tempfile

import yaml

from datacontract.reports.diff.diff import ContractDiff

DIFF = ContractDiff()

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
        result = ContractDiff._normalize_by(items, "role")
        assert set(result.keys()) == {"admin", "viewer"}
        assert result["admin"] == {"access": "read"}

    def test_key_field_omitted_from_value(self):
        items = [{"channel": "slack", "url": "https://slack.com"}]
        result = ContractDiff._normalize_by(items, "channel")
        assert "channel" not in result["slack"]

    def test_positional_fallback_when_key_absent(self):
        items = [{"type": "sql", "rule": "count > 0"}, {"type": "sql"}]
        result = ContractDiff._normalize_by(items, "name")
        assert "__pos_0__" in result
        assert "__pos_1__" in result

    def test_mixed_present_and_absent_key(self):
        items = [
            {"name": "row_count", "rule": "count > 0"},
            {"rule": "no_nulls"},  # name absent
        ]
        result = ContractDiff._normalize_by(items, "name")
        assert "row_count" in result
        assert "__pos_1__" in result

    def test_empty_list(self):
        assert ContractDiff._normalize_by([], "role") == {}


class TestNormalizeProperties:
    def test_flat_properties_keyed_by_name(self):
        props = [
            {"name": "order_id", "logicalType": "string"},
            {"name": "amount", "logicalType": "number"},
        ]
        result = ContractDiff._normalize_properties(props)
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
        result = ContractDiff._normalize_properties(props)
        assert isinstance(result["address"]["properties"], dict)
        assert "street" in result["address"]["properties"]
        assert "city" in result["address"]["properties"]

    def test_empty_properties(self):
        assert ContractDiff._normalize_properties([]) == {}


class TestNormalize:
    def test_schema_keyed_by_name(self):
        contract = _contract(
            schema=[
                {"name": "orders", "physicalName": "orders_tbl"},
                {"name": "customers", "physicalName": "customers_tbl"},
            ]
        )
        result = ContractDiff._normalize(contract)
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
        result = ContractDiff._normalize(contract)
        assert isinstance(result["schema"]["orders"]["properties"], dict)
        assert "order_id" in result["schema"]["orders"]["properties"]

    def test_sla_properties_keyed_by_property(self):
        contract = _contract(
            slaProperties=[
                {"property": "availability", "value": "99.9%"},
                {"property": "latency", "value": "500ms"},
            ]
        )
        result = ContractDiff._normalize(contract)
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
        result = ContractDiff._normalize(contract)
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
        result = ContractDiff._normalize(contract)
        assert isinstance(result["roles"], dict)
        assert "admin" in result["roles"]

    def test_support_keyed_by_channel(self):
        contract = _contract(
            support=[
                {"channel": "slack", "url": "https://slack.com"},
            ]
        )
        result = ContractDiff._normalize(contract)
        assert "slack" in result["support"]

    def test_custom_properties_keyed_by_property(self):
        contract = _contract(
            customProperties=[
                {"property": "domain", "value": "sales"},
                {"property": "team_name", "value": "orders"},
            ]
        )
        result = ContractDiff._normalize(contract)
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
        result = ContractDiff._normalize(contract)
        assert "alice" in result["team"]["members"]
        assert "bob" in result["team"]["members"]

    def test_team_deprecated_array_form(self):
        contract = _contract(
            team=[
                {"username": "alice", "role": "lead"},
            ]
        )
        result = ContractDiff._normalize(contract)
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
        result = ContractDiff._normalize(contract)
        quality = result["schema"]["orders"]["quality"]
        assert "row_count" in quality
        assert "__pos_1__" in quality

    def test_non_list_fields_unchanged(self):
        contract = _contract(description="a contract")
        result = ContractDiff._normalize(contract)
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
        result = ContractDiff._normalize(contract)
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
        result = ContractDiff._normalize(contract)
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
        result = ContractDiff._normalize(contract)
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
        result = ContractDiff._normalize(contract)
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
        result = ContractDiff._normalize(contract)
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
        result = ContractDiff._normalize(contract)
        assert isinstance(result["servers"], dict)
        assert "production" in result["servers"]
        assert len(result["servers"]) == 1

    def test_no_mutation_of_input(self):
        contract = _contract(schema=[{"name": "orders"}])
        original = _contract(schema=[{"name": "orders"}])
        ContractDiff._normalize(contract)
        assert contract == original


# ---------------------------------------------------------------------------
# _diff — semantic correctness
# ---------------------------------------------------------------------------


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
        result = DIFF._diff(c, c)
        assert result == {}

    def test_field_added(self):
        v1 = self._base()
        v2 = self._base()
        v2["schema"][0]["properties"].append({"name": "region", "logicalType": "string"})
        result = DIFF._diff(v1, v2)
        assert "dictionary_item_added" in result

    def test_field_removed(self):
        v1 = self._base()
        v2 = self._base()
        v2["schema"][0]["properties"] = [v2["schema"][0]["properties"][0]]  # remove amount
        result = DIFF._diff(v1, v2)
        assert "dictionary_item_removed" in result

    def test_field_type_changed(self):
        v1 = self._base()
        v2 = self._base()
        v2["schema"][0]["properties"][0]["logicalType"] = "integer"
        result = DIFF._diff(v1, v2)
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
        result = DIFF._diff(v1, v2)
        removed = result.get("dictionary_item_removed", {})
        changed = result.get("values_changed", {})
        assert any("orders" in k for k in removed)
        assert not any("customers" in k for k in changed)
        assert not any("customers" in k for k in removed)

    def test_sla_value_changed(self):
        v1 = _contract(slaProperties=[{"property": "availability", "value": "99.9%"}])
        v2 = _contract(slaProperties=[{"property": "availability", "value": "99.5%"}])
        result = DIFF._diff(v1, v2)
        assert "values_changed" in result

    def test_server_added(self):
        v1 = _contract(servers=[{"server": "production", "type": "snowflake"}])
        v2 = _contract(
            servers=[
                {"server": "production", "type": "snowflake"},
                {"server": "staging", "type": "snowflake"},
            ]
        )
        result = DIFF._diff(v1, v2)
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
        result = DIFF._diff(v1, v2)
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
        result = DIFF._diff(v1, v2)
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
        result = DIFF._diff(v1, v2)
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
        result = DIFF._diff(v1, v2)
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
        result = DIFF._diff(v1, v2)
        assert "dictionary_item_added" in result


class TestGenerate:
    FIXTURE_DIR = os.path.join(os.path.dirname(__file__), "fixtures", "diff", "unit")

    def _generate(self):
        return DIFF.generate(
            os.path.join(self.FIXTURE_DIR, "odcs_diff_unit_v1.yaml"),
            os.path.join(self.FIXTURE_DIR, "odcs_diff_unit_v2.yaml"),
        )

    def test_generate_returns_dict(self):
        assert isinstance(self._generate(), dict)

    def test_generate_detects_known_changes(self):
        result = self._generate()
        added = result.get("dictionary_item_added", {})
        removed = result.get("dictionary_item_removed", {})
        changed = result.get("values_changed", {})
        assert any("customers" in k for k in added)
        assert any("customer_id" in k for k in removed)
        assert any("availability" in k for k in changed)

    def test_generate_identical_files_no_diff(self):
        v1_path = os.path.join(self.FIXTURE_DIR, "odcs_diff_unit_v1.yaml")
        assert DIFF.generate(v1_path, v1_path) == {}

    def test_generate_with_temp_files(self):
        contract = _contract(schema=[{"name": "orders", "physicalName": "orders_tbl"}])
        with (
            tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f1,
            tempfile.NamedTemporaryFile(suffix=".yaml", mode="w", delete=False) as f2,
        ):
            yaml.dump(contract, f1)
            yaml.dump(contract, f2)
        try:
            assert DIFF.generate(f1.name, f2.name) == {}
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


class TestNormalizeAuthDefs:
    def test_keys_by_url(self):
        items = [
            {"url": "https://example.com/wiki", "type": "definition"},
            {"url": "https://example.com/slack", "type": "support"},
        ]
        result = ContractDiff._normalize_auth_defs(items)
        assert set(result.keys()) == {"https://example.com/wiki", "https://example.com/slack"}

    def test_all_fields_preserved_in_value(self):
        items = [{"url": "https://example.com/wiki", "type": "definition", "description": "main ref"}]
        result = ContractDiff._normalize_auth_defs(items)
        assert result["https://example.com/wiki"]["type"] == "definition"
        assert result["https://example.com/wiki"]["description"] == "main ref"

    def test_id_fallback_when_url_absent(self):
        items = [{"id": "def-001", "type": "definition"}]
        result = ContractDiff._normalize_auth_defs(items)
        assert "def-001" in result

    def test_positional_fallback_when_url_and_id_absent(self):
        items = [{"type": "definition"}, {"type": "support"}]
        result = ContractDiff._normalize_auth_defs(items)
        assert "__pos_0__" in result
        assert "__pos_1__" in result

    def test_empty_list_returns_empty_dict(self):
        assert ContractDiff._normalize_auth_defs([]) == {}

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
        assert DIFF._diff(v1, v2) == {}

    def test_url_change_detected(self):
        v1 = _contract(authoritativeDefinitions=[{"url": "https://example.com/wiki", "type": "definition"}])
        v2 = _contract(authoritativeDefinitions=[{"url": "https://example.com/NEW", "type": "definition"}])
        result = DIFF._diff(v1, v2)
        # Changing a url changes the dict key — DeepDiff reports this as
        # dictionary_item_added + dictionary_item_removed or values_changed
        assert result != {}

    def test_type_change_detected(self):
        v1 = _contract(authoritativeDefinitions=[{"url": "https://example.com/wiki", "type": "definition"}])
        v2 = _contract(authoritativeDefinitions=[{"url": "https://example.com/wiki", "type": "policy"}])
        result = DIFF._diff(v1, v2)
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
        assert DIFF._diff(v1, v2) == {}

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
        assert DIFF._diff(v1, v2) == {}

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
        assert DIFF._diff(v1, v2) == {}


class TestNormalizeRelationships:
    def test_schema_level_keyed_by_from_to(self):
        items = [
            {"from": "orders.order_id", "to": "line_items.order_id", "type": "foreignKey"},
            {"from": "orders.customer_id", "to": "customers.customer_id", "type": "foreignKey"},
        ]
        result = ContractDiff._normalize_relationships(items, schema_level=True)
        assert "orders.order_id:line_items.order_id" in result
        assert "orders.customer_id:customers.customer_id" in result

    def test_property_level_keyed_by_to(self):
        items = [
            {"to": "customers.customer_id", "type": "foreignKey"},
        ]
        result = ContractDiff._normalize_relationships(items, schema_level=False)
        assert "customers.customer_id" in result

    def test_positional_fallback_when_fields_absent(self):
        items = [{"type": "foreignKey"}]
        result = ContractDiff._normalize_relationships(items, schema_level=True)
        assert "__pos_0__" in result

    def test_empty_list_returns_empty_dict(self):
        assert ContractDiff._normalize_relationships([], schema_level=True) == {}

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
        assert DIFF._diff(v1, v2) == {}

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
        assert DIFF._diff(v1, v2) == {}

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
        result = DIFF._diff(v1, v2)
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

        result = DIFF._diff(contract("foreignKey"), contract("reference"))
        assert "values_changed" in result


class TestNormalizeDescription:
    def test_description_purpose_change_detected(self):
        v1 = _contract(**{"description": {"purpose": "Provides order data"}})
        v2 = _contract(**{"description": {"purpose": "Provides order and line item data"}})
        result = DIFF._diff(v1, v2)
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
        result = DIFF._diff(v1, v2)
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
        assert DIFF._diff(v1, v2) == {}

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
        result = DIFF._diff(v1, v2)
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
        assert DIFF._diff(v1, v2) == {}

    def test_description_scalar_fields_all_detected(self):
        """purpose, usage, and limitations are all plain strings — changes must be detected."""
        for field in ("purpose", "usage", "limitations"):
            v1 = _contract(**{"description": {field: "original value"}})
            v2 = _contract(**{"description": {field: "updated value"}})
            result = DIFF._diff(v1, v2)
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
        result = DIFF._diff(v1, v2)
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
        assert DIFF._diff(v1, v2) == {}

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
        raw = DIFF._diff(v1, v2)
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
        result = DIFF._diff(v1, v2)
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
        result = DIFF._diff(v1, v2)
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
        result = DIFF._diff(v1, v2)
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
        result = DIFF._diff(v1, v2)
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
        assert DIFF._diff(v1, v2) == {}

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
        raw = DIFF._diff(v1, v2)
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
        assert DIFF._diff(v1, v2) == {}

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
        result = DIFF._diff(v1, v2)
        assert result != {}

    def test_property_quality_custom_property_change_detected(self):
        v1 = self._property_quality(
            [{"name": "positive", "type": "sql", "customProperties": [{"property": "priority", "value": "p1"}]}]
        )
        v2 = self._property_quality(
            [{"name": "positive", "type": "sql", "customProperties": [{"property": "priority", "value": "p2"}]}]
        )
        result = DIFF._diff(v1, v2)
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
        assert DIFF._diff(v1, v2) == {}

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
        assert DIFF._diff(v1, v2) == {}


class TestGeneratePriceDescriptionScalars(TestGenerate):
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
