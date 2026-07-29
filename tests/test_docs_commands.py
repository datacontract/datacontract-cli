"""The command reference is generated from `--help` and must not drift.

Every page under docs/docs/commands/ is produced by update_command_docs.py from
the Click command tree, so adding a command or an option without regenerating
is a test failure rather than a silently stale page.
"""

import subprocess
import sys
from pathlib import Path

import pytest
import typer.main

from datacontract.cli import app
from tests.docs_paths import DOCS
from update_command_docs import is_group

REPO_ROOT = Path(__file__).resolve().parents[1]
COMMANDS = DOCS / "commands"


def leaves():
    """(page path, command) for every command that should have a reference page."""
    root = typer.main.get_command(app)
    for name, cmd in root.commands.items():
        if is_group(cmd):
            yield COMMANDS / name / "index.md", cmd
            for sub_name, sub in cmd.commands.items():
                yield COMMANDS / name / f"{sub_name}.md", sub
        else:
            yield COMMANDS / f"{name}.md", cmd


IDS = [str(page.relative_to(COMMANDS)) for page, _ in leaves()]


@pytest.mark.parametrize("page,cmd", list(leaves()), ids=IDS)
def test_every_command_has_a_reference_page(page, cmd):
    assert page.exists(), f"missing command reference page: {page.relative_to(REPO_ROOT)}"


@pytest.mark.parametrize("page,cmd", list(leaves()), ids=IDS)
def test_every_option_is_documented(page, cmd):
    """A new option that never reaches the docs is the drift this catches."""
    text = page.read_text()
    for param in cmd.params:
        for opt in list(param.opts) + list(getattr(param, "secondary_opts", [])):
            if opt.startswith("--") and opt != "--help":
                assert opt in text, f"{opt} is missing from {page.relative_to(REPO_ROOT)}"


def test_command_docs_are_regenerated():
    """`python update_command_docs.py --check` must be clean."""
    result = subprocess.run(
        [sys.executable, "update_command_docs.py", "--check"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, result.stdout + result.stderr
