from collections.abc import Iterable

from datacontract.breaking.rules import DEFAULT_RULES, BreakingChangeRule
from datacontract.model.breaking import BreakingChangeEntry, BreakingChangeLevel, BreakingChangeResult
from datacontract.model.changelog import ChangelogEntry, ChangelogResult

_LEVEL_ORDER = {
    BreakingChangeLevel.INFO: 0,
    BreakingChangeLevel.WARNING: 1,
    BreakingChangeLevel.ERROR: 2,
}


class BreakingChangeDetector:
    """Classify detailed changelog entries using an ordered rule set."""

    def __init__(self, rules: Iterable[BreakingChangeRule] = DEFAULT_RULES):
        self._rules = tuple(rules)
        if not self._rules:
            raise ValueError("At least one breaking-change rule is required")

    def detect(self, changelog: ChangelogResult) -> BreakingChangeResult:
        entries = [self._classify(entry) for entry in changelog.entries]
        summary = [self._summarize(entry, entries) for entry in changelog.summary]
        return BreakingChangeResult(v1=changelog.v1, v2=changelog.v2, summary=summary, entries=entries)

    def _classify(self, entry: ChangelogEntry) -> BreakingChangeEntry:
        matches = [match for rule in self._rules if (match := rule.evaluate(entry)) is not None]
        if not matches:
            raise ValueError(f"No breaking-change rule classified {entry.path}")
        highest_priority = max(self._priority(match.rule_id) for match in matches)
        highest = [match for match in matches if self._priority(match.rule_id) == highest_priority]
        if len({match.rule_id for match in highest}) > 1:
            raise ValueError(f"Ambiguous breaking-change rules for {entry.path}: {highest}")
        evaluation = highest[0]
        return BreakingChangeEntry(
            path=entry.path,
            change_type=entry.type,
            level=evaluation.level,
            message=evaluation.message,
            rule_id=evaluation.rule_id,
            old_value=entry.old_value,
            new_value=entry.new_value,
        )

    def _priority(self, rule_id: str) -> int:
        for rule in self._rules:
            if rule.rule_id == rule_id:
                return rule.priority
        raise ValueError(f"Unknown rule {rule_id}")

    @staticmethod
    def _summarize(summary_entry: ChangelogEntry, entries: list[BreakingChangeEntry]) -> BreakingChangeEntry:
        matching = [
            entry
            for entry in entries
            if entry.path == summary_entry.path or entry.path.startswith(f"{summary_entry.path}.")
        ]
        if not matching:
            return BreakingChangeEntry(
                path=summary_entry.path,
                change_type=summary_entry.type,
                level=BreakingChangeLevel.INFO,
                message=f"Changed contract at {summary_entry.path}",
                rule_id="summary-fallback",
            )
        highest = max(matching, key=lambda entry: _LEVEL_ORDER[entry.level])
        return BreakingChangeEntry(
            path=summary_entry.path,
            change_type=summary_entry.type,
            level=highest.level,
            message=f"{highest.level.value.capitalize()} impact at {summary_entry.path}",
            rule_id=f"summary:{highest.rule_id}",
            old_value=highest.old_value,
            new_value=highest.new_value,
        )
