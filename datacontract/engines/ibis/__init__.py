import sqlglot.expressions as sge
from sqlglot.dialects.tsql import TSQL
from sqlglot.generator import Generator

# sqlglot 30.18 renamed Drop's `this` to `tables`; ibis 12 still passes `this`. Remove once ibis 13 is the floor.
# Patches the generators, not Drop.__init__, which compiled sqlglot (sqlglotc) never calls.
if "this" not in sge.Drop.arg_types:
    for generator in (Generator, TSQL.Generator):

        def _drop_sql_with_this(self, expression, _drop_sql=generator.drop_sql):
            if expression.args.get("this") and not expression.args.get("tables"):
                expression = expression.copy()
                expression.set("tables", [expression.args.pop("this")])
            return _drop_sql(self, expression)

        generator.drop_sql = _drop_sql_with_this
