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

# Each group is a single Snowflake type under different names, which its catalog
# reports as the one canonical name (TEXT, NUMBER, FLOAT), so a contract declaring
# any of the aliases must match its own column. Dialect-specific because elsewhere
# (MySQL, SQL Server) TEXT and VARCHAR, or INT and DECIMAL, are distinct types.
_SNOWFLAKE_FAMILIES = (
    {exp.DataType.Type.VARCHAR, exp.DataType.Type.TEXT, exp.DataType.Type.NVARCHAR},
    # exact numerics: INT/INTEGER/BIGINT/SMALLINT/TINYINT/BYTEINT/NUMERIC are NUMBER(38,0)
    {
        exp.DataType.Type.DECIMAL,
        exp.DataType.Type.INT,
        exp.DataType.Type.BIGINT,
        exp.DataType.Type.SMALLINT,
        exp.DataType.Type.TINYINT,
    },
    # approximate numerics: FLOAT/FLOAT4/FLOAT8/DOUBLE/REAL are all 64-bit FLOAT
    {exp.DataType.Type.DOUBLE, exp.DataType.Type.FLOAT},
)


def _dialect_name(dialect) -> str:
    if isinstance(dialect, str):
        return dialect.lower()
    name = getattr(dialect, "__name__", None) or type(dialect).__name__
    return name.lower()


def _is_snowflake(dialect) -> bool:
    return _dialect_name(dialect) == "snowflake"


# Athena DDL is written in Hive spellings while its catalog reports the Trino
# names: STRING and VARCHAR are the same type there, and `datacontract import
# athena` carries the Hive spelling (array<string>) into the contract.
_TRINO_DIALECTS = {"athena", "trino", "presto"}
_TRINO_TEXT_FAMILY = {exp.DataType.Type.VARCHAR, exp.DataType.Type.TEXT}


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


def _base_compatible(exp_dt: exp.DataType, act_dt: exp.DataType, dialect) -> bool:
    """Whether two parsed types share a base type, up to dialect aliases."""
    both_numeric = {exp_dt.this, act_dt.this} <= exp.DataType.NUMERIC_TYPES
    return (
        exp_dt.this == act_dt.this
        or {exp_dt.this, act_dt.this} <= _TIMESTAMP_FAMILY
        or (both_numeric and _base_sql(exp_dt, dialect) == _base_sql(act_dt, dialect))
        or (_is_snowflake(dialect) and any({exp_dt.this, act_dt.this} <= family for family in _SNOWFLAKE_FAMILIES))
        or (_dialect_name(dialect) in _TRINO_DIALECTS and {exp_dt.this, act_dt.this} <= _TRINO_TEXT_FAMILY)
    )


# Types whose parameters are nested types or named fields rather than
# length/precision numbers (Snowflake OBJECT/ARRAY/MAP, BigQuery STRUCT).
_STRUCTURED_TYPES = {
    exp.DataType.Type.OBJECT,
    exp.DataType.Type.STRUCT,
    exp.DataType.Type.ARRAY,
    exp.DataType.Type.MAP,
}


def _is_structured(dtype: exp.DataType) -> bool:
    return dtype.this in _STRUCTURED_TYPES


def _scalar_params_equal(exp_dt: exp.DataType, act_dt: exp.DataType) -> bool:
    """Compare length/precision parameters. ``DECIMAL(p)`` means ``DECIMAL(p, 0)``
    in every supported dialect, so a missing scale is compared as 0."""
    expected, actual = _params(exp_dt), _params(act_dt)
    if {exp_dt.this, act_dt.this} <= exp.DataType.NUMERIC_TYPES:
        if len(expected) == 1:
            expected = expected + ["0"]
        if len(actual) == 1:
            actual = actual + ["0"]
    return expected == actual


def _fields(dtype: exp.DataType) -> Optional[dict[str, exp.DataType]]:
    """Named fields of an OBJECT/STRUCT type, or ``None`` if any child is not a
    plain ``name type`` field definition."""
    fields: dict[str, exp.DataType] = {}
    for child in dtype.expressions:
        if not isinstance(child, exp.ColumnDef) or child.kind is None:
            return None
        fields[child.name.lower()] = child.kind
    return fields


def _dtype_matches(exp_dt: exp.DataType, act_dt: exp.DataType, dialect) -> bool:
    """Structural comparison of two parsed types, for structured types and their
    children: bases match up to dialect aliases; a side without parameters or
    fields constrains nothing (a declared bare ``OBJECT`` matches any object
    column, and a catalog that strips the field list — ``INFORMATION_SCHEMA``
    reports a structured column as its bare token — cannot contradict the
    declared fields); OBJECT/STRUCT fields are matched by name, without regard
    to order, and their types compared recursively."""
    if not _base_compatible(exp_dt, act_dt, dialect):
        return False

    exp_children = exp_dt.expressions
    act_children = act_dt.expressions
    if not exp_children or not act_children:
        return True

    if exp_dt.this in (exp.DataType.Type.OBJECT, exp.DataType.Type.STRUCT):
        exp_fields, act_fields = _fields(exp_dt), _fields(act_dt)
        if exp_fields is None or act_fields is None:
            return _params(exp_dt) == _params(act_dt)
        if set(exp_fields) != set(act_fields):
            return False
        return all(_dtype_matches(exp_fields[name], act_fields[name], dialect) for name in exp_fields)

    if all(isinstance(child, exp.DataType) for child in [*exp_children, *act_children]):
        # ARRAY element / MAP key and value types
        if len(exp_children) != len(act_children):
            return False
        return all(_dtype_matches(e, a, dialect) for e, a in zip(exp_children, act_children))

    return _scalar_params_equal(exp_dt, act_dt)


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

    if not _base_compatible(exp_dt, act_dt, dialect):
        return False, f"expected physical type '{expected}' but the column is '{actual}'"

    # Structured types carry nested types and named fields as their parameters,
    # so they are compared structurally rather than as rendered strings (field
    # order and dialect aliases inside the fields must not matter).
    if _is_structured(exp_dt) or _is_structured(act_dt):
        if _dtype_matches(exp_dt, act_dt, dialect):
            return True, ""
        return False, f"expected physical type '{expected}' but the column is '{actual}'"

    # sqlglot fills in a dialect's default precision (a bare NUMBER parses as
    # DECIMAL(38,0)), so what the contract declares is read off the raw string.
    if _split_base(_normalize_raw(expected))[1] and not _scalar_params_equal(exp_dt, act_dt):
        return False, f"expected physical type '{expected}' but the column is '{actual}'"

    return True, ""
