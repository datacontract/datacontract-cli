"""Coarse type-category normalization for schema ``field_type`` checks.

The legacy soda engine compared the data source's reported SQL type string
against a per-dialect equivalence table (``SCHEMA_CHECK_TYPES_MAPPING``). The
ibis engine instead normalizes both the contract's declared type and the actual
column's ibis dtype into a small set of categories and compares those. This
sidesteps dialect-specific type-name differences (``varchar`` vs ``text`` vs
``string``) while still catching genuine mismatches (e.g. string vs integer).
"""

from __future__ import annotations

import re

# Categories returned by normalization.
NUMERIC = {"integer", "number", "decimal", "float"}


def normalize_type_name(type_name: str | None) -> str:
    """Map a contract type name (logical or physical) to a coarse category."""
    if not type_name:
        return "other"
    name = type_name.strip().lower()
    # strip parameters like varchar(10) / decimal(10,2) and array<...> wrappers
    name = re.sub(r"\(.*\)", "", name)
    name = re.sub(r"<.*>", "", name).strip()

    if name in {
        "varchar",
        "char",
        "character",
        "character varying",
        "nvarchar",
        "nchar",
        "text",
        "string",
        "str",
        "clob",
        "nclob",
        "uuid",
        "enum",
    }:
        return "string"
    if name in {
        "int",
        "integer",
        "bigint",
        "smallint",
        "tinyint",
        "long",
        "short",
        "int2",
        "int4",
        "int8",
        "serial",
        "bigserial",
        "smallserial",
        "int64",
        "int32",
        "int16",
        "int8",
        "byteint",
    }:
        return "integer"
    if name in {"decimal", "numeric", "dec"}:
        return "decimal"
    if name in {"number"}:
        return "number"
    if name in {
        "float",
        "double",
        "double precision",
        "real",
        "float4",
        "float8",
        "float32",
        "float64",
        "binary_float",
        "binary_double",
    }:
        return "float"
    if name in {"bool", "boolean", "bit", "logical"}:
        return "boolean"
    if name in {
        "timestamp",
        "timestamptz",
        "timestamp without time zone",
        "timestamp with time zone",
        "timestamp_tz",
        "timestamp_ntz",
        "timestamp_ltz",
        "datetime",
        "datetime2",
        "smalldatetime",
    }:
        return "timestamp"
    if name in {"date"}:
        return "date"
    if name in {"time", "time without time zone", "time with time zone"}:
        return "time"
    if name in {"bytes", "binary", "varbinary", "blob", "bytea", "raw"}:
        return "binary"
    if name in {"struct", "record", "object", "row", "json", "jsonb", "variant", "map", "interval"}:
        # json/struct/object/map all collapse to a single nested category for matching
        if name == "map":
            return "map"
        return "struct"
    if name in {"array", "list"}:
        return "array"
    if name in {"null", "none", "void"}:
        return "null"
    return "other"


def category_matches(expected: str, actual: str) -> bool:
    """Return True if an actual column category satisfies the expected category.

    Lenient on purpose: unknown categories ("other") always match, and the
    numeric family is treated as compatible to avoid false failures where a
    contract says ``number`` but the engine reports ``decimal``/``float``/``int``.
    """
    if expected == actual:
        return True
    if expected == "other" or actual == "other":
        return True
    # ODCS "number" is intentionally ambiguous: accept any numeric storage.
    if expected == "number" and actual in NUMERIC:
        return True
    if actual == "number" and expected in NUMERIC:
        return True
    # decimal/float are routinely interchangeable across engines.
    if expected in {"decimal", "float"} and actual in {"decimal", "float"}:
        return True
    # struct/object/json all collapse together.
    if expected in {"struct"} and actual in {"struct"}:
        return True
    return False
