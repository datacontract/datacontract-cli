"""Compare a contract ``physicalType`` against a column's real native type.

Both sides are parsed with sqlglot in the server's dialect, so dialect aliases
(``int`` ≡ ``integer``, ``decimal`` ≡ ``numeric``) and case are handled, while
genuinely distinct native types (``varchar`` vs ``nvarchar``) stay distinct.

Length/precision is only enforced when the contract declares it: a bare
``varchar`` in the contract matches ``varchar(255)`` in the database, but
``varchar(255)`` does not match ``varchar(100)``.

``physical_type_matches`` returns a tri-state:

- ``True``  — the native type satisfies the declared ``physicalType``
- ``False`` — it does not (with a human-readable reason)
- ``None``  — the declared type cannot be interpreted in the server's dialect
  (e.g. a SQL Server ``uniqueidentifier`` declared while testing Snowflake), so
  the caller should skip the check with a warning rather than fail it.
"""

from __future__ import annotations

import re
from typing import Optional, Tuple

import sqlglot
from sqlglot import exp

# Tokens that mean "sqlglot parsed something, but not a type it understands".
_UNRESOLVED = {exp.DataType.Type.UNKNOWN, exp.DataType.Type.USERDEFINED, exp.DataType.Type.NULL}


def _timestamp_family() -> set:
    """Timestamp tokens that differ only by timezone handling.

    A declared ``timestamp`` is treated as compatible with a ``timestamp with
    time zone`` column: they are the same base type and the distinction is not
    modelled at the logical level many contracts are written at (in particular,
    DCS contracts store the logical ``timestamp`` keyword as the physicalType).
    """
    names = ("TIMESTAMP", "TIMESTAMPTZ", "TIMESTAMPLTZ", "TIMESTAMPNTZ", "TIMESTAMP_S", "TIMESTAMP_MS", "TIMESTAMP_NS")
    return {getattr(exp.DataType.Type, n) for n in names if hasattr(exp.DataType.Type, n)}


_TIMESTAMP_FAMILY = _timestamp_family()

# In Snowflake these are one type, and its INFORMATION_SCHEMA reports a VARCHAR
# column as TEXT, so a contract declaring VARCHAR would never match its own
# column. Dialect-specific because elsewhere (MySQL, SQL Server) TEXT and VARCHAR
# are genuinely different types.
_SNOWFLAKE_TEXT_FAMILY = {
    exp.DataType.Type.VARCHAR,
    exp.DataType.Type.TEXT,
    exp.DataType.Type.NVARCHAR,
}


def _is_snowflake(dialect) -> bool:
    name = getattr(dialect, "__name__", None) or type(dialect).__name__
    return str(name).lower() == "snowflake" or str(dialect).lower() == "snowflake"


def _parse(type_str: str, dialect) -> Optional[exp.DataType]:
    """Parse a type string into an ``exp.DataType`` for ``dialect``, or ``None``."""
    if not type_str or not type_str.strip():
        return None
    try:
        parsed = sqlglot.parse_one(type_str.strip(), into=exp.DataType, dialect=dialect)
    except Exception:
        return None
    if not isinstance(parsed, exp.DataType) or parsed.this in _UNRESOLVED:
        return None
    return parsed


def _params(dtype: exp.DataType) -> list[str]:
    """Rendered type parameters (length / precision / scale), normalized for comparison."""
    return [e.sql().strip().lower() for e in dtype.expressions]


def _normalize_raw(type_str: str) -> str:
    return re.sub(r"\s+", " ", type_str.strip().lower())


def _split_base(type_str: str):
    """Split ``varchar(255)`` into ``('varchar', '(255)')``."""
    i = type_str.find("(")
    if i == -1:
        return type_str.strip(), ""
    return type_str[:i].strip(), type_str[i:].strip()


def _raw_match(expected: str, actual: str) -> Optional[bool]:
    """String-level comparison for types sqlglot cannot parse (Oracle ROWID,
    RAW, INTERVAL …). Returns True/False, matching on the base type name and
    enforcing parameters only when the contract declares them; the length-only
    difference (``raw`` vs ``raw(2000)``) is treated as a match.
    """
    e, a = _normalize_raw(expected), _normalize_raw(actual)
    if e == a:
        return True
    e_base, e_params = _split_base(e)
    a_base, _ = _split_base(a)
    if e_base != a_base:
        return False
    return True if not e_params else e == a


def _base_sql(dtype: exp.DataType, dialect) -> str:
    """Render the bare base type in ``dialect``, collapsing that dialect's aliases."""
    return exp.DataType(this=dtype.this).sql(dialect=dialect).lower()


def physical_type_matches(
    expected: Optional[str],
    actual: Optional[str],
    dialect,
) -> Tuple[Optional[bool], str]:
    """Compare a declared ``physicalType`` against an actual native type.

    ``dialect`` is a sqlglot dialect (name or Dialect) for the server under test.
    Returns ``(result, reason)`` where ``result`` is ``True`` / ``False`` /
    ``None`` (skip) as described in the module docstring.
    """
    if not expected or not expected.strip() or not actual or not actual.strip():
        return None, "no physical type to compare; skipping the physical type check"

    exp_dt = _parse(expected, dialect)
    act_dt = _parse(actual, dialect)

    # When both sides are types sqlglot cannot model (e.g. Oracle ROWID / RAW /
    # INTERVAL), fall back to a string-level comparison so an identical column
    # still matches. When only the declared type is unparseable while the column
    # is an ordinary type, the physicalType is foreign to this server's dialect
    # (e.g. a SQL Server 'uniqueidentifier' declared against Snowflake): skip.
    if exp_dt is None and act_dt is None:
        if _raw_match(expected, actual):
            return True, ""
        return False, f"expected physical type '{expected}' but the column is '{actual}'"
    if exp_dt is None or act_dt is None:
        return None, (
            f"physicalType '{expected}' could not be interpreted in the '{dialect}' dialect of the "
            f"server under test; skipping the physical type check"
        )

    both_numeric = {exp_dt.this, act_dt.this} <= exp.DataType.NUMERIC_TYPES
    same_base = (
        exp_dt.this == act_dt.this
        or {exp_dt.this, act_dt.this} <= _TIMESTAMP_FAMILY
        or (both_numeric and _base_sql(exp_dt, dialect) == _base_sql(act_dt, dialect))
        or (_is_snowflake(dialect) and {exp_dt.this, act_dt.this} <= _SNOWFLAKE_TEXT_FAMILY)
    )
    if not same_base:
        return False, f"expected physical type '{expected}' but the column is '{actual}'"

    expected_params = _params(exp_dt)
    if expected_params and expected_params != _params(act_dt):
        return False, f"expected physical type '{expected}' but the column is '{actual}'"

    return True, ""
