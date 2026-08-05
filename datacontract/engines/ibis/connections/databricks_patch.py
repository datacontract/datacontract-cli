"""Make ibis's Databricks schema introspection survive Databricks-only column types.

ibis reflects a Databricks table by reading ``DESCRIBE ... AS JSON`` and mapping
every column through ``DatabricksType.from_string`` (see
``ibis.backends.databricks._databricks_schema_to_ibis``). The whole model is
reflected in one pass, so a single column ibis cannot represent raises out of
``con.table(...)`` and every check of that model fails with the same error —
including checks on unrelated columns.

Two things are patched here:

1. ``GEOGRAPHY`` / ``GEOMETRY`` with an SRID. ibis reads the first type
   parameter as a geometry *subtype* (the PostGIS spelling
   ``GEOGRAPHY(POINT, 4326)``), but Databricks declares only the SRID,
   ``GEOGRAPHY(4326)``, so the subtype lookup fails with ``KeyError: '4326'``
   (https://github.com/datacontract/datacontract-cli/issues/1483). A lone
   numeric parameter is handed to ibis as the SRID instead.

2. Anything else ibis still cannot convert becomes ``Unknown`` for that column
   alone, with a warning naming it, so the rest of the model is still checked.
   This mirrors what the pyspark path already does for Spark types ibis has no
   mapping for (``_pyspark_table_unconvertible_as_unknown``).

Both patches are process-global (ibis looks these up as class/module attributes)
and idempotent. Point 1 can go once a fixed ibis release is available.
"""

from __future__ import annotations

import logging

logger = logging.getLogger(__name__)

_PATCHED_FLAG = "__datacontract_patched__"


def apply_databricks_compatibility_patch() -> None:
    """Patch ibis's Databricks type conversion. Safe to call more than once.

    Best-effort: if the backend internals differ from what we expect (e.g. a
    future ibis refactor), the patch is skipped and the originals stay in place
    rather than breaking the connection.
    """
    try:
        _patch_geospatial_srid()
        _patch_unconvertible_columns()
    except Exception:  # pragma: no cover - defensive, never block a connection
        logger.debug("Could not apply Databricks compatibility patch", exc_info=True)


def _patch_geospatial_srid() -> None:
    """Read a lone numeric ``GEOGRAPHY`` / ``GEOMETRY`` parameter as the SRID."""
    from ibis.backends.sql.datatypes import DatabricksType

    for geotype in ("GEOGRAPHY", "GEOMETRY"):
        original = getattr(DatabricksType, f"_from_sqlglot_{geotype}")
        if getattr(original, _PATCHED_FLAG, False):
            continue
        setattr(DatabricksType, f"_from_sqlglot_{geotype}", _srid_aware(original))


def _srid_aware(original):
    """Wrap ibis's ``_from_sqlglot_GEO*`` to accept ``GEO*(<srid>)``.

    ibis's signature is ``(subtype, srid)``; Databricks passes the SRID alone, so
    a first parameter that is a plain number is moved into the ``srid`` slot. A
    named subtype (``GEOMETRY(POINT, 4326)``) is left where it is.
    """
    # __func__ unwraps the classmethod so the wrapper can pass its own cls.
    unbound = original.__func__

    def from_sqlglot_geo(cls, arg=None, srid=None, nullable=None):
        if srid is None and _is_numeric_param(arg):
            arg, srid = None, arg
        return unbound(cls, arg, srid, nullable=nullable)

    from_sqlglot_geo.__name__ = unbound.__name__
    setattr(from_sqlglot_geo, _PATCHED_FLAG, True)
    return classmethod(from_sqlglot_geo)


def _is_numeric_param(param) -> bool:
    """True for a sqlglot type parameter that is a bare integer, e.g. ``4326``."""
    if param is None:
        return False
    try:
        int(param.this.this)
    except (AttributeError, TypeError, ValueError):
        return False
    return True


def _patch_unconvertible_columns() -> None:
    """Type a column ibis cannot convert as ``Unknown`` instead of failing the model."""
    from ibis.backends import databricks as databricks_backend

    original = databricks_backend._databricks_schema_to_ibis
    if getattr(original, _PATCHED_FLAG, False):
        return
    databricks_backend._databricks_schema_to_ibis = _tolerant_schema_reader(original)


def _tolerant_schema_reader(original):
    """Wrap ibis's ``_databricks_schema_to_ibis`` with a per-column fallback."""

    def databricks_schema_to_ibis(schema):
        try:
            return original(schema)
        except Exception:
            logger.debug("Databricks schema conversion failed, retrying column by column", exc_info=True)
        return _schema_column_by_column(original, schema)

    setattr(databricks_schema_to_ibis, _PATCHED_FLAG, True)
    return databricks_schema_to_ibis


def _schema_column_by_column(original, schema):
    """Convert each column on its own, typing the unconvertible ones as ``Unknown``."""
    import ibis.expr.datatypes as dt
    import ibis.expr.schema as sch

    fields, unknown_columns = {}, []
    for item in schema:
        name = item["name"]
        try:
            fields[name] = original([item])[name]
        except Exception:
            fields[name] = dt.unknown
            unknown_columns.append(f"{name} ({_type_name(item)})")
    if unknown_columns:
        logger.warning(
            f"Column(s) {', '.join(unknown_columns)} have a type ibis cannot represent. "
            f"Type checks for these columns will fail."
        )
    return sch.Schema(fields)


def _type_name(item) -> str:
    try:
        return str(item["type"]["name"])
    except Exception:
        return "unknown type"
