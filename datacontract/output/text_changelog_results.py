import io

from rich import box
from rich.console import Console
from rich.table import Table

from datacontract.model.changelog import ChangelogResult, ChangelogType

_VAL_W = 30


def write_text_changelog_results(result: ChangelogResult, console: Console):
    _print_summary(result, console)
    _print_table(result, console)


def _badges(entries: list) -> str:
    removed = sum(1 for e in entries if e.type == ChangelogType.removed)
    changed = sum(1 for e in entries if e.type == ChangelogType.changed)
    added = sum(1 for e in entries if e.type == ChangelogType.added)
    parts = []
    if removed:
        parts.append(f"[ {removed} Removed ]")
    if changed:
        parts.append(f"[ {changed} Changed ]")
    if added:
        parts.append(f"[ {added} Added ]")
    return "  ".join(parts)


def _print_summary(result: ChangelogResult, console: Console):
    if not result.summary:
        return
    console.print("Summary")
    console.print(_badges(result.summary))
    table = Table(box=box.ROUNDED, show_header=True)
    table.add_column("Change", no_wrap=True)
    table.add_column("Field", no_wrap=True)
    for entry in result.summary:
        table.add_row(_with_markup(entry.type), entry.path)
    buf = io.StringIO()
    wide = Console(file=buf, width=300, highlight=False, force_terminal=console.is_terminal, no_color=console.no_color)
    wide.print(table)
    print(buf.getvalue(), end="")
    print("")


def _print_table(result: ChangelogResult, console: Console):
    console.print("Details")
    table = Table(box=box.ROUNDED)
    table.add_column("Change", no_wrap=True)
    table.add_column("Path", no_wrap=True)
    table.add_column("Old Value", max_width=_VAL_W, no_wrap=True)
    table.add_column("New Value", max_width=_VAL_W, no_wrap=True)
    for entry in result.entries:
        table.add_row(
            _with_markup(entry.type),
            entry.path,
            _wrap(entry.old_value or "", _VAL_W),
            _wrap(entry.new_value or "", _VAL_W),
        )
    buf = io.StringIO()
    wide = Console(file=buf, width=300, highlight=False, force_terminal=console.is_terminal, no_color=console.no_color)
    wide.print(table)
    print(buf.getvalue(), end="")


def _with_markup(changelog_type: ChangelogType) -> str:
    if changelog_type == ChangelogType.added:
        return "[green]added[/green]"
    if changelog_type == ChangelogType.removed:
        return "[red]removed[/red]"
    if changelog_type == ChangelogType.changed:
        return "[yellow]changed[/yellow]"
    return changelog_type.value


def _wrap(text: str, max_width: int) -> str:
    if len(text) <= max_width:
        return text
    lines, current = [], ""
    for word in text.split():
        if current and len(current) + 1 + len(word) > max_width:
            lines.append(current)
            current = word
        else:
            current = (current + " " + word).lstrip()
    if current:
        lines.append(current)
    return "\n".join(lines)
