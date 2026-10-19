from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

from datacontract.engines.checks.create_checks import freshness_value_to_seconds
from datacontract.engines.checks.severity import failure_result
from datacontract.model.breaking import Direction
from datacontract.model.changelog import ChangelogEntry, ChangelogType
from datacontract.model.run import ResultEnum


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

    def evaluate(self, entry: ChangelogEntry, before: dict, after: dict) -> RuleEvaluation | None:
        if not entry.path.startswith("schema.") or not entry.path.endswith(self._suffixes):
            return None
        if entry.type == ChangelogType.added:
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
    _thresholds = (
        ".mustBeLessThan",
        ".mustBeLessOrEqualTo",
        ".mustBeGreaterThan",
        ".mustBeGreaterOrEqualTo",
    )

    def evaluate(self, entry: ChangelogEntry, before: dict, after: dict) -> RuleEvaluation | None:
        if not entry.path.startswith("schema.") or ".quality." not in entry.path:
            return None
        quality_path, rule_path = entry.path.rsplit(".quality.", 1)
        name, _, field = rule_path.partition(".")
        rule_versions = [
            rule
            for rule in (_lookup(tree, f"{quality_path}.quality.{name}") for tree in (before, after))
            if isinstance(rule, dict)
        ]
        if (
            field
            and rule_versions
            and all(failure_result(rule.get("severity")) != ResultEnum.failed for rule in rule_versions)
        ):
            # A rule that can only warn guarantees nothing.
            direction = Direction.UNTESTED
        elif rule_path.endswith(".arguments.validValues"):
            # The diff emits one entry per list element.
            direction = {
                ChangelogType.added: Direction.LOOSENS,
                ChangelogType.removed: Direction.TIGHTENS,
            }.get(entry.type, Direction.BOTH)
        elif rule_path.endswith(".arguments.invalidValues"):
            direction = {
                ChangelogType.added: Direction.TIGHTENS,
                ChangelogType.removed: Direction.LOOSENS,
            }.get(entry.type, Direction.BOTH)
        elif rule_path.endswith(self._thresholds + (".mustBe", ".mustNotBe", ".mustBeBetween", ".mustNotBeBetween")):
            rule_path_in_contract, threshold = entry.path.rsplit(".", 1)
            old_rule = _lookup(before, rule_path_in_contract) or {}
            new_rule = _lookup(after, rule_path_in_contract) or {}
            if entry.type == ChangelogType.added and threshold not in old_rule:
                # Replacing one kind of threshold with another cannot be ordered.
                direction = (
                    Direction.UNDETERMINED if any(k.startswith("must") for k in old_rule) else Direction.TIGHTENS
                )
            elif entry.type == ChangelogType.removed and threshold not in new_rule:
                direction = Direction.UNDETERMINED if any(k.startswith("must") for k in new_rule) else Direction.LOOSENS
            elif rule_path.endswith(self._thresholds):
                direction = _ordered_direction(
                    entry.path, _parse_number(entry.old_value), _parse_number(entry.new_value)
                )
            elif rule_path.endswith((".mustBe", ".mustNotBe")):
                direction = Direction.UNDETERMINED
            else:
                # The diff reports the bounds as unordered list elements, so compare the whole ranges.
                old_range, new_range = (
                    sorted(bounds) if None not in bounds else None
                    for bounds in (
                        [_parse_number(str(v)) for v in value]
                        if isinstance(value, list) and len(value) == 2
                        else [None]
                        for value in (old_rule.get(threshold), new_rule.get(threshold))
                    )
                )
                if old_range is None or new_range is None:
                    direction = Direction.UNDETERMINED
                elif old_range == new_range:
                    direction = Direction.UNTESTED
                else:
                    narrower = new_range[0] >= old_range[0] and new_range[1] <= old_range[1]
                    wider = new_range[0] <= old_range[0] and new_range[1] >= old_range[1]
                    # mustBeBetween names the allowed range, mustNotBeBetween the forbidden one.
                    if threshold == "mustNotBeBetween":
                        narrower, wider = wider, narrower
                    if narrower:
                        direction = Direction.TIGHTENS
                    elif wider:
                        direction = Direction.LOOSENS
                    else:
                        direction = Direction.BOTH
        elif rule_path.endswith(".severity"):
            was_blocking = failure_result(entry.old_value) == ResultEnum.failed
            is_blocking = failure_result(entry.new_value) == ResultEnum.failed
            if was_blocking == is_blocking:
                direction = Direction.UNTESTED
            else:
                direction = Direction.TIGHTENS if is_blocking else Direction.LOOSENS
        elif not field:
            rule = _lookup(after if entry.type == ChangelogType.added else before, entry.path)
            if failure_result(rule.get("severity") if isinstance(rule, dict) else None) != ResultEnum.failed:
                direction = Direction.UNTESTED
            else:
                direction = Direction.TIGHTENS if entry.type == ChangelogType.added else Direction.LOOSENS
        elif rule_path.endswith((".description", ".dimension", ".businessImpact")):
            direction = Direction.UNTESTED
        elif ".customProperties." in rule_path or ".authoritativeDefinitions." in rule_path or ".tags" in rule_path:
            direction = Direction.UNTESTED
        else:
            # What the rule checks changed (type, metric, query, other arguments, thresholds we cannot order).
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
    if path.endswith(
        (".minLength", ".minimum", ".exclusiveMinimum", ".minItems", ".mustBeGreaterThan", ".mustBeGreaterOrEqualTo")
    ):
        return Direction.TIGHTENS if new > old else Direction.LOOSENS
    return Direction.TIGHTENS if new < old else Direction.LOOSENS


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
        try:
            return float(date.fromisoformat(normalized).toordinal())
        except ValueError:
            return None


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
