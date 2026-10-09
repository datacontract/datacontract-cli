"""The values of a CSV file, read as text, converted to the types the contract declares.

One definition serves both the table the checks read and the type check on the text, so a value the type check
reports is the same value the table holds as NULL: the other checks on its column treat it as missing.
"""

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
    """The declared format of a date, timestamp or time column (Java DateTimeFormatter), or None.

    A format strptime cannot express is None too, so the column is read as ISO 8601; the type check says so.
    """
    if duckdb_type not in _DATE_TIME_TYPES or not prop.logicalTypeOptions:
        return None
    pattern = prop.logicalTypeOptions.get("format")
    return pattern if pattern and strptime_format(pattern) is not None else None


def csv_value(text, duckdb_type: str, pattern: Optional[str] = None):
    """The ibis expression converting `text` to `duckdb_type`: NULL for a value that does not convert.

    An integer is a whole number, not 2.50 or 2.00, which a cast would round. A date, timestamp or time in a
    declared format must be in that format and exist; without one, it is ISO 8601.
    """
    import ibis

    target = CSV_TYPES[duckdb_type]
    if duckdb_type == "BIGINT":
        return text.strip().re_search(r"^[+-]?[0-9]+$").ifelse(text.strip().try_cast(target), ibis.null(target))
    if pattern is not None and duckdb_type in _DATE_TIME_TYPES:

        @ibis.udf.scalar.builtin
        def try_strptime(value: str, format: str) -> datetime.datetime:  # -> TRY_STRPTIME(value, format)
            ...

        return try_strptime(text, strptime_format(pattern)).cast(target)
    return text.try_cast(target)
