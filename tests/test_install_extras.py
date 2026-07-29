"""The install hints the CLI prints must name extras that actually exist.

`datacontract test` tells the user which extra to install when a backend is
missing. Most server types share their name with the extra, but not all, and a
hint naming a non-existent extra leaves the user with a `pip install` that
silently changes nothing.
"""

import re
from importlib.metadata import metadata
from pathlib import Path

import pytest

from datacontract.engines.ibis.connections.connect import _FILE_SERVER_TYPES
from datacontract.engines.ibis.ibis_check_execute import install_extra_for


def declared_extras() -> set[str]:
    """Read the extras from the installed distribution, which is what pip resolves."""
    return set(metadata("datacontract-cli").get_all("Provides-Extra") or [])


# Every server type `datacontract test` can dispatch on, so a new backend that
# forgets its extra is caught here rather than by the first user to hit it.
SERVER_TYPES = sorted(
    _FILE_SERVER_TYPES
    | {
        "api",
        "athena",
        "bigquery",
        "databricks",
        "dataframe",
        "impala",
        "kafka",
        "mysql",
        "oracle",
        "postgres",
        "redshift",
        "snowflake",
        "sqlserver",
        "trino",
    }
)


@pytest.mark.parametrize("server_type", SERVER_TYPES)
def test_every_server_type_points_at_a_declared_extra(server_type):
    assert install_extra_for(server_type) in declared_extras()


@pytest.mark.parametrize(
    "server_type, expected",
    [
        ("local", "duckdb"),  # there is no `local` extra
        ("api", "duckdb"),  # `api` installs the web server, not a test backend
        ("postgres", "postgres"),
    ],
)
def test_server_types_without_a_matching_extra_are_redirected(server_type, expected):
    assert install_extra_for(server_type) == expected


def test_every_extra_a_data_source_guide_installs_exists():
    """A guide that names a typo'd extra installs nothing and fails at test time."""
    extras = declared_extras()
    guides = (Path(__file__).parent.parent / "docs" / "docs" / "testing").glob("*.md")

    for guide in guides:
        for match in re.finditer(r"datacontract-cli\[([a-z0-9,_-]+)\]", guide.read_text()):
            for extra in match.group(1).split(","):
                assert extra in extras, f"{guide.name} installs unknown extra '{extra}'"
