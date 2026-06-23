"""Type normalization and structural comparison for schema ``field_type`` checks.

``normalize_type_name`` maps a raw type string (logical or physical) to one of
the nine ODCS logical-type categories.

``schema_property_matches`` compares two ``SchemaProperty`` trees — one from the
contract, one reconstructed from the ibis-reported dtype — and returns True when
the actual type is structurally compatible with the expected one.
"""

from __future__ import annotations

import re

from open_data_contract_standard.model import SchemaProperty


def normalize_type_name(type_name: str | None) -> str | None:
    """Map a contract type name (logical or physical) to one of the 9 ODCS categories.

    Returns ``None`` for types that are unsupported or unrecognized (binary,
    map, null, interval …) so they can be silently ignored rather than
    producing false type-check failures.
    """
    if not type_name:
        return None
    name = type_name.strip().lower()
    # strip parameters like varchar(10) / decimal(10,2) and array<...> wrappers
    name = re.sub(r"\(.*\)", "", name)
    name = re.sub(r"<.*>", "", name).strip()

    if name in {
        "varchar",
        "varchar2",
        "char",
        "character",
        "character varying",
        "nvarchar",
        "nvarchar2",
        "nchar",
        "text",
        "string",
        "str",
        "clob",
        "nclob",
        "uuid",
        "enum",
    }:
        return "string"
    if name in {
        "int",
        "integer",
        "bigint",
        "smallint",
        "tinyint",
        "long",
        "short",
        "int2",
        "int4",
        "int8",
        "serial",
        "bigserial",
        "smallserial",
        "int64",
        "int32",
        "int16",
        "int8",
        "byteint",
    }:
        return "integer"
    if name in {
        "decimal",
        "numeric",
        "dec",
        "float",
        "double",
        "double precision",
        "real",
        "float4",
        "float8",
        "float32",
        "float64",
        "binary_float",
        "binary_double",
        "number",
    }:
        return "number"
    if name in {"bool", "boolean", "bit", "logical"}:
        return "boolean"
    if name in {
        "timestamp",
        "timestamptz",
        "timestamp without time zone",
        "timestamp with time zone",
        "timestamp_tz",
        "timestamp_ntz",
        "timestamp_ltz",
        "datetime",
        "datetime2",
        "smalldatetime",
    }:
        return "timestamp"
    if name in {"date"}:
        return "date"
    if name in {"time", "time without time zone", "time with time zone"}:
        return "time"
    if name in {"struct", "record", "object", "row", "json", "jsonb", "variant"}:
        return "object"
    if name in {"array", "list"}:
        return "array"
    # binary, map, null, interval and other unrecognized types are not in the
    # 9 allowed categories; return None so they are silently ignored.
    return None


_NUMERIC = {"integer", "number"}


def schema_property_matches(expected: SchemaProperty | None, actual: SchemaProperty | None) -> bool:
    """Return True if ``actual`` is structurally compatible with ``expected``.

    Lenient by design:

    - If expected is ``None`` (unsupported/unrecognized type) always passes.
    - ``integer`` and ``number`` are mutually compatible (ODCS "number" is
      intentionally ambiguous across numeric storage classes).
    - A bare ``object`` or ``array`` on the expected side (no nested detail)
      matches any actual structure with the same base (underdeclared contract).
    - Extra actual fields inside an ``object`` are ignored.
    """
    if expected is None:
        return True
    if actual is None:
        return False

    expected_base = normalize_type_name(expected.logicalType or expected.physicalType)
    actual_base = normalize_type_name(actual.logicalType or actual.physicalType)

    if expected_base is None:
        return True
    if actual_base is None:
        return False
    if expected_base != actual_base and not (expected_base in _NUMERIC and actual_base in _NUMERIC):
        return False

    if expected_base == "array":
        if expected.items is None:
            return True
        return schema_property_matches(expected.items, actual.items)

    if expected_base == "object":
        if not expected.properties:
            return True
        actual_by_name = {p.name.lower(): p for p in (actual.properties or []) if p.name}
        for exp_field in expected.properties:
            if not exp_field.name:
                continue
            act_field = actual_by_name.get(exp_field.name.lower())
            if act_field is None:
                return False
            if not schema_property_matches(exp_field, act_field):
                return False
        return True

    return True


def schema_property_mismatch_reason(
    expected: SchemaProperty | None,
    actual: SchemaProperty | None,
    path: str = "",
) -> str:
    errors = schema_property_mismatch_reasons(expected, actual, path)
    num_errors = len(errors)
    print(f"==== {num_errors}")

    if num_errors == 0:
        return ""
    elif num_errors == 1:
        return errors[0]
    else:
        return f"{errors[0]} (and {num_errors - 1} other errors)"


def schema_property_mismatch_reasons(
    expected: SchemaProperty | None,
    actual: SchemaProperty | None,
    path: str = "",
) -> list[str]:
    errors: list[str] = []

    if expected is None:
        return errors

    field_label = f"field '{path}'" if path else "column"
    if actual is None:
        exp_str = expected.logicalType or expected.physicalType
        errors.append(
            f"{field_label}: expected type '{exp_str}' but the column type could not be determined"
        )
        return errors

    expected_base = normalize_type_name(expected.logicalType or expected.physicalType)
    actual_base = normalize_type_name(actual.logicalType or actual.physicalType)

    if expected_base is None:
        return errors

    if expected_base != actual_base and not (expected_base in _NUMERIC and actual_base in _NUMERIC):
        exp_str = expected.logicalType or expected.physicalType
        act_str = actual.logicalType or actual.physicalType
        errors.append(f"{field_label}: expected type '{exp_str}' but got '{act_str}'")
        return errors

    if expected_base == "array":
        if expected.items is not None:
            child_path = f"{path}[]" if path else "[]"
            errors.extend(
                schema_property_mismatch_reasons(expected.items, actual.items, child_path)
            )

    if expected_base == "object":
        if not expected.properties:
            return errors

        actual_by_name = {p.name.lower(): p for p in (actual.properties or []) if p.name}
        for exp_field in expected.properties:
            if not exp_field.name:
                continue

            child_path = f"{path}.{exp_field.name}" if path else exp_field.name
            act_field = actual_by_name.get(exp_field.name.lower())

            if act_field is None:
                errors.append(f"field '{child_path}' is missing")
                continue

            errors.extend(
                schema_property_mismatch_reasons(exp_field, act_field, child_path)
            )

    return errors
