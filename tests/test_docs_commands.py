"""The command reference is generated from `--help` and has to stay reachable.

Every page under docs/docs/commands/ is produced by update_command_docs.py from
the Click command tree, the same way the docs build produces it, so what is
asserted here is that the generator covers every command and option and that
the prose guides and the generated pages still link to each other.
"""

from pathlib import Path

import pytest
import typer.main

from datacontract.cli import app
from tests.docs_paths import DOCS
from update_command_docs import is_group

REPO_ROOT = Path(__file__).resolve().parents[1]
COMMANDS = DOCS / "commands"

pytestmark = pytest.mark.usefixtures("generated_docs")


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


def test_the_global_options_are_documented():
    """`--version` and `--system-truststore` appear on no other page.

    The root options used to be left out entirely: the generator wrote a page
    per subcommand but skipped the root `--help`, and `commands/index.md` was
    hand-written.
    """
    text = (COMMANDS / "index.md").read_text()
    for param in typer.main.get_command(app).params:
        for opt in param.opts:
            if opt.startswith("--") and opt != "--help":
                assert opt in text, f"{opt} is missing from commands/index.md"


GUIDES = [
    (guide, COMMANDS / command / f"{guide.stem}.md")
    for folder, command in (("imports", "import"), ("exports", "export"))
    for guide in sorted((DOCS / folder).glob("*.md"))
    if guide.stem != "index" and "unlisted: true" not in guide.read_text()
]
GUIDE_IDS = [str(guide.relative_to(DOCS)) for guide, _ in GUIDES]


@pytest.mark.parametrize("guide,page", GUIDES, ids=GUIDE_IDS)
def test_each_guide_links_to_its_command_page(guide, page):
    """The generated reference pages arrived with no way in from the prose.

    A reader on `Import: Postgres` could not reach the option table without
    going back through the sidebar, and the two pages competed in search.
    """
    assert page.exists(), f"no command page for {guide.relative_to(REPO_ROOT)}"
    link = f"({page.relative_to(DOCS).as_posix()}"
    assert link.replace("commands/", "../commands/") in guide.read_text(), (
        f"{guide.relative_to(REPO_ROOT)} does not link to {page.relative_to(REPO_ROOT)}"
    )


@pytest.mark.parametrize("guide,page", GUIDES, ids=GUIDE_IDS)
def test_each_command_page_links_back_to_its_guide(guide, page):
    assert f"../../{guide.relative_to(DOCS).as_posix()}" in page.read_text(), (
        f"{page.relative_to(REPO_ROOT)} does not link back to {guide.relative_to(REPO_ROOT)}"
    )
