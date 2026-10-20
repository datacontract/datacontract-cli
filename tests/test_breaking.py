import io
import sys
from pathlib import Path

import pytest
import yaml
from rich.console import Console
from typer.testing import CliRunner

from datacontract.breaking.detector import BreakingChangeDetector
from datacontract.breaking.rules import (
    BreakingChangeRule,
    KeyConstraintRule,
    MetadataFallbackRule,
    PropertyAddedOrRemovedRule,
    RequiredChangedRule,
    RuleEvaluation,
    SchemaAddedOrRemovedRule,
    TypeChangedRule,
    UniqueConstraintRule,
    ValidationConstraintRule,
)
from datacontract.cli import app
from datacontract.data_contract import DataContract
from datacontract.model.breaking import BreakingChangeLevel, Direction, Perspective
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


def _direction(rule, entry):
    return rule.evaluate(entry, {}, {}).direction


def _detect(*entries, perspective=Perspective.CONSUMER, summary=()):
    changelog = ChangelogResult(v1="v1", v2="v2", summary=list(summary), entries=list(entries))
    return BreakingChangeDetector().detect(changelog, perspective, {}, {})


@pytest.mark.parametrize(
    "direction,consumer,producer",
    [
        (Direction.TIGHTENS, BreakingChangeLevel.INFO, BreakingChangeLevel.ERROR),
        (Direction.LOOSENS, BreakingChangeLevel.ERROR, BreakingChangeLevel.INFO),
        (Direction.BOTH, BreakingChangeLevel.ERROR, BreakingChangeLevel.ERROR),
        (Direction.UNDETERMINED, BreakingChangeLevel.WARNING, BreakingChangeLevel.WARNING),
        (Direction.UNTESTED, BreakingChangeLevel.INFO, BreakingChangeLevel.INFO),
    ],
)
def test_perspective_grades_direction(direction, consumer, producer):
    class FixedRule(BreakingChangeRule):
        rule_id = "fixed"

        def evaluate(self, entry, before, after):
            return RuleEvaluation(self.rule_id, direction, "fixed")

    changelog = ChangelogResult(v1="v1", v2="v2", entries=[_entry("field", ChangelogType.updated)])
    detector = BreakingChangeDetector((FixedRule(),))
    assert detector.detect(changelog, Perspective.CONSUMER, {}, {}).entries[0].level == consumer
    assert detector.detect(changelog, Perspective.PRODUCER, {}, {}).entries[0].level == producer


@pytest.mark.parametrize(
    "change_type,old,new,direction",
    [
        (ChangelogType.updated, "False", "True", Direction.TIGHTENS),
        (ChangelogType.updated, "true", "false", Direction.LOOSENS),
        (ChangelogType.added, None, "True", Direction.TIGHTENS),
        (ChangelogType.removed, "True", None, Direction.LOOSENS),
        (ChangelogType.added, None, "False", Direction.UNTESTED),
        (ChangelogType.updated, "True", "maybe", Direction.UNDETERMINED),
    ],
)
def test_required_direction(change_type, old, new, direction):
    entry = _entry("schema.orders.properties.customer_id.required", change_type, old, new)
    assert _direction(RequiredChangedRule(), entry) == direction


@pytest.mark.parametrize(
    "change_type,direction",
    [
        (ChangelogType.added, Direction.TIGHTENS),
        (ChangelogType.removed, Direction.LOOSENS),
        (ChangelogType.updated, Direction.BOTH),
    ],
)
def test_type_direction(change_type, direction):
    entry = _entry("schema.orders.properties.region.logicalType", change_type, "string", "integer")
    assert _direction(TypeChangedRule(), entry) == direction


def test_schema_physical_type_is_untested():
    entry = _entry("schema.orders.physicalType", ChangelogType.updated, "table", "view")
    assert TypeChangedRule().evaluate(entry, {}, {}) is None


def test_schema_added_or_removed():
    assert _direction(SchemaAddedOrRemovedRule(), _entry("schema.orders", ChangelogType.added)) == Direction.TIGHTENS
    removed = SchemaAddedOrRemovedRule().evaluate(_entry("schema.orders", ChangelogType.removed), {}, {})
    assert removed.direction == Direction.LOOSENS
    assert removed.message == "Removed schema orders"


@pytest.mark.parametrize(
    "path",
    ["schema.orders.properties.customer_id", "schema.orders.properties.customer.properties.email"],
)
def test_property_added_or_removed(path):
    assert _direction(PropertyAddedOrRemovedRule(), _entry(path, ChangelogType.added)) == Direction.TIGHTENS
    removed = PropertyAddedOrRemovedRule().evaluate(_entry(path, ChangelogType.removed, "string"), {}, {})
    assert removed.direction == Direction.LOOSENS
    assert removed.message == f"Removed property {path.rsplit('.', 1)[1]}"


def test_property_metadata_is_not_a_property():
    entry = _entry("schema.orders.properties.customer.properties.email.description", ChangelogType.removed, "old")
    assert PropertyAddedOrRemovedRule().evaluate(entry, {}, {}) is None


def test_uniqueness_direction():
    entry = _entry("schema.orders.properties.order_id.unique", ChangelogType.updated, "False", "True")
    assert _direction(UniqueConstraintRule(), entry) == Direction.TIGHTENS
    entry = _entry("schema.orders.properties.tags.logicalTypeOptions.uniqueItems", ChangelogType.removed, "True")
    assert _direction(UniqueConstraintRule(), entry) == Direction.LOOSENS


def test_single_primary_key_direction():
    entry = _entry("schema.orders.properties.order_id.primaryKey", ChangelogType.updated, "True", "False")
    assert _direction(KeyConstraintRule(), entry) == Direction.LOOSENS


@pytest.mark.parametrize(
    "path,old,new,direction",
    [
        ("schema.orders.properties.customer_id.minLength", "5", "10", Direction.TIGHTENS),
        ("schema.orders.properties.customer_id.maxLength", "5", "10", Direction.LOOSENS),
        ("schema.orders.properties.tags.logicalTypeOptions.minItems", "1", "2", Direction.TIGHTENS),
        ("schema.orders.properties.tags.logicalTypeOptions.maxItems", "1", "2", Direction.LOOSENS),
        (
            "schema.orders.properties.order_date.logicalTypeOptions.minimum",
            "2024-01-01",
            "2024-02-01",
            Direction.TIGHTENS,
        ),
        (
            "schema.orders.properties.order_date.logicalTypeOptions.minimum",
            "2024-02-01",
            "2024-01-01",
            Direction.LOOSENS,
        ),
        (
            "schema.orders.properties.order_date.logicalTypeOptions.maximum",
            "2024-02-01",
            "2024-01-01",
            Direction.TIGHTENS,
        ),
        (
            "schema.orders.properties.order_date.logicalTypeOptions.maximum",
            "2024-01-01",
            "2024-02-01",
            Direction.LOOSENS,
        ),
        (
            "schema.orders.properties.order_date.logicalTypeOptions.minimum",
            "not-a-date",
            "2024-01-01",
            Direction.UNDETERMINED,
        ),
        ("schema.orders.properties.order_id.logicalTypeOptions.pattern", "^[0-9]+$", "^\\d+$", Direction.UNDETERMINED),
    ],
)
def test_validation_constraint_direction(path, old, new, direction):
    assert _direction(ValidationConstraintRule(), _entry(path, ChangelogType.updated, old, new)) == direction


def test_adding_a_validation_constraint_tightens():
    entry = _entry("schema.orders.properties.code.logicalTypeOptions.pattern", ChangelogType.added, None, "^A")
    assert _direction(ValidationConstraintRule(), entry) == Direction.TIGHTENS


def test_unknown_change_is_untested():
    result = MetadataFallbackRule().evaluate(_entry("description.purpose", ChangelogType.updated, "old", "new"), {}, {})
    assert result.direction == Direction.UNTESTED
    assert result.message == "Changed contract at description.purpose from 'old' to 'new'"


def test_only_the_added_element_itself_is_graded():
    result = _detect(
        _entry("schema.customers", ChangelogType.added),
        _entry("schema.customers.properties.customer_id", ChangelogType.added),
        _entry("schema.customers.properties.customer_id.required", ChangelogType.added, None, "True"),
        perspective=Perspective.PRODUCER,
    )
    assert [(entry.direction, entry.level) for entry in result.entries] == [
        (Direction.TIGHTENS, BreakingChangeLevel.ERROR),
        (None, BreakingChangeLevel.INFO),
        (None, BreakingChangeLevel.INFO),
    ]


def test_summary_uses_highest_detail_severity():
    result = _detect(
        _entry("schema.orders.description", ChangelogType.updated, "old", "new"),
        _entry("schema.orders.properties.id", ChangelogType.removed, "string"),
        summary=[_entry("schema.orders", ChangelogType.updated)],
    )
    assert result.summary[0].level == BreakingChangeLevel.ERROR


def test_detector_uses_first_matching_rule():
    class FirstRule(BreakingChangeRule):
        rule_id = "first"

        def evaluate(self, entry, before, after):
            return RuleEvaluation(self.rule_id, Direction.UNTESTED, "first")

    class SecondRule(BreakingChangeRule):
        rule_id = "second"

        def evaluate(self, entry, before, after):
            return RuleEvaluation(self.rule_id, Direction.UNDETERMINED, "second")

    result = BreakingChangeDetector((FirstRule(), SecondRule())).detect(
        ChangelogResult(v1="v1", v2="v2", entries=[_entry("field", ChangelogType.updated)]),
        Perspective.CONSUMER,
        {},
        {},
    )
    assert result.entries[0].rule_id == "first"


def _contract(schema=None, sla=None):
    document = {
        "apiVersion": "v3.2.0",
        "kind": "DataContract",
        "id": "orders",
        "version": "1.0.0",
        "status": "active",
        "schema": schema or [{"name": "orders", "properties": [{"name": "id", "logicalType": "integer"}]}],
    }
    if sla is not None:
        document["slaProperties"] = sla
    return document


def _directions(v1, v2):
    result = DataContract(data_contract_str=yaml.safe_dump(v1)).breaking(
        DataContract(data_contract_str=yaml.safe_dump(v2))
    )
    return {entry.direction for entry in result.entries if entry.direction not in (None, Direction.UNTESTED)}


def _orders(**changes):
    prop = {"name": "id", "logicalType": "integer", **changes}
    return [{"name": "orders", "properties": [prop]}]


def _quality(**rule):
    return _orders(quality=[{"name": "q", "type": "library", "metric": "nullValues", **rule}])


def _freshness(value, unit="h", element="orders.created_at"):
    return [{"property": "freshness", "value": value, "unit": unit, **({"element": element} if element else {})}]


def _retention(value):
    return [{"property": "retention", "value": value, "element": "orders.created_at"}]


def _with_customers(*relationship):
    schema = _orders(relationships=list(relationship)) if relationship else _orders()
    return schema + [{"name": "customers", "properties": [{"name": "id"}, {"name": "account_id"}]}]


def _keyed(*names):
    return [{"name": "orders", "properties": [{"name": name, "primaryKey": name in names} for name in ("a", "b", "c")]}]


@pytest.mark.parametrize(
    "v1,v2,directions",
    [
        pytest.param(_contract(), _contract(_orders(physicalName="order_id")), {Direction.BOTH}, id="rename-column"),
        pytest.param(_contract(), _contract(_orders(physicalName="id")), set(), id="spell-out-name"),
        pytest.param(
            _contract([{"name": "sales.orders"}]),
            _contract([{"name": "sales.orders", "physicalName": "orders"}]),
            {Direction.BOTH},
            id="rename-dotted-table",
        ),
        pytest.param(
            _contract(
                _orders(logicalType="array", items={"logicalType": "string"}, logicalTypeOptions={"minItems": 1})
            ),
            _contract(
                _orders(logicalType="array", items={"logicalType": "string"}, logicalTypeOptions={"minItems": 2})
            ),
            {Direction.TIGHTENS},
            id="min-items",
        ),
        pytest.param(
            _contract(_with_customers()),
            _contract(_with_customers({"to": "customers.id"})),
            {Direction.TIGHTENS},
            id="relationship-added",
        ),
        pytest.param(
            _contract(_with_customers({"to": "customers.id"})),
            _contract(_with_customers()),
            {Direction.LOOSENS},
            id="relationship-removed",
        ),
        pytest.param(
            _contract(_with_customers({"id": "fk", "to": "customers.id"})),
            _contract(_with_customers({"id": "fk", "to": "customers.account_id"})),
            {Direction.BOTH},
            id="relationship-retargeted",
        ),
        pytest.param(
            _contract(sla=_freshness(24)), _contract(sla=_freshness(1)), {Direction.TIGHTENS}, id="freshness-shorter"
        ),
        pytest.param(
            _contract(sla=_freshness(24, "h")),
            _contract(sla=_freshness(1, "d")),
            set(),
            id="freshness-same-duration",
        ),
        pytest.param(
            _contract(sla=_freshness(1, "d")),
            _contract(sla=_freshness(48, "h")),
            {Direction.LOOSENS},
            id="freshness-longer",
        ),
        pytest.param(
            _contract(sla=_freshness(1)),
            _contract(sla=_freshness(1, element="orders.updated_at")),
            {Direction.BOTH},
            id="freshness-other-column",
        ),
        pytest.param(_contract(sla=_retention("P2Y")), _contract(sla=_retention("P1Y")), set(), id="retention"),
        pytest.param(_contract(), _contract(sla=_freshness(1)), {Direction.TIGHTENS}, id="freshness-added"),
        pytest.param(_contract(), _contract(sla=_freshness(1, element=None)), set(), id="freshness-added-unchecked"),
        pytest.param(
            _contract(sla=_freshness(24, element=None)),
            _contract(sla=_freshness(1, element=None)),
            set(),
            id="freshness-shorter-unchecked",
        ),
        pytest.param(
            _contract(sla=_freshness(24, element="other.created_at")),
            _contract(sla=_freshness(24)),
            {Direction.TIGHTENS},
            id="freshness-element-resolved",
        ),
        pytest.param(
            _contract(sla=[{"property": "latency", "value": "1s"}]),
            _contract(sla=[{"property": "latency", "value": "5s"}]),
            set(),
            id="untested-service-level",
        ),
        pytest.param(
            _contract(_quality(mustBeBetween=[0, 10])),
            _contract(_quality(mustBeBetween=[0, 20])),
            {Direction.LOOSENS},
            id="between-wider",
        ),
        pytest.param(
            _contract(_quality(mustBeBetween=[0, 10])),
            _contract(_quality(mustBeBetween=[5, 20])),
            {Direction.BOTH},
            id="between-shifted",
        ),
        pytest.param(
            _contract(_quality(mustNotBeBetween=[0, 10])),
            _contract(_quality(mustNotBeBetween=[0, 20])),
            {Direction.TIGHTENS},
            id="not-between-wider",
        ),
        pytest.param(
            _contract(_quality(mustBeLessThan=10)),
            _contract(_quality(mustBeLessThan=5)),
            {Direction.TIGHTENS},
            id="less-than-lowered",
        ),
        pytest.param(
            _contract(_quality(mustBeGreaterThan=10)),
            _contract(_quality(mustBeGreaterThan=5)),
            {Direction.LOOSENS},
            id="greater-than-lowered",
        ),
        pytest.param(
            _contract(_quality(mustBe=0)),
            _contract(_quality(mustBeLessThan=10)),
            {Direction.LOOSENS},
            id="threshold-replaced-by-wider",
        ),
        pytest.param(
            _contract(_quality(mustBeBetween=[0, 10])),
            _contract(_quality(mustBeLessThan=10)),
            {Direction.BOTH},
            id="threshold-replaced-by-overlapping",
        ),
        pytest.param(
            _contract(_quality(mustNotBe=0)),
            _contract(_quality(mustNotBeBetween=[0, 10])),
            {Direction.TIGHTENS},
            id="threshold-replaced-by-narrower-complement",
        ),
        pytest.param(
            _contract(_quality(mustBe=0)), _contract(_quality(mustBe=5)), {Direction.BOTH}, id="must-be-moved"
        ),
        pytest.param(
            _contract(_quality(mustBeLessThan=10)),
            _contract(_quality(mustBeLessThan=5, unit="percent")),
            {Direction.UNDETERMINED},
            id="threshold-in-other-unit",
        ),
        pytest.param(
            _contract(_quality(metric="invalidValues", arguments={"validValues": ["a", "b"]}, mustBe=0)),
            _contract(_quality(metric="invalidValues", arguments={"validValues": ["a", "b", "c"]}, mustBe=0)),
            {Direction.LOOSENS},
            id="valid-value-added",
        ),
        pytest.param(
            _contract(_orders(quality=[{"metric": "nullValues", "mustBe": 0}])),
            _contract(_orders(quality=[{"name": "no_nulls", "metric": "nullValues", "mustBe": 0}])),
            set(),
            id="rule-named",
        ),
        pytest.param(
            _contract(_orders(quality=[{"name": "a", "metric": "nullValues", "mustBe": 0}])),
            _contract(_orders(quality=[{"name": "b", "metric": "nullValues", "mustBe": 0}])),
            set(),
            id="rule-renamed",
        ),
        pytest.param(
            _contract(_orders(quality=[{"id": "q1", "name": "a", "metric": "nullValues", "mustBe": 0}])),
            _contract(_orders(quality=[{"id": "q1", "name": "b", "metric": "nullValues", "mustBe": 1}])),
            {Direction.BOTH},
            id="rule-paired-by-id",
        ),
        pytest.param(
            _contract(
                _orders(quality=[{"metric": "nullValues", "mustBe": 0}, {"metric": "duplicateValues", "mustBe": 0}])
            ),
            _contract(_orders(quality=[{"metric": "duplicateValues", "mustBeLessThan": 5}])),
            {Direction.LOOSENS},
            id="first-of-two-nameless-rules-removed",
        ),
        pytest.param(
            _contract(_quality(mustBeLessThan=10)),
            _contract(_quality(mustBeLessThan=10, unit="rows")),
            set(),
            id="unit-rows-declared",
        ),
        pytest.param(
            _contract(_quality(metric="nullValues", mustBeLessThan=5, unit="percent")),
            _contract(_quality(metric="nullValues", mustBeLessThan=5, unit="%")),
            set(),
            id="unit-percent-respelled",
        ),
        pytest.param(
            _contract(_quality(metric="invalidValues", arguments={"validValues": ["a", "b"]}, mustBe=0)),
            _contract(_quality(metric="invalidValues", arguments={"validValues": ["a"]}, mustBe=0)),
            {Direction.TIGHTENS},
            id="valid-value-removed",
        ),
        pytest.param(
            _contract(_quality(metric="missingValues", arguments={"missingValues": ["", "N/A"]}, mustBe=0)),
            _contract(_quality(metric="missingValues", arguments={"missingValues": ["", "N/A", "-"]}, mustBe=0)),
            {Direction.TIGHTENS},
            id="missing-value-marker-added",
        ),
        pytest.param(
            _contract(_quality(metric="nullValues", mustBe=0)),
            _contract(_quality(metric="missingValues", arguments={"missingValues": ["N/A"]}, mustBe=0)),
            {Direction.TIGHTENS},
            id="null-values-to-missing-values",
        ),
        pytest.param(
            _contract(
                [
                    {
                        "name": "orders",
                        "quality": [
                            {"name": "q", "metric": "duplicateValues", "arguments": {"properties": ["a"]}, "mustBe": 0}
                        ],
                    }
                ]
            ),
            _contract(
                [
                    {
                        "name": "orders",
                        "quality": [
                            {
                                "name": "q",
                                "metric": "duplicateValues",
                                "arguments": {"properties": ["a", "b"]},
                                "mustBe": 0,
                            }
                        ],
                    }
                ]
            ),
            {Direction.LOOSENS},
            id="duplicate-key-widened",
        ),
        pytest.param(
            _contract(_quality(type="sql", metric=None, query="SELECT COUNT(*) FROM orders", mustBe=0)),
            _contract(_quality(type="sql", metric=None, query="SELECT COUNT(*) FROM orders WHERE 1 = 1", mustBe=0)),
            {Direction.UNDETERMINED},
            id="query-changed",
        ),
        pytest.param(
            _contract(_quality(mustBe=0, method="reconciliation", schedule="0 * * * *", scheduler="cron")),
            _contract(_quality(mustBe=0, method="other", schedule="0 0 * * *", scheduler="cron")),
            set(),
            id="schedule-and-method-changed",
        ),
        pytest.param(_contract(), _contract(_quality(mustBe=0)), {Direction.TIGHTENS}, id="rule-added"),
        pytest.param(_contract(_quality(mustBe=0)), _contract(), {Direction.LOOSENS}, id="rule-removed"),
        pytest.param(
            _contract(), _contract(_orders(quality=[{"type": "text", "description": "Nice"}])), set(), id="text-rule"
        ),
        pytest.param(
            _contract(_orders(quality=[{"rule": "nullValues", "mustBe": 0}])),
            _contract(_orders(quality=[{"metric": "nullValues", "mustBe": 0}])),
            {Direction.TIGHTENS},
            id="rule-alias-replaced-by-metric",
        ),
        pytest.param(
            _contract(_quality(mustBe=0)),
            _contract(_quality(mustBe=0, severity="warning")),
            {Direction.LOOSENS},
            id="rule-made-warning",
        ),
        pytest.param(
            _contract(_orders(logicalTypeOptions={"minimum": 0})),
            _contract(_orders(logicalTypeOptions={"exclusiveMinimum": 0})),
            {Direction.TIGHTENS},
            id="minimum-made-exclusive",
        ),
        pytest.param(
            _contract(_orders(logicalTypeOptions={"maximum": 10})),
            _contract(_orders(logicalTypeOptions={"exclusiveMaximum": 20})),
            {Direction.LOOSENS},
            id="maximum-replaced-by-higher-exclusive",
        ),
        pytest.param(
            _contract(_orders(logicalType="timestamp", logicalTypeOptions={"minimum": "2024-01-01T00:00:00Z"})),
            _contract(_orders(logicalType="timestamp", logicalTypeOptions={"minimum": "2025-01-01T00:00:00Z"})),
            {Direction.TIGHTENS},
            id="timestamp-minimum-raised",
        ),
        pytest.param(
            _contract(_quality(mustBeGreaterThan=5)),
            _contract(_quality(mustBeGreaterOrEqualTo=6)),
            set(),
            id="same-row-count-threshold",
        ),
        pytest.param(
            _contract(_quality(metric="invalidValues", arguments={"validValues": ["a", "b"]}, mustBe=5)),
            _contract(_quality(metric="invalidValues", arguments={"validValues": ["a", "b", "c"]}, mustBe=5)),
            {Direction.BOTH},
            id="valid-value-added-to-exact-count",
        ),
        pytest.param(
            _contract(), _contract(_quality(metric="rowCount", mustBeGreaterThan=0)), set(), id="unrunnable-rule"
        ),
        pytest.param(
            _contract(_orders(logicalTypeOptions={"minimum": 0})),
            _contract(_orders(logicalTypeOptions={"exclusiveMinimum": -1})),
            set(),
            id="same-integer-bound",
        ),
        pytest.param(_contract(), _contract(_quality(mustBe=5, severity="warning")), set(), id="warning-rule"),
        pytest.param(
            _contract(_quality(mustBeLessThan=10, severity="warning")),
            _contract(_quality(mustBeLessThan=5, severity="warning")),
            set(),
            id="warning-rule-threshold",
        ),
        pytest.param(
            _contract(_quality(mustBeLessThan=10, severity="warning")),
            _contract(_quality(mustBeLessThan=5)),
            {Direction.TIGHTENS},
            id="warning-rule-made-blocking",
        ),
        pytest.param(_contract(_keyed()), _contract(_keyed("a")), {Direction.TIGHTENS}, id="key-added"),
        pytest.param(_contract(_keyed("a", "b")), _contract(_keyed("a", "b", "c")), {Direction.BOTH}, id="key-widened"),
        pytest.param(_contract(_keyed("a")), _contract(_keyed("a", "b")), {Direction.BOTH}, id="key-made-composite"),
    ],
)
def test_change_direction(v1, v2, directions):
    assert _directions(v1, v2) == directions


def test_replaced_threshold_is_graded_once():
    result = DataContract(data_contract_str=yaml.safe_dump(_contract(_quality(mustBe=0)))).breaking(
        DataContract(data_contract_str=yaml.safe_dump(_contract(_quality(mustBeLessThan=10))))
    )
    assert [(entry.path.rsplit(".", 1)[1], entry.direction) for entry in result.entries] == [
        ("mustBe", Direction.UNTESTED),
        ("mustBeLessThan", Direction.LOOSENS),
    ]


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
    assert result.perspective == Perspective.CONSUMER
    assert result.is_breaking


def test_cli_warning_only_change_exits_zero_but_shows_warning():
    result = runner.invoke(app, ["breaking", WARNING_ONLY_V1, WARNING_ONLY_V2])
    assert result.exit_code == 0
    assert "Perspective: consumer" in result.output
    assert "[ 1 Warning ]  [ 2 Info ]" in result.output


def test_cli_producer_perspective_breaks_on_an_added_property():
    result = runner.invoke(app, ["breaking", "--perspective", "producer", WARNING_ONLY_V1, WARNING_ONLY_V2])
    assert result.exit_code == 1
    assert "Perspective: producer" in result.output


def test_cli_missing_file_exits_nonzero():
    result = runner.invoke(app, ["breaking", "unknown.yaml", "unknown.yaml"])
    assert result.exit_code == 1
    assert result.exception is not None
    assert "The file 'unknown.yaml' does not exist." in str(result.exception)


def test_cli_exits_nonzero_for_mixed_changes():
    result = runner.invoke(app, ["breaking", V1, V2])
    assert result.exit_code == 1


def test_contract_strings_are_not_parsed_as_markup(capsys):
    contract = """
apiVersion: v3.0.2
kind: DataContract
id: orders
version: 1.0.0
status: active
schema:
  - name: orders
    properties:
      - name: "x[/]y"
        logicalType: string
        description: {description}
"""
    v1 = DataContract(data_contract_str=contract.format(description='"[link=http://e.io]c[/link]"'))
    v2 = DataContract(data_contract_str=contract.format(description='"plain"'))
    write_text_breaking_results(v1.breaking(v2), Console(file=io.StringIO(), force_terminal=True, width=300))
    out = capsys.readouterr().out
    assert "x[/]y" in out
    assert "[link=http://e.io]c[/link]" in out
    assert "\x1b]8;" not in out


def test_cli_yaml_error_names_the_file(tmp_path):
    broken = tmp_path / "v2.yaml"
    broken.write_text("kind: [broken\n")
    result = runner.invoke(app, ["breaking", V1, str(broken)])
    assert result.exit_code != 0
    assert f"Cannot parse YAML in '{broken}'" in str(result.exception)
