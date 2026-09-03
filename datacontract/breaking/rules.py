from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import date

from datacontract.model.breaking import BreakingChangeLevel
from datacontract.model.changelog import ChangelogEntry, ChangelogType


@dataclass(frozen=True)
class RuleEvaluation:
    rule_id: str
    level: BreakingChangeLevel
    message: str


class BreakingChangeRule(ABC):
    rule_id: str

    @abstractmethod
    def evaluate(self, entry: ChangelogEntry) -> RuleEvaluation | None:
        """Return a classification when this rule applies to ``entry``."""


class SchemaRemovedRule(BreakingChangeRule):
    rule_id = "schema-removed"

    def evaluate(self, entry: ChangelogEntry) -> RuleEvaluation | None:
        segments = entry.path.split(".")
        if entry.type == ChangelogType.removed and len(segments) == 2 and segments[0] == "schema":
            return RuleEvaluation(self.rule_id, BreakingChangeLevel.ERROR, f"Removed schema {segments[1]}")
        return None


class FieldRemovedRule(BreakingChangeRule):
    rule_id = "field-removed"

    def evaluate(self, entry: ChangelogEntry) -> RuleEvaluation | None:
        segments = entry.path.split(".")
        if entry.type != ChangelogType.removed or not _is_schema_property_path(segments):
            return None
        property_name = segments[-1]
        return RuleEvaluation(self.rule_id, BreakingChangeLevel.ERROR, f"Removed property {property_name}")


class RequiredChangedRule(BreakingChangeRule):
    rule_id = "required-changed"

    def evaluate(self, entry: ChangelogEntry) -> RuleEvaluation | None:
        if not entry.path.endswith(".required"):
            return None
        old = _parse_bool(entry.old_value)
        new = _parse_bool(entry.new_value)
        if entry.type == ChangelogType.added and new is True:
            level = BreakingChangeLevel.ERROR
        elif entry.type == ChangelogType.removed or new is False:
            # Dropping the requirement, or writing out the optional default, only loosens the contract.
            level = BreakingChangeLevel.INFO
        elif entry.type == ChangelogType.updated and old is False and new is True:
            level = BreakingChangeLevel.ERROR
        elif entry.type in (ChangelogType.added, ChangelogType.updated):
            level = BreakingChangeLevel.WARNING
        else:
            return None
        return RuleEvaluation(self.rule_id, level, _change_message("requiredness", entry))


class TypeChangedRule(BreakingChangeRule):
    rule_id = "type-changed"

    def evaluate(self, entry: ChangelogEntry) -> RuleEvaluation | None:
        if not entry.path.endswith((".logicalType", ".physicalType")):
            return None
        if entry.type == ChangelogType.updated:
            level = BreakingChangeLevel.ERROR
        elif entry.type == ChangelogType.added:
            level = BreakingChangeLevel.INFO
        elif entry.type == ChangelogType.removed:
            level = BreakingChangeLevel.WARNING
        else:
            return None
        return RuleEvaluation(self.rule_id, level, _change_message("type", entry))


class UniqueConstraintRule(BreakingChangeRule):
    rule_id = "unique-constraint-changed"

    def evaluate(self, entry: ChangelogEntry) -> RuleEvaluation | None:
        if not entry.path.endswith(".unique"):
            return None
        old = _parse_bool(entry.old_value)
        new = _parse_bool(entry.new_value)
        if new is True and old is not True:
            level = BreakingChangeLevel.ERROR
        elif old is True and new is not True:
            level = BreakingChangeLevel.INFO
        else:
            level = BreakingChangeLevel.WARNING
        return RuleEvaluation(self.rule_id, level, _change_message("uniqueness", entry))


class KeyConstraintRule(BreakingChangeRule):
    rule_id = "key-constraint-changed"

    def evaluate(self, entry: ChangelogEntry) -> RuleEvaluation | None:
        if not entry.path.endswith((".primaryKey", ".primary_key")):
            return None
        return RuleEvaluation(self.rule_id, BreakingChangeLevel.WARNING, _change_message("key constraint", entry))


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
    )

    def evaluate(self, entry: ChangelogEntry) -> RuleEvaluation | None:
        if not entry.path.endswith(self._suffixes):
            return None
        old = _parse_number(entry.old_value)
        new = _parse_number(entry.new_value)
        if old is None or new is None:
            level = BreakingChangeLevel.WARNING
        elif _is_tightening(entry.path, old, new):
            level = BreakingChangeLevel.ERROR
        else:
            level = BreakingChangeLevel.INFO
        return RuleEvaluation(self.rule_id, level, _change_message("validation constraint", entry))


class MetadataFallbackRule(BreakingChangeRule):
    rule_id = "metadata-or-unknown-change"

    def evaluate(self, entry: ChangelogEntry) -> RuleEvaluation:
        return RuleEvaluation(self.rule_id, BreakingChangeLevel.INFO, _change_message("contract", entry))


def _is_schema_property_path(segments: list[str]) -> bool:
    return len(segments) >= 3 and segments[0] == "schema" and segments[-2] == "properties"


def _parse_bool(value: str | None) -> bool | None:
    if value is None:
        return None
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


def _is_tightening(path: str, old: float, new: float) -> bool:
    if path.endswith((".minLength", ".minimum", ".exclusiveMinimum")):
        return new > old
    if path.endswith((".maxLength", ".maximum", ".exclusiveMaximum")):
        return new < old
    return True


def _change_message(subject: str, entry: ChangelogEntry) -> str:
    if entry.type == ChangelogType.added:
        return f"Added {subject} at {entry.path}"
    if entry.type == ChangelogType.removed:
        return f"Removed {subject} at {entry.path}"
    return f"Changed {subject} at {entry.path} from {entry.old_value!r} to {entry.new_value!r}"


DEFAULT_RULES: tuple[BreakingChangeRule, ...] = (
    RequiredChangedRule(),
    SchemaRemovedRule(),
    FieldRemovedRule(),
    TypeChangedRule(),
    UniqueConstraintRule(),
    KeyConstraintRule(),
    ValidationConstraintRule(),
    MetadataFallbackRule(),
)
