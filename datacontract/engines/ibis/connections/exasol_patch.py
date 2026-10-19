from __future__ import annotations

import types


def _raw_sql(self, query):
    return self.con.execute(query)


def _from_sqlglot_GEOMETRY(cls, arg=None, srid=None, nullable=None):
    from ibis.backends.sql.datatypes import ExasolType

    # Exasol spells it GEOMETRY(srid); ibis expects GEOMETRY(POINT, srid)
    if arg is not None and srid is None and str(arg.this.this).isdigit():
        srid, arg = arg, None
    return super(ExasolType, cls)._from_sqlglot_GEOMETRY(arg, srid, nullable=nullable)


def apply_exasol_compatibility_patch(con) -> None:
    from ibis.backends.sql.datatypes import ExasolType

    if not hasattr(con, "raw_sql"):
        con.raw_sql = types.MethodType(_raw_sql, con)
    ExasolType._from_sqlglot_GEOMETRY = classmethod(_from_sqlglot_GEOMETRY)
