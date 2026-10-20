import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone

from open_data_contract_standard.model import DataQuality
from pydantic import ValidationError

from datacontract.engines.checks.create_checks import (
    freshness_value_to_seconds,
    is_percent_unit,
    to_threshold,
    unrunnable_reason,
)
from datacontract.engines.checks.custom_quality_check import ENGINE as CUSTOM_CHECK_ENGINE
from datacontract.engines.checks.severity import failure_result
from datacontract.model.breaking import Direction
from datacontract.model.changelog import ChangelogEntry, ChangelogType
from datacontract.model.run import ResultEnum

# In the order to_threshold reads them.
_THRESHOLDS = (
    "mustBe",
    "mustNotBe",
    "mustBeGreaterThan",
    "mustBeGreaterOrEqualTo",
    "mustBeLessThan",
    "mustBeLessOrEqualTo",
    "mustBeBetween",
    "mustNotBeBetween",
)


@dataclass(frozen=True)
class RuleEvaluation:
    rule_id: str
    direction: Direction
    message: str


class BreakingChangeRule(ABC):
    rule_id: str

    @abstractmethod
    def evaluate(self, entry: ChangelogEntry, before: dict, after: dict) -> RuleEvaluation | None:
        """The direction of ``entry`` when this rule applies; ``before`` and ``after`` are the normalized contracts."""


class SchemaAddedOrRemovedRule(BreakingChangeRule):
    rule_id = "schema-added-or-removed"

    def evaluate(self, entry: ChangelogEntry, before: dict, after: dict) -> RuleEvaluation | None:
        segments = entry.path.split(".")
        if len(segments) != 2 or segments[0] != "schema":
            return None
        if entry.type == ChangelogType.added:
            return RuleEvaluation(self.rule_id, Direction.TIGHTENS, f"Added schema {segments[1]}")
        if entry.type == ChangelogType.removed:
            return RuleEvaluation(self.rule_id, Direction.LOOSENS, f"Removed schema {segments[1]}")
        return None


class PropertyAddedOrRemovedRule(BreakingChangeRule):
    rule_id = "property-added-or-removed"

    def evaluate(self, entry: ChangelogEntry, before: dict, after: dict) -> RuleEvaluation | None:
        segments = entry.path.split(".")
        if not _is_schema_property_path(segments):
            return None
        if entry.type == ChangelogType.added:
            return RuleEvaluation(self.rule_id, Direction.TIGHTENS, f"Added property {segments[-1]}")
        if entry.type == ChangelogType.removed:
            return RuleEvaluation(self.rule_id, Direction.LOOSENS, f"Removed property {segments[-1]}")
        return None


class PhysicalNameChangedRule(BreakingChangeRule):
    rule_id = "physical-name-changed"

    def evaluate(self, entry: ChangelogEntry, before: dict, after: dict) -> RuleEvaluation | None:
        if not entry.path.startswith("schema.") or not entry.path.endswith(".physicalName"):
            return None
        owner = entry.path.removesuffix(".physicalName")
        # Schema and property names may contain dots (sales.orders).
        name = owner.rsplit(".properties.", 1)[1] if ".properties." in owner else owner.removeprefix("schema.")
        direction = Direction.UNTESTED if (entry.old_value or name) == (entry.new_value or name) else Direction.BOTH
        return RuleEvaluation(self.rule_id, direction, _change_message("physical name", entry))


class RequiredChangedRule(BreakingChangeRule):
    rule_id = "required-changed"

    def evaluate(self, entry: ChangelogEntry, before: dict, after: dict) -> RuleEvaluation | None:
        if not entry.path.startswith("schema.") or not entry.path.endswith(".required"):
            return None
        return RuleEvaluation(self.rule_id, _flag_direction(entry), _change_message("requiredness", entry))


class TypeChangedRule(BreakingChangeRule):
    rule_id = "type-changed"

    def evaluate(self, entry: ChangelogEntry, before: dict, after: dict) -> RuleEvaluation | None:
        # schema.<name>.physicalType is the kind of table (table, view), which no check reads.
        if (
            not entry.path.startswith("schema.")
            or len(entry.path.split(".")) < 5
            or not entry.path.endswith((".logicalType", ".physicalType"))
        ):
            return None
        if entry.type == ChangelogType.updated:
            direction = Direction.BOTH
        elif entry.type == ChangelogType.added:
            direction = Direction.TIGHTENS
        else:
            direction = Direction.LOOSENS
        return RuleEvaluation(self.rule_id, direction, _change_message("type", entry))


class UniqueConstraintRule(BreakingChangeRule):
    rule_id = "unique-constraint-changed"

    def evaluate(self, entry: ChangelogEntry, before: dict, after: dict) -> RuleEvaluation | None:
        if not entry.path.startswith("schema.") or not entry.path.endswith((".unique", ".uniqueItems")):
            return None
        return RuleEvaluation(self.rule_id, _flag_direction(entry), _change_message("uniqueness", entry))


class KeyConstraintRule(BreakingChangeRule):
    rule_id = "key-constraint-changed"

    def evaluate(self, entry: ChangelogEntry, before: dict, after: dict) -> RuleEvaluation | None:
        if not entry.path.startswith("schema."):
            return None
        if entry.path.endswith(".primaryKeyPosition"):
            # A composite key is unique as a set of columns, whatever their order.
            return RuleEvaluation(self.rule_id, Direction.UNTESTED, _change_message("key constraint", entry))
        if not entry.path.endswith((".primaryKey", ".primary_key")):
            return None
        direction = _flag_direction(entry)
        schema_path = entry.path.split(".properties.", 1)[0]
        is_composite = any(
            sum(
                1
                for prop in ((_lookup(tree, schema_path) or {}).get("properties") or {}).values()
                if prop.get("primaryKey")
            )
            > 1
            for tree in (before, after)
        )
        if is_composite and direction in (Direction.TIGHTENS, Direction.LOOSENS):
            # A column joining or leaving a composite key changes both its not-null and the key's uniqueness.
            direction = Direction.BOTH
        return RuleEvaluation(self.rule_id, direction, _change_message("key constraint", entry))


class ValidationConstraintRule(BreakingChangeRule):
    rule_id = "validation-constraint-changed"
    _suffixes = (
        ".pattern",
        ".minLength",
        ".maxLength",
        ".minimum",
        ".maximum",
        ".exclusiveMinimum",
        ".exclusiveMaximum",
        ".minItems",
        ".maxItems",
    )
    _bounds = (("minimum", "exclusiveMinimum"), ("maximum", "exclusiveMaximum"))

    def evaluate(self, entry: ChangelogEntry, before: dict, after: dict) -> RuleEvaluation | None:
        if not entry.path.startswith("schema.") or not entry.path.endswith(self._suffixes):
            return None
        options_path, key = entry.path.rsplit(".", 1)
        old_options, new_options = (_lookup(tree, options_path) or {} for tree in (before, after))
        group = next((group for group in self._bounds if key in group), ())
        if entry.type != ChangelogType.updated and any(
            options.get(other) is not None for other in group if other != key for options in (old_options, new_options)
        ):
            # An inclusive bound replaced by an exclusive one, or the reverse: compare what both versions accept.
            old_bounds, new_bounds = (
                {k: _parse_number(str(options[k])) for k in group if options.get(k) is not None}
                for options in (old_options, new_options)
            )
            if key != _carrier(old_options, new_options, group):
                direction = Direction.UNTESTED
            elif None in (*old_bounds.values(), *new_bounds.values()):
                direction = Direction.UNDETERMINED
            else:
                property_type = (_lookup(after, options_path.removesuffix(".logicalTypeOptions")) or {}).get(
                    "logicalType"
                )
                probes = _probes([*old_bounds.values(), *new_bounds.values()], integers=property_type == "integer")

                def accepts(bounds: dict, value: float) -> bool:
                    return all(
                        {
                            "minimum": value >= b,
                            "exclusiveMinimum": value > b,
                            "maximum": value <= b,
                            "exclusiveMaximum": value < b,
                        }[k]
                        for k, b in bounds.items()
                    )

                direction = _accepted_direction(
                    lambda value: accepts(old_bounds, value), lambda value: accepts(new_bounds, value), probes
                )
        elif entry.type == ChangelogType.added:
            direction = Direction.TIGHTENS
        elif entry.type == ChangelogType.removed:
            direction = Direction.LOOSENS
        elif entry.path.endswith(".pattern"):
            direction = Direction.UNDETERMINED
        else:
            direction = _ordered_direction(entry.path, _parse_number(entry.old_value), _parse_number(entry.new_value))
        return RuleEvaluation(self.rule_id, direction, _change_message("validation constraint", entry))


class EnumConstraintRule(BreakingChangeRule):
    rule_id = "enum-constraint-changed"

    def evaluate(self, entry: ChangelogEntry, before: dict, after: dict) -> RuleEvaluation | None:
        if not entry.path.startswith("schema.") or ".properties." not in entry.path:
            return None
        if entry.path.endswith(".enum"):
            direction = Direction.TIGHTENS if entry.type == ChangelogType.added else Direction.LOOSENS
        elif (
            ".enum." in entry.path
            and entry.path.endswith(".value")
            and ".customProperties." not in entry.path.rsplit(".enum.", 1)[1]
            and ".authoritativeDefinitions." not in entry.path.rsplit(".enum.", 1)[1]
        ):
            # Stable IDs may change or swap without changing the set of allowed values.
            enum_path = entry.path.rsplit(".enum.", 1)[0] + ".enum"
            old_values, new_values = (
                {str(item.get("value")) for item in (_lookup(tree, enum_path) or {}).values() if isinstance(item, dict)}
                for tree in (before, after)
            )
            removes = entry.old_value is not None and entry.old_value not in new_values
            adds = entry.new_value is not None and entry.new_value not in old_values
            if removes and adds:
                direction = Direction.BOTH
            elif removes:
                direction = Direction.TIGHTENS
            elif adds:
                direction = Direction.LOOSENS
            else:
                direction = Direction.UNTESTED
        else:
            return None
        return RuleEvaluation(self.rule_id, direction, _change_message("allowed values", entry))


class RelationshipChangedRule(BreakingChangeRule):
    rule_id = "relationship-changed"

    def evaluate(self, entry: ChangelogEntry, before: dict, after: dict) -> RuleEvaluation | None:
        if not entry.path.startswith("schema.") or ".relationships." not in entry.path:
            return None
        owner, _, rest = entry.path.rpartition(".relationships.")
        container = f"{owner}.relationships"
        relationships = {**(_lookup(before, container) or {}), **(_lookup(after, container) or {})}
        # A relationship key may contain dots (customers.id), so match it against the known keys.
        key = max((k for k in relationships if rest == k or rest.startswith(f"{k}.")), key=len, default=None)
        if key is None:
            return None
        field = rest[len(key) + 1 :]
        if field == "type":
            was_checked = (entry.old_value or "foreignKey") == "foreignKey"
            is_checked = (entry.new_value or "foreignKey") == "foreignKey"
            if was_checked == is_checked:
                direction = Direction.UNTESTED
            else:
                direction = Direction.TIGHTENS if is_checked else Direction.LOOSENS
        elif (relationships[key].get("type") or "foreignKey") != "foreignKey":
            direction = Direction.UNTESTED
        elif not field:
            direction = Direction.TIGHTENS if entry.type == ChangelogType.added else Direction.LOOSENS
        elif field.split(".")[0] in ("from", "to"):
            direction = Direction.BOTH
        else:
            direction = Direction.UNTESTED
        return RuleEvaluation(self.rule_id, direction, _change_message("relationship", entry))


class FreshnessChangedRule(BreakingChangeRule):
    rule_id = "freshness-changed"

    def evaluate(self, entry: ChangelogEntry, before: dict, after: dict) -> RuleEvaluation | None:
        segments = entry.path.split(".")
        if len(segments) < 2 or segments[0] != "slaProperties" or segments[1] != "freshness":
            return None
        sla_path = ".".join(segments[:2])
        old_sla, new_sla = _lookup(before, sla_path) or {}, _lookup(after, sla_path) or {}
        # datacontract test checks freshness only with a value and an element naming a model.field of the contract.
        was_checked, is_checked = (
            sla.get("value") is not None
            and str(sla.get("element") or "").count(".") == 1
            and str(sla["element"]).split(".")[0] in (tree.get("schema") or {})
            for sla, tree in ((old_sla, before), (new_sla, after))
        )
        field = segments[2] if len(segments) > 2 else None
        if not was_checked and not is_checked:
            direction = Direction.UNTESTED
        elif was_checked != is_checked:
            direction = Direction.TIGHTENS if is_checked else Direction.LOOSENS
        elif field == "element":
            direction = Direction.BOTH
        elif field in ("value", "unit"):
            old_seconds = freshness_value_to_seconds(old_sla["value"], old_sla.get("unit"))
            new_seconds = freshness_value_to_seconds(new_sla["value"], new_sla.get("unit"))
            if old_seconds is None or new_seconds is None:
                direction = Direction.UNDETERMINED
            elif old_seconds == new_seconds:
                direction = Direction.UNTESTED
            else:
                direction = Direction.TIGHTENS if new_seconds < old_seconds else Direction.LOOSENS
        else:
            direction = Direction.UNTESTED
        return RuleEvaluation(self.rule_id, direction, _change_message("freshness", entry))


class QualityConstraintRule(BreakingChangeRule):
    rule_id = "quality-constraint-changed"
    # The list arguments a library metric reads, and whether adding a value to one counts more bad rows.
    _counting_arguments = {
        ("invalidValues", "validValues"): False,
        ("missingValues", "missingValues"): True,
        ("duplicateValues", "properties"): False,
    }
    _unchecked_fields = (
        "id",
        "name",
        "rule",
        "description",
        "dimension",
        "businessImpact",
        "method",
        "schedule",
        "scheduler",
        "severity",
        "tags",
        "customProperties",
        "authoritativeDefinitions",
    )

    def evaluate(self, entry: ChangelogEntry, before: dict, after: dict) -> RuleEvaluation | None:
        if not entry.path.startswith("schema.") or ".quality." not in entry.path:
            return None
        quality_path, rule_path = entry.path.rsplit(".quality.", 1)
        name, _, field = rule_path.partition(".")
        old_rule, new_rule = (
            rule if isinstance(rule, dict) else {}
            for rule in (_lookup(tree, f"{quality_path}.quality.{name}") for tree in (before, after))
        )
        at_property = ".properties." in quality_path
        was_guarantee, is_guarantee = (_is_guarantee(rule, at_property) for rule in (old_rule, new_rule))
        metric = new_rule.get("metric")
        top, _, rest = field.partition(".")
        argument = rest.split(".")[0] if top == "arguments" and rest else None
        if not was_guarantee and not is_guarantee:
            direction = Direction.UNTESTED
        elif not field:
            direction = Direction.TIGHTENS if entry.type == ChangelogType.added else Direction.LOOSENS
        elif was_guarantee != is_guarantee:
            decisive = ("severity", "type", "engine", "implementation", "metric", "query", "arguments", "unit")
            if top == _carrier(old_rule, new_rule, (*decisive, *_THRESHOLDS)):
                direction = Direction.TIGHTENS if is_guarantee else Direction.LOOSENS
            else:
                direction = Direction.UNTESTED
        elif top == "arguments" and new_rule.get("type") not in ("sql", "custom") and metric is not None:
            if old_rule.get("metric") != metric:
                # The metric entry carries the change.
                direction = Direction.UNTESTED
            elif argument is None:
                # The whole block added or removed: only missingValues runs without it, counting nulls alone.
                if metric != "missingValues":
                    direction = Direction.UNDETERMINED
                else:
                    direction = _count_direction(new_rule, more=entry.type == ChangelogType.added)
            elif (metric, argument) in self._counting_arguments and entry.type != ChangelogType.updated:
                more = self._counting_arguments[(metric, argument)] == (entry.type == ChangelogType.added)
                direction = _count_direction(new_rule, more)
            elif (metric, argument) in self._counting_arguments or (metric, argument) == ("invalidValues", "pattern"):
                direction = Direction.UNDETERMINED
            else:
                direction = Direction.UNTESTED
        elif field in _THRESHOLDS:
            old, new = to_threshold(_threshold_quality(old_rule)), to_threshold(_threshold_quality(new_rule))
            percent = {_is_percent(rule) for rule in (old_rule, new_rule)}
            if field != _carrier(old_rule, new_rule, _THRESHOLDS):
                direction = Direction.UNTESTED
            elif old is None or new is None or len(percent) > 1:
                direction = Direction.UNDETERMINED
            else:
                probes = _probes(
                    [bound for t in (old, new) for bound in (t.value, t.value2) if bound is not None],
                    # A library metric counts rows, unless it is a percentage of them.
                    integers=not percent.pop() and new_rule.get("type") not in ("sql", "custom"),
                )
                direction = (
                    Direction.UNDETERMINED if probes is None else _accepted_direction(old.passes, new.passes, probes)
                )
        elif field == "metric" and {old_rule.get("metric"), metric} == {"nullValues", "missingValues"}:
            missing_rule = new_rule if metric == "missingValues" else old_rule
            markers = [v for v in (missing_rule.get("arguments") or {}).get("missingValues") or [] if v is not None]
            direction = _count_direction(new_rule, more=metric == "missingValues") if markers else Direction.UNTESTED
        elif field == "unit":
            direction = Direction.UNTESTED if _is_percent(old_rule) == _is_percent(new_rule) else Direction.UNDETERMINED
        elif top in self._unchecked_fields:
            direction = Direction.UNTESTED
        else:
            # What the rule checks changed: its type, metric, query, engine, implementation or custom check arguments.
            direction = Direction.UNDETERMINED
        subject = f"{field} of quality rule '{name}'" if field else "quality rule"
        return RuleEvaluation(self.rule_id, direction, _change_message(subject, entry))


class VectorShapeRule(BreakingChangeRule):
    rule_id = "vector-shape-changed"

    def evaluate(self, entry: ChangelogEntry, before: dict, after: dict) -> RuleEvaluation | None:
        if not entry.path.startswith("schema.") or not entry.path.endswith(
            (".logicalTypeOptions.dimensions", ".logicalTypeOptions.elementType")
        ):
            return None
        if entry.path.endswith(".elementType"):
            old = entry.old_value or "float32"
            new = entry.new_value or "float32"
            direction = Direction.UNTESTED if old == new else Direction.BOTH
        else:
            direction = {
                ChangelogType.added: Direction.TIGHTENS,
                ChangelogType.removed: Direction.LOOSENS,
            }.get(entry.type, Direction.BOTH)
        return RuleEvaluation(self.rule_id, direction, _change_message("vector shape", entry))


class MetadataFallbackRule(BreakingChangeRule):
    rule_id = "metadata-or-unknown-change"

    def evaluate(self, entry: ChangelogEntry, before: dict, after: dict) -> RuleEvaluation:
        return RuleEvaluation(self.rule_id, Direction.UNTESTED, _change_message("contract", entry))


def _lookup(tree, path: str):
    """The value at a dotted changelog path; a key may itself contain dots."""
    if not path:
        return tree
    if not isinstance(tree, dict):
        return None
    for key in sorted(tree, key=lambda k: -len(str(k))):
        if path == str(key):
            return tree[key]
        if path.startswith(f"{key}."):
            found = _lookup(tree[key], path[len(str(key)) + 1 :])
            if found is not None:
                return found
    return None


def _is_schema_property_path(segments: list[str]) -> bool:
    return len(segments) >= 3 and segments[0] == "schema" and segments[-2] == "properties"


def _flag_direction(entry: ChangelogEntry) -> Direction:
    """Direction of a boolean constraint, which is off when absent."""
    old = False if entry.old_value is None else _parse_bool(entry.old_value)
    new = False if entry.new_value is None else _parse_bool(entry.new_value)
    if old is None or new is None:
        return Direction.UNDETERMINED
    if old == new:
        return Direction.UNTESTED
    return Direction.TIGHTENS if new else Direction.LOOSENS


def _ordered_direction(path: str, old: float | None, new: float | None) -> Direction:
    if old is None or new is None:
        return Direction.UNDETERMINED
    if old == new:
        return Direction.UNTESTED
    if path.endswith((".minLength", ".minimum", ".exclusiveMinimum", ".minItems")):
        return Direction.TIGHTENS if new > old else Direction.LOOSENS
    return Direction.TIGHTENS if new < old else Direction.LOOSENS


def _is_guarantee(rule: dict, at_property: bool) -> bool:
    """Whether datacontract test turns a quality rule into a check that can fail, as _quality_rule_checks does."""
    if failure_result(rule.get("severity")) != ResultEnum.failed:
        return False
    if rule.get("type") == "custom" and rule.get("engine") == "soda" and rule.get("implementation"):
        return False
    if rule.get("type") == "custom" and rule.get("engine") == CUSTOM_CHECK_ENGINE:
        return True
    if to_threshold(_threshold_quality(rule)) is None:
        return False
    if rule.get("type") == "sql":
        return rule.get("query") is not None
    if rule.get("metric") is None:
        return False
    try:
        quality = DataQuality.model_validate({k: rule[k] for k in ("metric", "unit", "arguments") if k in rule})
    except ValidationError:
        return False
    return unrunnable_reason(quality, "property" if at_property else None) is None


def _threshold_quality(rule: dict) -> DataQuality:
    """The thresholds of a normalized quality rule, ready for to_threshold."""
    try:
        return DataQuality.model_validate({k: v for k, v in rule.items() if k in _THRESHOLDS})
    except ValidationError:
        return DataQuality()


def _is_percent(rule: dict) -> bool:
    return is_percent_unit(DataQuality(unit=rule.get("unit")))


def _carrier(old: dict, new: dict, keys: tuple[str, ...]) -> str | None:
    """Of ``keys`` changing together, the one whose entry carries the change: the first set in v2, else removed."""
    changed = [key for key in keys if old.get(key) != new.get(key)]
    return next((key for key in changed if new.get(key) is not None), next(iter(changed), None))


def _count_direction(rule: dict, more: bool) -> Direction:
    """How counting more (or fewer) bad rows moves a quality rule, judged by the threshold it is checked against."""
    threshold = to_threshold(_threshold_quality(rule))
    probes = (
        None if threshold is None else _probes([0, threshold.value, threshold.value2], integers=not _is_percent(rule))
    )
    if probes is None:
        return Direction.UNDETERMINED
    accepted = [threshold.passes(p) for p in probes if p >= 0]
    if all(accepted) or not any(accepted):
        return Direction.UNTESTED
    if accepted == sorted(accepted, reverse=True):
        # Passes up to a limit: more bad rows can only fail it.
        return Direction.TIGHTENS if more else Direction.LOOSENS
    if accepted == sorted(accepted):
        return Direction.LOOSENS if more else Direction.TIGHTENS
    return Direction.BOTH


def _probes(bounds: list, integers: bool) -> list[float] | None:
    """Values that tell apart any predicates on numbers that change their answer only at ``bounds``; None if not numbers."""
    bounds = sorted({bound for bound in bounds if bound is not None})
    if not all(isinstance(bound, (int, float)) and not isinstance(bound, bool) for bound in bounds):
        return None
    if integers:
        return sorted({n for bound in bounds for n in range(math.floor(bound) - 1, math.ceil(bound) + 2)})
    return bounds + [(a + b) / 2 for a, b in zip(bounds, bounds[1:])] + [bounds[0] - 1, bounds[-1] + 1]


def _accepted_direction(old_accepts, new_accepts, probes: list[float]) -> Direction:
    loosens = any(new_accepts(p) and not old_accepts(p) for p in probes)
    tightens = any(old_accepts(p) and not new_accepts(p) for p in probes)
    if loosens and tightens:
        return Direction.BOTH
    if loosens:
        return Direction.LOOSENS
    return Direction.TIGHTENS if tightens else Direction.UNTESTED


def _parse_bool(value: str) -> bool | None:
    normalized = value.strip().lower()
    if normalized in {"true", "1"}:
        return True
    if normalized in {"false", "0"}:
        return False
    return None


def _parse_number(value: str | None) -> float | None:
    if value is None:
        return None
    normalized = value.strip()
    try:
        return float(normalized)
    except ValueError:
        pass
    try:
        # Python 3.10 reads no "Z" suffix.
        parsed = datetime.fromisoformat(f"{normalized[:-1]}+00:00" if normalized.endswith("Z") else normalized)
    except ValueError:
        return None
    return (parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)).timestamp()


def _change_message(subject: str, entry: ChangelogEntry) -> str:
    if entry.type == ChangelogType.added:
        return f"Added {subject} at {entry.path}"
    if entry.type == ChangelogType.removed:
        return f"Removed {subject} at {entry.path}"
    return f"Changed {subject} at {entry.path} from {entry.old_value!r} to {entry.new_value!r}"


DEFAULT_RULES: tuple[BreakingChangeRule, ...] = (
    QualityConstraintRule(),
    RelationshipChangedRule(),
    FreshnessChangedRule(),
    PhysicalNameChangedRule(),
    RequiredChangedRule(),
    SchemaAddedOrRemovedRule(),
    PropertyAddedOrRemovedRule(),
    TypeChangedRule(),
    UniqueConstraintRule(),
    KeyConstraintRule(),
    ValidationConstraintRule(),
    EnumConstraintRule(),
    VectorShapeRule(),
    MetadataFallbackRule(),
)
