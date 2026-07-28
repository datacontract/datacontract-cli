"""The docs list every importer and exporter three times; all three stay alphabetical.

The order has drifted twice: once by appending new pages at the end, and once by
sorting on the file name when the sidebar renders the page title, which put
``Import: AWS Glue`` under G and ``Import: Amazon Redshift`` under R. Each list
is checked against the text it actually displays.
"""

import re

import pytest

from tests.docs_paths import DOCS

FOLDERS = [("imports", "Import: ", "import"), ("exports", "Export: ", "export")]
IDS = [folder for folder, _, _ in FOLDERS]

# The reference and connection guides are listed the same way, minus a command
# page to cross-check against.
SIDEBAR_FOLDERS = FOLDERS + [("reference", "", None), ("testing", "", None)]
SIDEBAR_IDS = [folder for folder, _, _ in SIDEBAR_FOLDERS]


def pages(folder: str):
    """Every listed page of the folder, index and unlisted stubs excluded."""
    listed = [
        page
        for page in (DOCS / folder).glob("*.md")
        if page.stem != "index" and "unlisted: true" not in page.read_text()
    ]
    # by stem, not by file name: "avro-idl.md" sorts before "avro.md" ("-" < ".")
    return sorted(listed, key=lambda page: page.stem)


def sidebar_label(page, prefix: str) -> str:
    """The text Docusaurus renders in the sidebar for this page."""
    text = page.read_text()
    label = re.search(r'^sidebar_label: "(.*)"$', text, re.M)
    rendered = label.group(1) if label else re.search(r'^title: "(.*)"$', text, re.M).group(1)
    return rendered.removeprefix(prefix)


def sidebar_position(page) -> int:
    return int(re.search(r"^sidebar_position: (\d+)$", page.read_text(), re.M).group(1))


@pytest.mark.parametrize("folder, prefix, _command", SIDEBAR_FOLDERS, ids=SIDEBAR_IDS)
def test_sidebar_is_ordered_by_the_label_it_renders(folder, prefix, _command):
    ordered = [sidebar_label(page, prefix) for page in sorted(pages(folder), key=sidebar_position)]

    assert ordered == sorted(ordered, key=str.lower)


@pytest.mark.parametrize("folder, prefix, _command", SIDEBAR_FOLDERS, ids=SIDEBAR_IDS)
def test_sidebar_positions_are_a_gapless_sequence(folder, prefix, _command):
    """A duplicate or a gap makes the rendered order depend on the file name again."""
    positions = sorted(sidebar_position(page) for page in pages(folder))

    assert positions == list(range(1, len(positions) + 1))


@pytest.mark.parametrize("folder, prefix, _command", FOLDERS, ids=IDS)
def test_card_grid_lists_every_page_in_order(folder, prefix, _command):
    index = (DOCS / folder / "index.md").read_text()
    grid = re.search(r'<div className="card-grid">(.*?)</div>', index, re.S).group(1)
    # the cards show the format name, so that is what has to be in order here
    titles = re.findall(r'doc-card-title">([^<]+)<', grid)

    assert titles == sorted(titles)
    assert titles == [page.stem for page in pages(folder)]


def test_the_reference_card_grid_matches_its_sidebar():
    """Its cards show the page label rather than a format name."""
    index = (DOCS / "reference" / "index.md").read_text()
    grid = re.search(r'<div className="card-grid">(.*?)</div>', index, re.S).group(1)
    titles = re.findall(r'doc-card-title">([^<]+)<', grid)

    assert titles == sorted(titles, key=str.lower)
    assert titles == [sidebar_label(page, "") for page in sorted(pages("reference"), key=sidebar_position)]


@pytest.mark.parametrize("folder, prefix, command", FOLDERS, ids=IDS)
def test_command_page_lists_every_format_in_order(folder, prefix, command):
    page = (DOCS / "commands" / f"{command}.md").read_text()
    listed = re.findall(r"`([^`]+)`", re.search(r"Available formats: (.+?)\.\n", page).group(1))

    assert listed == sorted(listed)
    assert listed == [page.stem for page in pages(folder)]
