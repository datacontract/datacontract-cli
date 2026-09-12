import io
from collections import Counter

from rich import box
from rich.console import Console
from rich.table import Table

from datacontract.model.breaking import BreakingChangeEntry, BreakingChangeLevel, BreakingChangeResult
from datacontract.output.text_changelog_results import _wrap

_VAL_W = 30
_LEVEL_ORDER = [BreakingChangeLevel.ERROR, BreakingChangeLevel.WARNING, BreakingChangeLevel.INFO]
_LEVEL_COLOR = {
    BreakingChangeLevel.ERROR: "red",
    BreakingChangeLevel.WARNING: "yellow",
    BreakingChangeLevel.INFO: "green",
}


def write_text_breaking_results(result: BreakingChangeResult, console: Console):
    _print_summary(result, console)
    _print_table(result, console)


def _badges(entries: list[BreakingChangeEntry]) -> str:
    counts = Counter(entry.level for entry in entries)
    parts = []
    for level in _LEVEL_ORDER:
        count = counts[level]
        if count:
            color = _LEVEL_COLOR[level]
            parts.append(f"[ [{color}]{count} {level.value.capitalize()}[/{color}] ]")
    return "  ".join(parts)


def _print_summary(result: BreakingChangeResult, console: Console):
    if not result.summary:
        return
    console.print("Summary")
    console.print(_badges(result.summary))
    table = Table(box=box.ROUNDED, show_header=True)
    table.add_column("Severity", no_wrap=True)
    table.add_column("Change", no_wrap=True)
    table.add_column("Field", no_wrap=True)
    for entry in result.summary:
        table.add_row(_severity_markup(entry.level), entry.change_type.value.capitalize(), entry.path)
    _print_wide(table, console)


def _print_table(result: BreakingChangeResult, console: Console):
    console.print("Details")
    table = Table(box=box.ROUNDED)
    table.add_column("Severity", no_wrap=True)
    table.add_column("Change", no_wrap=True)
    table.add_column("Path", no_wrap=True)
    table.add_column("Old Value", max_width=_VAL_W, no_wrap=True)
    table.add_column("New Value", max_width=_VAL_W, no_wrap=True)
    table.add_column("Message", max_width=_VAL_W, no_wrap=True)
    for entry in result.entries:
        table.add_row(
            _severity_markup(entry.level),
            entry.change_type.value.capitalize(),
            entry.path,
            _wrap(entry.old_value or "", _VAL_W),
            _wrap(entry.new_value or "", _VAL_W),
            _wrap(entry.message, _VAL_W),
        )
    _print_wide(table, console)


def _severity_markup(level: BreakingChangeLevel) -> str:
    color = _LEVEL_COLOR[level]
    return f"[{color}]{level.value.upper()}[/{color}]"


def _print_wide(table: Table, console: Console):
    buf = io.StringIO()
    wide = Console(file=buf, width=300, highlight=False, force_terminal=console.is_terminal, no_color=console.no_color)
    wide.print(table)
    print(buf.getvalue(), end="")
    print("")
