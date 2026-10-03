"""Make ibis's Impala backend work against a HiveServer2.

ibis has no Hive backend, but impyla, the driver behind ``ibis.impala``, speaks
the HiveServer2 protocol that Impala inherited from Hive. Two places in the
Impala backend assume an Impala server:

- ``get_schema`` reads ``DESCRIBE <table>`` by the column names Impala returns
  (``name``, ``type``); Hive returns ``col_name``, ``data_type``, and appends a
  ``# Partition Information`` section that repeats the partition columns.
- The compiler groups by position (``GROUP BY 1``), which Hive rejects
  (``Expression not in GROUP BY key``); grouping by the expressions works on
  both.
"""

from __future__ import annotations

import types


def _get_schema(self, table_name: str, *, catalog=None, database=None):
    """``DESCRIBE`` read by position: column name, type, comment."""
    import ibis.expr.schema as sch
    import sqlglot as sg
    import sqlglot.expressions as sge

    table = sg.table(table_name, db=database or catalog, quoted=self.compiler.quoted)
    with self._safe_raw_sql(sge.Describe(this=table)) as cur:
        rows = cur.fetchall()

    columns = []
    for row in rows:
        name = (row[0] or "").strip()
        # a blank row or a `#` header starts the partition / detailed information section
        if not name or name.startswith("#"):
            break
        columns.append((name, self.compiler.type_mapper.from_string(row[1].strip())))
    return sch.Schema.from_tuples(columns)


def _hive_compiler():
    from ibis.backends.sql.compilers.impala import ImpalaCompiler

    class HiveCompiler(ImpalaCompiler):
        @staticmethod
        def _generate_groups(groups):
            return groups

    return HiveCompiler()


def apply_hive_compatibility_patch(con) -> None:
    con.compiler = _hive_compiler()
    con.get_schema = types.MethodType(_get_schema, con)
