from datacontract.data_contract import DataContract
from datacontract.model.changelog import ChangelogResult, ChangelogType

V1 = "fixtures/changelog/integration/changelog_integration_v1.yaml"
V2 = "fixtures/changelog/integration/changelog_integration_v2.yaml"


def test_changelog_returns_changelog_result():
    result = DataContract(data_contract_file=V1).changelog(DataContract(data_contract_file=V2))
    assert isinstance(result, ChangelogResult)


def test_changelog_has_changes():
    result = DataContract(data_contract_file=V1).changelog(DataContract(data_contract_file=V2))
    assert result.has_changes()


def test_changelog_no_changes():
    result = DataContract(data_contract_file=V1).changelog(DataContract(data_contract_file=V1))
    assert not result.has_changes()
    assert result.entries == []
    assert result.summary == []


def test_changelog_entry_types():
    result = DataContract(data_contract_file=V1).changelog(DataContract(data_contract_file=V2))
    types = {e.type for e in result.entries}
    assert ChangelogType.added in types
    assert ChangelogType.removed in types
    assert ChangelogType.updated in types


def test_changelog_summary_is_rolled_up():
    result = DataContract(data_contract_file=V1).changelog(DataContract(data_contract_file=V2))
    assert len(result.summary) < len(result.entries)


def test_changelog_summary_paths():
    result = DataContract(data_contract_file=V1).changelog(DataContract(data_contract_file=V2))
    paths = [e.path for e in result.summary]
    assert "schema.customers" in paths
    assert "schema.orders.properties.customer_id" in paths
    assert "slaProperties.availability" in paths


def test_changelog_entry_values():
    result = DataContract(data_contract_file=V1).changelog(DataContract(data_contract_file=V2))
    changed = [e for e in result.entries if e.path == "schema.orders.properties.order_date.logicalType"]
    assert len(changed) == 1
    assert changed[0].type == ChangelogType.updated
    assert changed[0].old_value == "string"
    assert changed[0].new_value == "date"


def test_changelog_v1_v2_labels():
    result = DataContract(data_contract_file=V1).changelog(DataContract(data_contract_file=V2))
    assert result.v1 == V1
    assert result.v2 == V2
