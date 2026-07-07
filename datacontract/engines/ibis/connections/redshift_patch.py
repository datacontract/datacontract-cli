"""Make ibis's Postgres schema introspection valid on Amazon Redshift.

Redshift has no dedicated ibis backend; it rides the Postgres backend over the
Postgres wire protocol (see ``connect.py``). ibis builds the column-metadata
query behind ``con.table(...)`` (``ibis.backends.postgres.Backend.get_schema``)
with an enum-detection ``CASE`` that joins ``pg_catalog.pg_enum``:

    CASE WHEN EXISTS(
      SELECT 1 FROM pg_catalog.pg_type t
      INNER JOIN pg_catalog.pg_enum e ON e.enumtypid = t.oid ...
    ) THEN 'enum' ELSE pg_catalog.format_type(...) END

PostgreSQL exposes ``pg_catalog.pg_enum``; Redshift does not, so introspecting
any model fails with:

    relation "pg_catalog.pg_enum" does not exist

Redshift has no enum types, so the ``CASE`` is pointless there. This module
re-binds ``get_schema`` on a connected backend with the same query minus the
enum join, reading the column type straight from ``pg_catalog.format_type``.
``_get_schema_using_query`` (custom-SQL introspection) calls ``self.get_schema``
internally, so it inherits the fix without a separate override. The patch can be
removed once a fixed ibis release is available.
"""

from __future__ import annotations

import logging
import types

logger = logging.getLogger(__name__)

# ibis's get_schema query without the pg_enum-dependent enum CASE. Every other
# relation (pg_attribute / pg_class / pg_namespace) and pg_catalog.format_type
# is supported by Redshift's leader-node catalog.
_TYPE_INFO_SQL = """\
SELECT
  a.attname AS column_name,
  pg_catalog.format_type(a.atttypid, a.atttypmod) AS data_type,
  NOT a.attnotnull AS nullable
FROM pg_catalog.pg_attribute a
INNER JOIN pg_catalog.pg_class c
   ON a.attrelid = c.oid
INNER JOIN pg_catalog.pg_namespace n
   ON c.relnamespace = n.oid
WHERE a.attnum > 0
  AND NOT a.attisdropped
  AND n.nspname = ANY(%(dbs)s)
  AND c.relname = %(name)s
ORDER BY a.attnum ASC"""


def apply_redshift_compatibility_patch(con) -> None:
    """Re-bind Postgres schema introspection to emit Redshift-compatible SQL.

    Best-effort: if the backend internals differ from what we expect (e.g. a
    future ibis refactor), the patch is skipped and the original method stays in
    place rather than breaking the connection.
    """
    try:
        con.get_schema = types.MethodType(_get_schema, con)
    except Exception:  # pragma: no cover - defensive, never block a connection
        logger.debug("Could not apply Redshift compatibility patch", exc_info=True)


def _get_schema(self, name: str, *, catalog=None, database=None):
    """Drop-in for ``Backend.get_schema`` without the ``pg_enum`` join."""
    import ibis.common.exceptions as com
    import ibis.expr.schema as sch

    dbs = [database or self.current_database]
    if database is None and (temp_table_db := self._session_temp_db) is not None:
        dbs.append(temp_table_db)

    type_mapper = self.compiler.type_mapper
    con = self.con
    params = {"dbs": dbs, "name": name}
    with con.cursor() as cursor, con.transaction():
        rows = cursor.execute(_TYPE_INFO_SQL, params, prepare=True).fetchall()

    if not rows:
        raise com.TableNotFound(name)

    return sch.Schema({col: type_mapper.from_string(typestr, nullable=nullable) for col, typestr, nullable in rows})
