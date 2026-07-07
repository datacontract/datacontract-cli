"""Make ibis's Oracle schema introspection valid on Oracle releases before 23ai.

ibis builds the column-metadata queries behind ``con.table(...)`` and
``con.sql(...)`` with a bare boolean projection ``NULLABLE = 'Y'`` in the SELECT
list (see ``ibis.backends.oracle.Backend.get_schema`` /
``_get_schema_using_query``). Oracle only added a SQL boolean type in 23ai, so on
every earlier release (19c, 21c, ...) that projection is a syntax error:

    ORA-00923: FROM keyword not found where expected

The 23ai test container (``gvenzl/oracle-free``) accepts it, which is why the
bug stays invisible in CI but breaks against real-world Oracle databases.

This module re-binds ``get_schema`` and ``_get_schema_using_query`` on a
connected Oracle backend with equivalent queries that express the nullable flag
as ``CASE WHEN NULLABLE = 'Y' THEN 1 ELSE 0 END``, which is valid on all
supported Oracle versions. The override can be removed once a fixed ibis release
is available.
"""

from __future__ import annotations

import logging
import types

logger = logging.getLogger(__name__)


def apply_oracle_compatibility_patch(con) -> None:
    """Re-bind Oracle schema introspection to emit pre-23ai-compatible SQL.

    Best-effort: if the backend internals differ from what we expect (e.g. a
    future ibis refactor), the patch is skipped and the original methods stay in
    place rather than breaking the connection.
    """
    try:
        con.get_schema = types.MethodType(_get_schema, con)
        con._get_schema_using_query = types.MethodType(_get_schema_using_query, con)
    except Exception:  # pragma: no cover - defensive, never block a connection
        logger.debug("Could not apply Oracle compatibility patch", exc_info=True)


def _nullable_flag():
    """``CASE WHEN NULLABLE = 'Y' THEN 1 ELSE 0 END`` as a sqlglot expression.

    Replaces ibis's bare ``NULLABLE = 'Y'`` boolean projection, which is invalid
    in an Oracle SELECT list before 23ai.
    """
    import sqlglot.expressions as sge
    from ibis.backends.sql.compilers.base import C

    return sge.Case(
        ifs=[sge.If(this=C.nullable.eq(sge.convert("Y")), true=sge.convert(1))],
        default=sge.convert(0),
    )


def _get_schema(self, name: str, *, catalog=None, database=None, **_):
    """Drop-in for ``Backend.get_schema`` using a CASE-based nullable flag."""
    import ibis.common.exceptions as exc
    import ibis.expr.schema as sch
    import sqlglot as sg
    import sqlglot.expressions as sge
    from ibis.backends.oracle import metadata_row_to_type
    from ibis.backends.sql.compilers.base import C

    if database is None:
        database = self.con.username.upper()
    stmt = (
        sg.select(
            C.column_name,
            C.data_type,
            C.data_precision,
            C.data_scale,
            _nullable_flag().as_("nullable"),
        )
        .from_(sg.table("all_tab_columns"))
        .where(
            C.table_name.eq(sge.convert(name)),
            C.owner.eq(sge.convert(database)),
        )
        .order_by(C.column_id)
    )
    with self._safe_raw_sql(stmt) as cur:
        results = cur.fetchall()

    if not results:
        raise exc.TableNotFound(name)

    type_mapper = self.compiler.type_mapper
    fields = {
        col: metadata_row_to_type(
            type_mapper=type_mapper,
            type_string=type_string,
            precision=precision,
            scale=scale,
            nullable=bool(nullable),
        )
        for col, type_string, precision, scale, nullable in results
    }
    return sch.Schema(fields)


def _get_schema_using_query(self, query: str):
    """Drop-in for ``Backend._get_schema_using_query`` using a CASE-based flag."""
    import ibis.expr.schema as sch
    import sqlglot as sg
    import sqlglot.expressions as sge
    from ibis import util
    from ibis.backends.oracle import metadata_row_to_type
    from ibis.backends.sql.compilers.base import STAR, C

    name = util.gen_name("oracle_metadata")
    dialect = self.name

    try:
        sg_expr = sg.parse_one(query, into=sg.exp.Table, dialect=dialect)
    except sg.ParseError:
        sg_expr = sg.parse_one(query, dialect=dialect)

    if isinstance(sg_expr, sg.exp.Table):
        sg_expr = sg.select(STAR).from_(sg_expr)

    def transformer(node):
        if isinstance(node, sg.exp.Table):
            return sg.table(node.name, quoted=True)
        elif isinstance(node, sg.exp.Column):
            return sg.column(col=node.name, quoted=True)
        return node

    sg_expr = sg_expr.transform(transformer)

    this = sg.table(name, quoted=True)
    create_view = sg.exp.Create(kind="VIEW", this=this, expression=sg_expr).sql(dialect)
    drop_view = sg.exp.Drop(kind="VIEW", this=this).sql(dialect)

    metadata_query = (
        sg.select(
            C.column_name,
            C.data_type,
            C.data_precision,
            C.data_scale,
            _nullable_flag().as_("nullable"),
        )
        .from_("all_tab_columns")
        .where(C.table_name.eq(sge.convert(name)))
        .order_by(C.column_id)
        .sql(dialect)
    )

    with self.begin() as con:
        con.execute(create_view)
        try:
            results = con.execute(metadata_query).fetchall()
        finally:
            con.execute(drop_view)

    type_mapper = self.compiler.type_mapper
    schema = {}
    for col, type_string, precision, scale, nullable in results:
        schema[col] = metadata_row_to_type(
            type_mapper=type_mapper,
            type_string=type_string,
            precision=precision,
            scale=scale,
            nullable=bool(nullable),
        )

    return sch.Schema(schema)
