"""Absolute path to the docs content root.

Resolved from this file rather than the working directory: the docs tests must
pass whether pytest is invoked from the repository root (as CI does) or from
tests/.
"""

from pathlib import Path

DOCS = Path(__file__).resolve().parents[1] / "docs" / "docs"
