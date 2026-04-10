import io
import sys
from pathlib import Path

from rich.console import Console

from datacontract.data_contract import DataContract
from datacontract.model.changelog import ChangelogEntry, ChangelogResult, ChangelogType
from datacontract.output.text_changelog_results import _badges, _with_markup, _wrap, write_text_changelog_results

V1 = "fixtures/changelog/integration/changelog_integration_v1.yaml"
V2 = "fixtures/changelog/integration/changelog_integration_v2.yaml"

GOLDEN_TEXT = Path(__file__).parent / "fixtures/changelog/golden_changelog_text.txt"


def _make_entries(added=0, removed=0, changed=0):
    entries = []
    for _ in range(added):
        entries.append(ChangelogEntry(path="a.b", type=ChangelogType.added))
    for _ in range(removed):
        entries.append(ChangelogEntry(path="a.b", type=ChangelogType.removed))
    for _ in range(changed):
        entries.append(ChangelogEntry(path="a.b", type=ChangelogType.updated))
    return entries


def _render(result: ChangelogResult) -> str:
    buf = io.StringIO()
    con = Console(file=buf, width=300, highlight=False)
    old_stdout = sys.stdout
    sys.stdout = buf
    try:
        write_text_changelog_results(result, con)
    finally:
        sys.stdout = old_stdout
    return buf.getvalue()


class TestBadges:
    def test_all_types(self):
        result = _badges(_make_entries(added=2, removed=1, changed=3))
        assert "1 Removed" in result
        assert "3 Updated" in result
        assert "2 Added" in result

    def test_ordering_added_updated_removed(self):
        result = _badges(_make_entries(added=1, removed=1, changed=1))
        assert result.index("Added") < result.index("Updated") < result.index("Removed")

    def test_added_badge_green(self):
        result = _badges(_make_entries(added=1))
        assert "[ [green]1 Added[/green] ]" == result

    def test_updated_badge_yellow(self):
        result = _badges(_make_entries(changed=1))
        assert "[ [yellow]1 Updated[/yellow] ]" == result

    def test_removed_badge_red(self):
        result = _badges(_make_entries(removed=1))
        assert "[ [red]1 Removed[/red] ]" == result

    def test_zero_count_omitted(self):
        result = _badges(_make_entries(added=3))
        assert "Removed" not in result
        assert "Updated" not in result
        assert "3 Added" in result

    def test_empty_list_returns_empty_string(self):
        assert _badges([]) == ""

    def test_separator_between_badges(self):
        result = _badges(_make_entries(removed=1, added=1))
        assert "  " in result


class TestWrap:
    def test_short_text_returned_as_is(self):
        assert _wrap("hello", 20) == "hello"

    def test_exact_max_width_not_wrapped(self):
        text = "a" * 20
        assert _wrap(text, 20) == text

    def test_single_word_longer_than_max_returned_as_is(self):
        long_word = "a" * 35
        assert _wrap(long_word, 30) == long_word

    def test_multi_word_each_line_within_max_width(self):
        result = _wrap("hello world foo bar", 11)
        for line in result.split("\n"):
            assert len(line) <= 11

    def test_multi_word_produces_multiple_lines(self):
        assert "\n" in _wrap("one two three four five six", 9)

    def test_empty_string_returned_as_is(self):
        assert _wrap("", 10) == ""


class TestWithMarkup:
    def test_added_green(self):
        assert _with_markup(ChangelogType.added) == "[green]Added[/green]"

    def test_removed_red(self):
        assert _with_markup(ChangelogType.removed) == "[red]Removed[/red]"

    def test_updated_yellow(self):
        assert _with_markup(ChangelogType.updated) == "[yellow]Updated[/yellow]"


class TestTerminalStateInheritance:
    """The wide rendering console inherits terminal/color state from the caller's console.
    This prevents colors being silently stripped when the outer console is a real TTY."""

    def test_colors_present_when_terminal(self):
        result = DataContract(data_contract_file=V1).changelog(DataContract(data_contract_file=V2))
        buf = io.StringIO()
        con = Console(file=buf, width=300, force_terminal=True)
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            write_text_changelog_results(result, con)
        finally:
            sys.stdout = old_stdout
        assert "\033[" in buf.getvalue()

    def test_colors_absent_when_not_terminal(self):
        result = DataContract(data_contract_file=V1).changelog(DataContract(data_contract_file=V2))
        buf = io.StringIO()
        con = Console(file=buf, width=300, no_color=True)
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            write_text_changelog_results(result, con)
        finally:
            sys.stdout = old_stdout
        assert "\033[" not in buf.getvalue()


class TestWriteTextChangelogResults:
    def test_summary_header_present(self):
        result = DataContract(data_contract_file=V1).changelog(DataContract(data_contract_file=V2))
        assert "Summary" in _render(result)

    def test_details_header_present(self):
        result = DataContract(data_contract_file=V1).changelog(DataContract(data_contract_file=V2))
        assert "Details" in _render(result)

    def test_badges_present(self):
        result = DataContract(data_contract_file=V1).changelog(DataContract(data_contract_file=V2))
        output = _render(result)
        assert "Removed" in output or "Updated" in output or "Added" in output

    def test_all_change_types_present(self):
        result = DataContract(data_contract_file=V1).changelog(DataContract(data_contract_file=V2))
        output = _render(result)
        assert "Added" in output
        assert "Removed" in output
        assert "Updated" in output

    def test_no_changes_suppresses_summary(self):
        result = DataContract(data_contract_file=V1).changelog(DataContract(data_contract_file=V1))
        assert "Summary" not in _render(result)

    def test_no_changes_still_renders_details(self):
        result = DataContract(data_contract_file=V1).changelog(DataContract(data_contract_file=V1))
        assert "Details" in _render(result)

    def test_golden_output(self):
        result = DataContract(data_contract_file=V1).changelog(DataContract(data_contract_file=V2))
        buf = io.StringIO()
        con = Console(file=buf, width=300, highlight=False, no_color=True)
        old_stdout = sys.stdout
        sys.stdout = buf
        try:
            write_text_changelog_results(result, con)
        finally:
            sys.stdout = old_stdout
        assert buf.getvalue() == GOLDEN_TEXT.read_text(encoding="utf-8"), (
            "Changelog text output has changed. If intentional, regenerate "
            "golden_changelog_text.txt (see tests/fixtures/changelog/helper/generate_golden.py)."
        )
