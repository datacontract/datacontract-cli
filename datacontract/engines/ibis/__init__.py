import sqlglot.expressions as sge

# sqlglot 30.18 renamed Drop's `this` to `tables` and silently drops unknown args, but
# ibis 12 still passes `this`, rendering a nameless DROP. Remove once ibis 13 is the floor.
if "this" not in sge.Drop.arg_types:
    _drop_init = sge.Drop.__init__

    def _drop_init_with_this(self, **args):
        if "this" in args:
            args["tables"] = [args.pop("this")]
        _drop_init(self, **args)

    sge.Drop.__init__ = _drop_init_with_this
