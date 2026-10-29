"""Rules on nested properties of Snowflake columns.

ibis reads every nested Snowflake column, structured or not, as untyped json, so the values
are walked as VARIANTs and cast to the property's declared type where a rule compares them.
"""

from __future__ import annotations

import ibis
import ibis.expr.datatypes as dt


@ibis.udf.scalar.builtin
def to_variant(value) -> dt.json: ...


@ibis.udf.scalar.builtin
def get_ignore_case(value: dt.json, key: str) -> dt.json:
    """The exact spelling of ``key`` first, else another case of it; NULL where ``value`` is no object."""


@ibis.udf.scalar.builtin
def is_null_value(value: dt.json) -> bool: ...


@ibis.udf.scalar.builtin
def is_array(value: dt.json) -> bool: ...


@ibis.udf.scalar.builtin
def is_object(value: dt.json) -> bool: ...


@ibis.udf.scalar.builtin
def as_array(value: dt.json) -> dt.Array(dt.json): ...


@ibis.udf.scalar.builtin
def to_varchar(value: dt.json) -> str: ...


@ibis.udf.scalar.builtin
def try_to_number(text: str) -> dt.Decimal(38, 0): ...


@ibis.udf.scalar.builtin
def try_to_double(text: str) -> float: ...


@ibis.udf.scalar.builtin
def try_to_boolean(text: str) -> bool: ...


@ibis.udf.scalar.builtin
def try_to_date(text: str) -> dt.date: ...


@ibis.udf.scalar.builtin
def try_to_timestamp(text: str) -> dt.timestamp: ...


@ibis.udf.scalar.builtin
def try_to_time(text: str) -> dt.time: ...


_CASTS = {
    "integer": try_to_number,
    "number": try_to_double,
    "boolean": try_to_boolean,
    "date": try_to_date,
    "timestamp": try_to_timestamp,
    "time": try_to_time,
}


def row_predicate(column, field: str, build, value_type: str | None):
    """Whether ``build`` marks the row bad at the nested ``field`` of ``column``."""

    def leaf(value):
        typed = _typed(value, value_type)
        return (~_missing(value) & typed.isnull()) | build(typed)

    return _walk(to_variant(column), _steps(field)[1:], leaf)


def nested_value(column, field: str, value_type: str | None):
    """The value at the nested ``field`` of ``column``, which holds no array hop."""
    value = to_variant(column)
    for key in _steps(field)[1:]:
        value = get_ignore_case(value, key)
    return _typed(value, value_type)


def item_repeats(column, field: str, value_type: str | None):
    array_path, _, leaf = field.rpartition("[]")
    leaf_steps = _steps(leaf[1:]) if leaf else []

    def repeats(array):
        def item_value(item):
            for key in leaf_steps:
                item = get_ignore_case(item, key)
            return _typed(item, value_type)

        values = as_array(array).map(item_value).filter(lambda v: v.notnull())
        return ~_missing(array) & (~is_array(array) | (values.unique().length() < values.length()))

    return _walk(to_variant(column), _steps(array_path)[1:], repeats)


def _steps(path: str) -> list[str | None]:
    """``names[].name`` as ``["names", None, "name"]``, where None steps into an array's items."""
    steps = []
    for part in path.split("."):
        steps.append(part.split("[", 1)[0])
        steps.extend([None] * part.count("[]"))
    return steps


def _walk(value, steps: list[str | None], build, element: bool = False):
    if not steps:
        return build(value)
    if steps[0] is None:
        items = as_array(value).map(lambda item: _walk(item, steps[1:], build, element=True))
        return ~_missing(value) & (~is_array(value) | items.contains(True))
    # bound to a lambda parameter, as the SQL would otherwise repeat the whole path several times per step
    below = ibis.array([get_ignore_case(value, steps[0])]).map(lambda child: _walk(child, steps[1:], build))
    below = below.contains(True)
    if element:
        # a missing element is an element whose properties are all missing
        return (~_missing(value) & ~is_object(value)) | below
    # a missing object excuses its properties; its own `required` catches its absence
    return ~_missing(value) & (~is_object(value) | below)


def _missing(value):
    return value.isnull() | is_null_value(value)


def _typed(value, value_type: str | None):
    """The value cast as Snowflake casts it, NULL where missing or where it cannot be cast."""
    if value_type in _CASTS:
        typed = _CASTS[value_type](to_varchar(value))
    elif value_type == "string":
        typed = ibis.ifelse(is_object(value) | is_array(value), ibis.null(), to_varchar(value))
    elif value_type == "array":
        typed = as_array(value)
    else:
        typed = value
    return ibis.ifelse(_missing(value), ibis.null(), typed)
