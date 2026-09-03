"""``logicalType: vector`` (ODCS v3.2.0, RFC 0042): a fixed-dimension dense numeric array.

The shape lives in ``logicalTypeOptions``: ``dimensions`` (required), and the
optional ``elementType`` (``float32`` by default), ``distanceMetric``,
``normalized``, ``embeddingModel`` and ``embeddingModelVersion``. The
``physicalType`` carries the platform's own spelling, such as pgvector's
``vector(1536)``, Snowflake's ``VECTOR(FLOAT, 1536)`` or DuckDB's ``FLOAT[1536]``,
which is also where the dimensions are read from when the options omit them.
"""

import re
from typing import Optional

from open_data_contract_standard.model import SchemaProperty

DEFAULT_ELEMENT_TYPE = "float32"

# pgvector: vector(1536), halfvec(768); Snowflake: VECTOR(FLOAT, 1536), VECTOR(INT, 8);
# DuckDB fixed-size arrays: FLOAT[1536], DOUBLE[3]; Databricks/Spark: ARRAY<FLOAT> (no dimensions)
_PGVECTOR = re.compile(r"^(vector|halfvec)\s*(?:\(\s*(\d+)\s*\))?$", re.I)
_SNOWFLAKE = re.compile(r"^vector\s*\(\s*(float|int)\s*,\s*(\d+)\s*\)$", re.I)
_FIXED_ARRAY = re.compile(r"^(float|real|double|float4|float8)\s*\[\s*(\d+)\s*\]$", re.I)


def is_vector(prop: SchemaProperty) -> bool:
    """True for ``logicalType: vector`` and for a native vector spelling in ``physicalType``."""
    if prop.logicalType and prop.logicalType.lower() == "vector":
        return True
    return parse_vector_type(prop.physicalType) is not None if prop.physicalType else False


def parse_vector_type(type_string: Optional[str]) -> Optional[tuple[Optional[int], str]]:
    """``(dimensions, elementType)`` for a native vector type string, or ``None`` if it is not one.

    Only spellings that mean "vector" on their platform count: a plain
    ``ARRAY<FLOAT>`` is an array, not a vector.
    """
    if not type_string:
        return None
    text = type_string.strip()
    match = _PGVECTOR.match(text)
    if match:
        element_type = "float16" if match.group(1).lower() == "halfvec" else DEFAULT_ELEMENT_TYPE
        return (int(match.group(2)) if match.group(2) else None), element_type
    match = _SNOWFLAKE.match(text)
    if match:
        return int(match.group(2)), ("int8" if match.group(1).lower() == "int" else DEFAULT_ELEMENT_TYPE)
    match = _FIXED_ARRAY.match(text)
    if match:
        element = match.group(1).lower()
        return int(match.group(2)), ("float64" if element in ("double", "float8") else DEFAULT_ELEMENT_TYPE)
    return None


def vector_dimensions(prop: SchemaProperty) -> Optional[int]:
    """The declared dimensions, from ``logicalTypeOptions`` or the native ``physicalType``."""
    options = prop.logicalTypeOptions or {}
    dimensions = options.get("dimensions")
    if dimensions is not None:
        try:
            return int(dimensions)
        except (TypeError, ValueError):
            return None
    parsed = parse_vector_type(prop.physicalType)
    return parsed[0] if parsed else None


def vector_element_type(prop: SchemaProperty) -> str:
    """The declared element type (``float32`` by default)."""
    options = prop.logicalTypeOptions or {}
    element_type = options.get("elementType")
    if element_type:
        return str(element_type).lower()
    parsed = parse_vector_type(prop.physicalType)
    return parsed[1] if parsed else DEFAULT_ELEMENT_TYPE


def is_double(prop: SchemaProperty) -> bool:
    """True when the elements need 64-bit floats."""
    return vector_element_type(prop) == "float64"
