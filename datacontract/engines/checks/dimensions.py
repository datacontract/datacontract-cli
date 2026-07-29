"""Default data quality dimensions for the CLI's built-in checks.

ODCS lets a contract author tag a `quality` rule with a `dimension`. The checks
the CLI derives from the schema block and from `slaProperties` have no such
field, so this module assigns each one the dimension it measures. That makes
`datacontract test --dimension` select the built-in checks too, instead of only
the minority of rules an author tagged by hand.

An author-declared `quality.dimension` always wins; this is only the fallback
for checks that cannot declare one.
"""

from __future__ import annotations

from typing import Optional

# Keyed by CheckSpec.type (and, for the Azure blob engine, Check.type).
DEFAULT_DIMENSIONS: dict[str, str] = {
    # completeness — a value the contract requires is absent
    "field_required": "completeness",
    "field_primary_key_required": "completeness",
    "azure_file_property_required": "completeness",
    # uniqueness — the contract forbids duplicates
    "field_unique": "uniqueness",
    "field_primary_key_unique": "uniqueness",
    "primary_key_unique": "uniqueness",
    # conformity — the data deviates from the declared shape, type, or value domain
    "field_is_present": "conformity",
    "field_type": "conformity",
    "field_physical_type": "conformity",
    "field_nested_type": "conformity",
    "field_nested_physical_type": "conformity",
    "field_regex": "conformity",
    "field_enum": "conformity",
    "field_min_length": "conformity",
    "field_max_length": "conformity",
    "field_minimum": "conformity",
    "field_maximum": "conformity",
    "field_not_equal": "conformity",
    # the JSON Schema validation checks, which all share the type "schema"
    "schema": "conformity",
    # the dataset does not conform to the retention period it promises
    "servicelevel_retention": "conformity",
    # timeliness — the data is not current
    "servicelevel_freshness": "timeliness",
}


def default_dimension(check_type: Optional[str]) -> Optional[str]:
    """The dimension a built-in check measures, or None if it has no natural one."""
    if check_type is None:
        return None
    return DEFAULT_DIMENSIONS.get(check_type)
