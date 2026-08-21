import pytest
from typer.testing import CliRunner

from datacontract.breaking.detector import BreakingChangeDetector
from datacontract.breaking.rules import (
    BreakingChangeRule,
    RequiredChangedRule,
    RuleEvaluation,
    TypeChangedRule,
)
from datacontract.cli import app
from datacontract.data_contract import DataContract
from datacontract.model.breaking import BreakingChangeLevel
from datacontract.model.changelog import ChangelogEntry, ChangelogResult, ChangelogType

V1 = "fixtures/changelog/integration/changelog_integration_v1.yaml"
V2 = "fixtures/changelog/integration/changelog_integration_v2.yaml"
WARNING_ONLY_V1 = "fixtures/changelog/breaking/warning_only_v1.yaml"
WARNING_ONLY_V2 = "fixtures/changelog/breaking/warning_only_v2.yaml"

runner = CliRunner()


def _entry(path, change_type, old_value=None, new_value=None):
    return ChangelogEntry(path=path, type=change_type, old_value=old_value, new_value=new_value)


def test_required_change_to_true_is_error():
    result = RequiredChangedRule().evaluate(
        _entry("schema.orders.properties.customer_id.required", ChangelogType.updated, "False", "True")
    )
    assert result is not None
    assert result.level == BreakingChangeLevel.ERROR


def test_required_change_to_false_is_info():
    result = RequiredChangedRule().evaluate(
        _entry("schema.orders.properties.customer_id.required", ChangelogType.updated, "true", "false")
    )
    assert result is not None
    assert result.level == BreakingChangeLevel.INFO


def test_type_change_is_error():
    result = TypeChangedRule().evaluate(
        _entry("schema.orders.properties.order_id.logicalType", ChangelogType.updated, "string", "integer")
    )
    assert result is not None
    assert result.level == BreakingChangeLevel.ERROR


def test_unmatched_entry_uses_info_fallback():
    changelog = ChangelogResult(
        v1="v1",
        v2="v2",
        entries=[_entry("description.purpose", ChangelogType.updated, "old", "new")],
    )
    result = BreakingChangeDetector().detect(changelog)
    assert result.entries[0].level == BreakingChangeLevel.INFO
    assert result.entries[0].rule_id == "metadata-or-unknown-change"
    assert not result.is_breaking


def test_summary_uses_highest_detail_severity():
    changelog = ChangelogResult(
        v1="v1",
        v2="v2",
        summary=[_entry("schema.orders", ChangelogType.updated)],
        entries=[
            _entry("schema.orders.description", ChangelogType.updated, "old", "new"),
            _entry("schema.orders.properties.id", ChangelogType.removed, "string"),
        ],
    )
    result = BreakingChangeDetector().detect(changelog)
    assert result.summary[0].level == BreakingChangeLevel.ERROR


def test_every_detail_entry_is_classified():
    changelog = DataContract(data_contract_file=V1).changelog(DataContract(data_contract_file=V2))
    result = BreakingChangeDetector().detect(changelog)
    assert len(result.entries) == len(changelog.entries)
    assert all(isinstance(entry.level, BreakingChangeLevel) for entry in result.entries)


def test_data_contract_breaking_reuses_changelog():
    result = DataContract(data_contract_file=V1).breaking(DataContract(data_contract_file=V2))
    assert result.v1 == V1
    assert result.v2 == V2
    assert result.is_breaking


def test_cli_warning_only_change_exits_zero_but_shows_warning():
    result = runner.invoke(app, ["breaking", WARNING_ONLY_V1, WARNING_ONLY_V2])
    assert result.exit_code == 0
    assert "[ 1 Warning ]  [ 1 Info ]" in result.output


def test_cli_missing_file_exits_nonzero():
    result = runner.invoke(app, ["breaking", "unknown.yaml", "unknown.yaml"])
    assert result.exit_code == 1
    assert result.exception is not None
    assert "The file 'unknown.yaml' does not exist." in str(result.exception)


def test_cli_shows_full_severity_range_for_mixed_changes():
    result = runner.invoke(app, ["breaking", V1, V2])
    assert result.exit_code == 1
    assert "[ 4 Error ]  [ 1 Warning ]  [ 3 Info ]" in result.output


def test_detector_rejects_ambiguous_rules():
    class FirstRule(BreakingChangeRule):
        priority = 10
        rule_id = "first"

        def evaluate(self, entry):
            return RuleEvaluation(self.rule_id, BreakingChangeLevel.INFO, "first")

    class SecondRule(BreakingChangeRule):
        priority = 10
        rule_id = "second"

        def evaluate(self, entry):
            return RuleEvaluation(self.rule_id, BreakingChangeLevel.WARNING, "second")

    with pytest.raises(ValueError, match="Ambiguous"):
        BreakingChangeDetector((FirstRule(), SecondRule())).detect(
            ChangelogResult(v1="v1", v2="v2", entries=[_entry("field", ChangelogType.updated)])
        )
