"""CSV text converted to the contract's types: one definition for the typed table and the type check on the text."""

import datetime
from typing import Optional

from open_data_contract_standard.model import SchemaProperty

from datacontract.export.duckdb_type_converter import convert_to_duckdb_csv_type

# The DuckDB type of each converted column and its ibis spelling; any other column stays text
CSV_TYPES = {
    "BIGINT": "int64",
    "DOUBLE": "float64",
    "BOOLEAN": "boolean",
    "DATE": "date",
    "TIMESTAMP": "timestamp",
    "TIME": "time",
}
_DATE_TIME_TYPES = {"DATE", "TIMESTAMP", "TIME"}

# Java DateTimeFormatter letters (ODCS logicalTypeOptions.format) and their strptime directives, longest first
_PATTERN_LETTERS = [
    ("yyyy", "%Y"),
    ("uuuu", "%Y"),
    ("yy", "%y"),
    ("MMMM", "%B"),
    ("MMM", "%b"),
    ("MM", "%m"),
    ("M", "%-m"),
    ("dd", "%d"),
    ("d", "%-d"),
    ("HH", "%H"),
    ("H", "%-H"),
    ("hh", "%I"),
    ("h", "%-I"),
    ("mm", "%M"),
    ("m", "%-M"),
    ("ss", "%S"),
    ("s", "%-S"),
    ("SSSSSS", "%f"),
    ("SSS", "%g"),
    ("a", "%p"),
    ("EEEE", "%A"),
    ("EEE", "%a"),
    # XXX is left out: it writes a zero offset as Z, which %z does not read
    ("xxx", "%z"),
    ("Z", "%z"),
]


def strptime_format(pattern: str) -> Optional[str]:
    """The strptime format of a Java DateTimeFormatter pattern, or None for a pattern it cannot express."""
    out = []
    i = 0
    while i < len(pattern):
        c = pattern[i]
        if c == "'":
            end = pattern.find("'", i + 1)
            if end == -1:
                return None
            out.append("'" if end == i + 1 else pattern[i + 1 : end].replace("%", "%%"))
            i = end + 1
        elif c.isalpha():
            letters = next((pair for pair in _PATTERN_LETTERS if pattern.startswith(pair[0], i)), None)
            if letters is None:
                return None
            out.append(letters[1])
            i += len(letters[0])
        else:
            out.append("%%" if c == "%" else c)
            i += 1
    return "".join(out)


def csv_type(prop: SchemaProperty) -> Optional[str]:
    """The DuckDB type a CSV column is converted to, or None for a column that stays text."""
    duckdb_type = convert_to_duckdb_csv_type(prop)
    return duckdb_type if duckdb_type in CSV_TYPES else None


def csv_format(prop: SchemaProperty, duckdb_type: Optional[str]) -> Optional[str]:
    """The declared format of a date, timestamp or time column, or None if strptime cannot express it (ISO 8601 then)."""
    if duckdb_type not in _DATE_TIME_TYPES or not prop.logicalTypeOptions:
        return None
    pattern = prop.logicalTypeOptions.get("format")
    return pattern if pattern and strptime_format(pattern) is not None else None


def csv_value(text, duckdb_type: str, pattern: Optional[str] = None):
    """The ibis expression converting `text` to `duckdb_type`: NULL for a value that does not convert."""
    import ibis

    target = CSV_TYPES[duckdb_type]
    if duckdb_type == "BIGINT":
        # A cast would round 2.50
        return text.strip().re_search(r"^[+-]?[0-9]+$").ifelse(text.strip().try_cast(target), ibis.null(target))
    if pattern is not None and duckdb_type in _DATE_TIME_TYPES:

        @ibis.udf.scalar.builtin
        def try_strptime(value: str, format: str) -> datetime.datetime:  # -> TRY_STRPTIME(value, format)
            ...

        return try_strptime(text, strptime_format(pattern)).cast(target)
    return text.try_cast(target)
