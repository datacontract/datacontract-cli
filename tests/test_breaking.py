import io
import sys
from pathlib import Path

from rich.console import Console
from typer.testing import CliRunner

from datacontract.breaking.detector import BreakingChangeDetector
from datacontract.breaking.rules import (
    BreakingChangeRule,
    FieldRemovedRule,
    KeyConstraintRule,
    MetadataFallbackRule,
    RequiredChangedRule,
    RuleEvaluation,
    SchemaRemovedRule,
    TypeChangedRule,
    UniqueConstraintRule,
    ValidationConstraintRule,
)
from datacontract.cli import app
from datacontract.data_contract import DataContract
from datacontract.model.breaking import BreakingChangeLevel
from datacontract.model.changelog import ChangelogEntry, ChangelogResult, ChangelogType
from datacontract.output.text_breaking_results import write_text_breaking_results

V1 = "fixtures/changelog/integration/changelog_integration_v1.yaml"
V2 = "fixtures/changelog/integration/changelog_integration_v2.yaml"
WARNING_ONLY_V1 = "fixtures/changelog/breaking/warning_only_v1.yaml"
WARNING_ONLY_V2 = "fixtures/changelog/breaking/warning_only_v2.yaml"

GOLDEN_TEXT = Path(__file__).parent / "fixtures/changelog/golden_breaking_text.txt"

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


def test_adding_required_false_is_info():
    result = RequiredChangedRule().evaluate(
        _entry("schema.orders.properties.region.required", ChangelogType.added, None, "False")
    )
    assert result is not None
    assert result.level == BreakingChangeLevel.INFO


def test_adding_a_type_is_info():
    result = TypeChangedRule().evaluate(
        _entry("schema.orders.properties.region.logicalType", ChangelogType.added, None, "string")
    )
    assert result is not None
    assert result.level == BreakingChangeLevel.INFO


def test_removing_a_type_is_warning():
    result = TypeChangedRule().evaluate(
        _entry("schema.orders.properties.region.logicalType", ChangelogType.removed, "string")
    )
    assert result is not None
    assert result.level == BreakingChangeLevel.WARNING


def test_type_change_is_error():
    result = TypeChangedRule().evaluate(
        _entry("schema.orders.properties.order_id.logicalType", ChangelogType.updated, "string", "integer")
    )
    assert result is not None
    assert result.level == BreakingChangeLevel.ERROR


def test_removing_schema_is_breaking():
    result = SchemaRemovedRule().evaluate(_entry("schema.orders", ChangelogType.removed))
    assert result is not None
    assert result.level == BreakingChangeLevel.ERROR
    assert result.message == "Removed schema orders"


def test_removing_property_metadata_is_not_property_removal():
    result = FieldRemovedRule().evaluate(
        _entry("schema.orders.properties.customer_id.description", ChangelogType.removed, "old description")
    )
    assert result is None


def test_removing_property_is_breaking():
    result = FieldRemovedRule().evaluate(
        _entry("schema.orders.properties.customer_id", ChangelogType.removed, "string")
    )
    assert result is not None
    assert result.level == BreakingChangeLevel.ERROR
    assert result.message == "Removed property customer_id"


def test_removing_nested_property_is_breaking():
    result = FieldRemovedRule().evaluate(
        _entry("schema.orders.properties.customer.properties.email", ChangelogType.removed, "string")
    )
    assert result is not None
    assert result.level == BreakingChangeLevel.ERROR
    assert result.message == "Removed property email"


def test_removing_nested_property_metadata_is_not_property_removal():
    result = FieldRemovedRule().evaluate(
        _entry("schema.orders.properties.customer.properties.email.description", ChangelogType.removed, "old")
    )
    assert result is None


def test_tightening_uniqueness_is_breaking():
    result = UniqueConstraintRule().evaluate(
        _entry("schema.orders.properties.order_id.unique", ChangelogType.updated, "False", "True")
    )
    assert result is not None
    assert result.level == BreakingChangeLevel.ERROR


def test_changing_primary_key_is_warning():
    result = KeyConstraintRule().evaluate(
        _entry("schema.orders.properties.order_id.primaryKey", ChangelogType.updated, "True", "False")
    )
    assert result is not None
    assert result.level == BreakingChangeLevel.WARNING


def test_tightening_validation_constraint_is_breaking():
    result = ValidationConstraintRule().evaluate(
        _entry("schema.orders.properties.customer_id.minLength", ChangelogType.updated, "5", "10")
    )
    assert result is not None
    assert result.level == BreakingChangeLevel.ERROR


def test_tightening_date_validation_constraint_is_breaking():
    result = ValidationConstraintRule().evaluate(
        _entry(
            "schema.orders.properties.order_date.logicalTypeOptions.minimum",
            ChangelogType.updated,
            "2024-01-01",
            "2024-02-01",
        )
    )
    assert result is not None
    assert result.level == BreakingChangeLevel.ERROR


def test_relaxing_date_minimum_constraint_is_info():
    result = ValidationConstraintRule().evaluate(
        _entry(
            "schema.orders.properties.order_date.logicalTypeOptions.minimum",
            ChangelogType.updated,
            "2024-02-01",
            "2024-01-01",
        )
    )
    assert result is not None
    assert result.level == BreakingChangeLevel.INFO


def test_tightening_date_maximum_constraint_is_breaking():
    result = ValidationConstraintRule().evaluate(
        _entry(
            "schema.orders.properties.order_date.logicalTypeOptions.maximum",
            ChangelogType.updated,
            "2024-02-01",
            "2024-01-01",
        )
    )
    assert result is not None
    assert result.level == BreakingChangeLevel.ERROR


def test_relaxing_date_validation_constraint_is_info():
    result = ValidationConstraintRule().evaluate(
        _entry(
            "schema.orders.properties.order_date.logicalTypeOptions.maximum",
            ChangelogType.updated,
            "2024-01-01",
            "2024-02-01",
        )
    )
    assert result is not None
    assert result.level == BreakingChangeLevel.INFO


def test_invalid_date_validation_constraint_is_warning():
    result = ValidationConstraintRule().evaluate(
        _entry(
            "schema.orders.properties.order_date.logicalTypeOptions.minimum",
            ChangelogType.updated,
            "not-a-date",
            "2024-01-01",
        )
    )
    assert result is not None
    assert result.level == BreakingChangeLevel.WARNING


def test_unknown_change_is_info():
    result = MetadataFallbackRule().evaluate(_entry("description.purpose", ChangelogType.updated, "old", "new"))
    assert result.level == BreakingChangeLevel.INFO
    assert result.message == "Changed contract at description.purpose from 'old' to 'new'"


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


def test_required_inside_an_added_schema_is_not_breaking():
    changelog = ChangelogResult(
        v1="v1",
        v2="v2",
        entries=[
            _entry("schema.customers", ChangelogType.added),
            _entry("schema.customers.properties.customer_id", ChangelogType.added),
            _entry("schema.customers.properties.customer_id.required", ChangelogType.added, None, "True"),
        ],
    )
    result = BreakingChangeDetector().detect(changelog)
    assert all(entry.level == BreakingChangeLevel.INFO for entry in result.entries)
    assert not result.is_breaking


def test_required_added_to_an_existing_property_is_breaking():
    changelog = ChangelogResult(
        v1="v1",
        v2="v2",
        entries=[_entry("schema.orders.properties.order_id.required", ChangelogType.added, None, "True")],
    )
    result = BreakingChangeDetector().detect(changelog)
    assert result.is_breaking


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


def test_golden_output():
    result = DataContract(data_contract_file=V1).breaking(DataContract(data_contract_file=V2))
    assert len(result.entries) == len(
        DataContract(data_contract_file=V1).changelog(DataContract(data_contract_file=V2)).entries
    )
    buf = io.StringIO()
    con = Console(file=buf, width=300, highlight=False, no_color=True)
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        write_text_breaking_results(result, con)
    finally:
        sys.stdout = old_stdout
    assert buf.getvalue() == GOLDEN_TEXT.read_text(encoding="utf-8"), (
        "Breaking-change text output has changed. If intentional, regenerate "
        "golden_breaking_text.txt (see tests/fixtures/changelog/helper/generate_golden.py)."
    )


def test_data_contract_breaking_reuses_changelog():
    result = DataContract(data_contract_file=V1).breaking(DataContract(data_contract_file=V2))
    assert result.v1 == V1
    assert result.v2 == V2
    assert result.is_breaking


def test_cli_warning_only_change_exits_zero_but_shows_warning():
    result = runner.invoke(app, ["breaking", WARNING_ONLY_V1, WARNING_ONLY_V2])
    assert result.exit_code == 0
    assert "[ 1 Warning ]  [ 2 Info ]" in result.output


def test_cli_missing_file_exits_nonzero():
    result = runner.invoke(app, ["breaking", "unknown.yaml", "unknown.yaml"])
    assert result.exit_code == 1
    assert result.exception is not None
    assert "The file 'unknown.yaml' does not exist." in str(result.exception)


def test_cli_exits_nonzero_and_badges_errors_for_mixed_changes():
    result = runner.invoke(app, ["breaking", V1, V2])
    assert result.exit_code == 1
    assert "[ 3 Error ]  [ 5 Info ]" in result.output


def test_detector_uses_first_matching_rule():
    class FirstRule(BreakingChangeRule):
        rule_id = "first"

        def evaluate(self, entry):
            return RuleEvaluation(self.rule_id, BreakingChangeLevel.INFO, "first")

    class SecondRule(BreakingChangeRule):
        rule_id = "second"

        def evaluate(self, entry):
            return RuleEvaluation(self.rule_id, BreakingChangeLevel.WARNING, "second")

    result = BreakingChangeDetector((FirstRule(), SecondRule())).detect(
        ChangelogResult(v1="v1", v2="v2", entries=[_entry("field", ChangelogType.updated)])
    )

    assert result.entries[0].rule_id == "first"
    assert result.entries[0].level == BreakingChangeLevel.INFO
