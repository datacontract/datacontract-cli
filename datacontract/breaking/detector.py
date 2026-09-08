from collections import defaultdict
from collections.abc import Iterable

from datacontract.breaking.rules import DEFAULT_RULES, BreakingChangeRule
from datacontract.model.breaking import BreakingChangeEntry, BreakingChangeLevel, BreakingChangeResult
from datacontract.model.changelog import ChangelogEntry, ChangelogResult, ChangelogType

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
        # Nothing inside a newly added element can break a consumer: it did not exist before.
        added = {entry.path for entry in entries if entry.change_type == ChangelogType.added}
        for entry in entries:
            segments = entry.path.split(".")
            if any(".".join(segments[:i]) in added for i in range(1, len(segments))):
                entry.level = BreakingChangeLevel.INFO
        entries_by_prefix = defaultdict(list)
        for entry in entries:
            prefix = ""
            for segment in entry.path.split("."):
                prefix = f"{prefix}.{segment}" if prefix else segment
                entries_by_prefix[prefix].append(entry)
        summary = [self._summarize(entry, entries_by_prefix.get(entry.path, [])) for entry in changelog.summary]
        return BreakingChangeResult(v1=changelog.v1, v2=changelog.v2, summary=summary, entries=entries)

    def _classify(self, entry: ChangelogEntry) -> BreakingChangeEntry:
        for rule in self._rules:
            evaluation = rule.evaluate(entry)
            if evaluation is not None:
                return BreakingChangeEntry(
                    path=entry.path,
                    change_type=entry.type,
                    level=evaluation.level,
                    message=evaluation.message,
                    rule_id=evaluation.rule_id,
                    old_value=entry.old_value,
                    new_value=entry.new_value,
                )
        raise ValueError(f"No breaking-change rule classified {entry.path}")

    @staticmethod
    def _summarize(summary_entry: ChangelogEntry, entries: list[BreakingChangeEntry]) -> BreakingChangeEntry:
        if not entries:
            return BreakingChangeEntry(
                path=summary_entry.path,
                change_type=summary_entry.type,
                level=BreakingChangeLevel.INFO,
                message=f"Changed contract at {summary_entry.path}",
                rule_id="summary-fallback",
            )
        highest = max(entries, key=lambda entry: _LEVEL_ORDER[entry.level])
        return BreakingChangeEntry(
            path=summary_entry.path,
            change_type=summary_entry.type,
            level=highest.level,
            message=f"{highest.level.value.capitalize()} impact at {summary_entry.path}",
            rule_id=f"summary:{highest.rule_id}",
            old_value=highest.old_value,
            new_value=highest.new_value,
        )
