"""Engine-neutral check intermediate representation (IR).

``create_checks`` (see ``create_checks.py``) walks an ODCS data contract and
produces a list of :class:`CheckSpec` objects. The ibis execution engine
(``datacontract/engines/ibis``) compiles each :class:`CheckSpec` into an ibis
expression, runs it, and evaluates the structured :class:`Threshold`.

This IR replaces the SodaCL-string ``Check.implementation`` that the old
``data_contract_checks.py`` produced: it carries *what* each check asserts
(metric + threshold + arguments) rather than a backend-specific SQL/YAML string.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import TYPE_CHECKING, Any, List, Optional

if TYPE_CHECKING:
    from open_data_contract_standard.model import SchemaProperty


class MetricType(str, Enum):
    """The kind of value a check computes against a model/field."""

    ROW_COUNT = "row_count"
    MISSING_COUNT = "missing_count"
    DUPLICATE_COUNT = "duplicate_count"
    INVALID_COUNT = "invalid_count"
    FIELD_PRESENT = "field_present"
    FIELD_TYPE = "field_type"
    FRESHNESS = "freshness"
    RETENTION = "retention"
    CUSTOM_SQL = "custom_sql"
    # A check the new engine cannot run (e.g. raw SodaCL custom checks).
    UNSUPPORTED = "unsupported"


class Op(str, Enum):
    EQ = "="
    NE = "!="
    GT = ">"
    GE = ">="
    LT = "<"
    LE = "<="
    BETWEEN = "between"
    NOT_BETWEEN = "not_between"


@dataclass
class Threshold:
    """A structured comparison applied to a computed metric value."""

    op: Op
    value: Any = None
    value2: Any = None  # only used for between / not_between

    def passes(self, actual: Any) -> bool:
        if actual is None:
            return False
        a = actual
        v = self.value
        if self.op == Op.EQ:
            return bool(a == v)
        if self.op == Op.NE:
            return bool(a != v)
        if self.op == Op.GT:
            return bool(a > v)
        if self.op == Op.GE:
            return bool(a >= v)
        if self.op == Op.LT:
            return bool(a < v)
        if self.op == Op.LE:
            return bool(a <= v)
        if self.op == Op.BETWEEN:
            return bool(v <= a <= self.value2)
        if self.op == Op.NOT_BETWEEN:
            return not bool(v <= a <= self.value2)
        return False

    def describe(self) -> str:
        if self.op == Op.BETWEEN:
            return f"between {self.value} and {self.value2}"
        if self.op == Op.NOT_BETWEEN:
            return f"not between {self.value} and {self.value2}"
        return f"{self.op.value} {self.value}"


@dataclass
class CheckSpec:
    """A single, engine-neutral data quality / schema check."""

    key: str
    category: str  # schema | quality | servicelevel | custom
    type: str  # stable check type string (e.g. "field_required"), preserved from the legacy engine
    name: str
    model: str
    metric: MetricType
    field: Optional[str] = None
    threshold: Optional[Threshold] = None

    # The threshold compares a percentage of rows (ODCS quality.unit: percent)
    # rather than an absolute count. Only meaningful for the count-of-bad-rows
    # metrics (missing_count, invalid_count), where the engine divides by the
    # model row count before applying the threshold.
    threshold_is_percent: bool = False

    # ODCS quality.severity. A non-blocking severity (e.g. "warning", "info")
    # downgrades a failing check to a warning instead of a failure. None => fail.
    severity: Optional[str] = None

    # --- metric arguments -------------------------------------------------
    missing_values: Optional[List[Any]] = None  # MISSING_COUNT / INVALID_COUNT
    valid_values: Optional[List[Any]] = None  # INVALID_COUNT
    invalid_values: Optional[List[Any]] = None  # INVALID_COUNT
    valid_regex: Optional[str] = None  # INVALID_COUNT
    valid_min: Any = None  # INVALID_COUNT
    valid_max: Any = None  # INVALID_COUNT
    valid_min_length: Optional[int] = None  # INVALID_COUNT
    valid_max_length: Optional[int] = None  # INVALID_COUNT

    expected_category: Optional[str] = None  # FIELD_TYPE: human-readable label (display only)
    expected_type_label: Optional[str] = None  # FIELD_TYPE: human-readable expected type
    expected_schema_property: Optional["SchemaProperty"] = None  # FIELD_TYPE: structural comparison

    columns: Optional[List[str]] = None  # DUPLICATE_COUNT across multiple columns

    query: Optional[str] = None  # CUSTOM_SQL (placeholders already substituted)
    dialect: Optional[str] = None  # CUSTOM_SQL input SQL dialect

    seconds: Optional[int] = None  # FRESHNESS / RETENTION threshold in seconds

    uses_raw_view: bool = False  # FIELD_PRESENT against the duckdb {model}__raw__ view

    # Preset result/reason for checks that are not executed (UNSUPPORTED).
    preset_result: Optional[str] = None
    preset_reason: Optional[str] = None

    def has_validity_constraints(self) -> bool:
        return any(
            v is not None
            for v in (
                self.valid_values,
                self.valid_regex,
                self.valid_min,
                self.valid_max,
                self.valid_min_length,
                self.valid_max_length,
            )
        )
