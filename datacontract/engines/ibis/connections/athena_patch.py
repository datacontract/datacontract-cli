"""ibis lists ``ArrayFilter`` and ``ArrayMap`` as unsupported on Athena, although Athena engine
version 3 runs the ``filter()`` / ``transform()`` its Trino compiler emits; checks on array items need them."""

from __future__ import annotations


def _athena_compiler():
    import ibis.expr.operations as ops
    from ibis.backends.sql.compilers.athena import AthenaCompiler
    from ibis.backends.sql.compilers.trino import TrinoCompiler

    lambdas = (ops.ArrayFilter, ops.ArrayMap)

    class ArrayLambdaAthenaCompiler(AthenaCompiler):
        # ibis replaces the visit method of every op still listed here
        UNSUPPORTED_OPS = tuple(op for op in AthenaCompiler.UNSUPPORTED_OPS if op not in lambdas)
        visit_ArrayFilter = TrinoCompiler.visit_ArrayFilter
        visit_ArrayMap = TrinoCompiler.visit_ArrayMap

    return ArrayLambdaAthenaCompiler()


def apply_athena_compatibility_patch(con) -> None:
    con.compiler = _athena_compiler()
