"""Load the metadata of the files at a local path as a table, one row per file.

A ``local`` server with ``format: metadata`` stands for the files themselves rather
than the records inside them, like an ``s3`` server with that format: its schemas
describe the files (``name``, ``size``, ``lastModified``, ``created``), and every
check the contract can express runs on that table.
"""

from __future__ import annotations

import glob
import logging
import os
from datetime import datetime, timezone
from typing import Any

logger = logging.getLogger(__name__)

COLUMNS = {"name": "VARCHAR", "size": "BIGINT", "lastModified": "TIMESTAMPTZ", "created": "TIMESTAMPTZ"}


def list_file_metadata(path: str) -> list[list[Any]]:
    """The rows of the metadata table, in the order of ``COLUMNS``: one per file at ``path``.

    ``path`` is a glob (``*`` and ``?`` within one directory, ``**`` across them),
    a directory, whose files are listed recursively, or a single file.
    """
    if any(character in path for character in "*?["):
        paths = glob.glob(path, recursive=True)
    elif os.path.isdir(path):
        paths = [os.path.join(root, name) for root, _, names in os.walk(path) for name in names]
    else:
        paths = [path]
    rows = []
    for file in sorted(paths):
        if not os.path.isfile(file):
            continue
        stat = os.stat(file)
        # only some systems record when a file was created, such as macOS and Windows
        birth = getattr(stat, "st_birthtime", None)
        rows.append(
            [
                file,
                stat.st_size,
                datetime.fromtimestamp(stat.st_mtime, timezone.utc),
                datetime.fromtimestamp(birth, timezone.utc) if birth is not None else None,
            ]
        )
    logger.info("Found %d file(s) at %s", len(rows), path)
    return rows
