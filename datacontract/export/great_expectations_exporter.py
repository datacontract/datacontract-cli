"""
This module provides functionalities to export data contracts to Great Expectations suites.
It includes definitions for exporting different types of data (pandas, Spark, SQL) into
Great Expectations expectations format.
"""

import json
import re
from enum import Enum
from typing import Any, Dict, List, Optional

from open_data_contract_standard.model import DataQuality, OpenDataContractStandard, SchemaProperty

from datacontract.export.exporter import (
    Exporter,
    _check_schema_name_for_export,
)

# Pre-built regex patterns for common string formats (RFC-compliant simplified patterns)
_FORMAT_REGEX_MAP: Dict[str, str] = {
    "email": r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$",
    "uuid": r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$",
    "uri": r"^[a-zA-Z][a-zA-Z0-9+\-.]*:[^\s]*$",
    "url": r"^https?://[^\s/$.?#][^\s]*$",
    "hostname": r"^[a-zA-Z0-9]([a-zA-Z0-9\-]{0,61}[a-zA-Z0-9])?(\.[a-zA-Z]{2,})+$",
    "ipv4": r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$",
    "ipv6": r"^([0-9a-fA-F]{0,4}:){2,7}[0-9a-fA-F]{0,4}$",
}

# Fields excluded when extracting quality block metadata into the GE meta dict
_QUALITY_META_EXCLUDED_FIELDS = {"type", "engine", "implementation"}


class GreatExpectationsEngine(str, Enum):
    pandas = "pandas"
    spark = "spark"
    sql = "sql"


class GreatExpectationsExporter(Exporter):
    def export(self, data_contract, schema_name, server, sql_server_type, export_args) -> str:
        expectation_suite_name = export_args.get("suite_name")
        engine = export_args.get("engine")
        schema_name, _ = _check_schema_name_for_export(data_contract, schema_name, self.export_format)
        sql_server_type = "snowflake" if sql_server_type == "auto" else sql_server_type
        return to_great_expectations(data_contract, schema_name, expectation_suite_name, engine, sql_server_type)


def _get_type(prop: SchemaProperty) -> Optional[str]:
    """Get the type from a schema property."""
    if prop.physicalType:
        return prop.physicalType
    if prop.logicalType:
        return prop.logicalType
    return None


def _get_logical_type_option(prop: SchemaProperty, key: str):
    """Get a logical type option value."""
    if prop.logicalTypeOptions is None:
        return None
    return prop.logicalTypeOptions.get(key)


def _get_enum_from_custom_properties(prop: SchemaProperty) -> Optional[List[str]]:
    """Get enum values from customProperties (used when importing from DCS)."""
    if prop.customProperties is None:
        return None
    for cp in prop.customProperties:
        if cp.property == "enum" and cp.value:
            if isinstance(cp.value, list):
                return cp.value
            return json.loads(cp.value)
    return None


def _get_format_regex(format_value: str) -> Optional[str]:
    """Return a regex string for common string format names, or None if unsupported."""
    return _FORMAT_REGEX_MAP.get(format_value.lower())


def _to_snake_case(text: str) -> str:
    """Convert a string to snake_case: lowercase, all non-alphanumeric chars → underscore, collapse multiples."""
    result = re.sub(r"[^a-z0-9_]", "_", text.strip().lower())
    return re.sub(r"_+", "_", result).strip("_")


def _display_name(prop: SchemaProperty, field_name: str) -> str:
    """Return businessName when set (and not 'NoBV'), else the column name, for use in human-readable meta.

    'NoBV' is a placeholder for 'No Business Value' and is ignored in favor of the column name.
    """
    if prop.businessName and prop.businessName.lower() != "nobv":
        return prop.businessName
    return field_name


def _build_expectation_id(contract_id: str, column_name: Optional[str], rule_name: str) -> str:
    """Build a unique expectation ID from contract ID, optional column name, and rule name."""
    if column_name:
        return f"{contract_id}.{column_name}.{rule_name}"
    return f"{contract_id}.{rule_name}"


def _build_constraint_meta(
    contract_id: str,
    column_name: str,
    rule_name: str,  # kept for caller clarity; expectation_id is derived from name instead
    name: str,
    description: str,
    dimension: str,
) -> Dict[str, Any]:
    """Build the meta dict for auto-generated constraint expectations (primaryKey, required, unique, logicalTypeOptions)."""
    return {
        "expectation_id": _build_expectation_id(contract_id, column_name, _to_snake_case(name)),
        "rule_location": "quality_column",
        "name": name,
        "description": description,
        "dimension": dimension,
    }


def _extract_quality_meta(
    quality: DataQuality,
    contract_id: str,
    column_name: Optional[str],
) -> Dict[str, Any]:
    """Extract and enrich meta from a quality block for the GE expectation meta field."""
    # Use name field first (more stable), fall back to description, then generic default
    rule_name_raw = getattr(quality, "name", None) or quality.description or "quality_rule"
    rule_name = _to_snake_case(rule_name_raw)
    rule_location = "quality_column" if column_name else "quality_table"

    meta: Dict[str, Any] = {
        "expectation_id": _build_expectation_id(contract_id, column_name, rule_name),
        "rule_location": rule_location,
    }

    # Extract all quality fields except excluded ones (type, engine, implementation)
    try:
        quality_dict = quality.model_dump(exclude_none=True)
    except AttributeError:
        quality_dict = quality.dict(exclude_none=True)

    for key, value in quality_dict.items():
        if key in _QUALITY_META_EXCLUDED_FIELDS:
            continue
        if key == "customProperties" and isinstance(value, list):
            # Flatten property/value pairs directly into meta
            for cp in value:
                prop_key = cp.get("property") if isinstance(cp, dict) else getattr(cp, "property", None)
                prop_val = cp.get("value") if isinstance(cp, dict) else getattr(cp, "value", None)
                if prop_key:
                    meta[prop_key] = prop_val
        else:
            meta[key] = value

    # Merge any extra meta defined inside implementation.meta (notes, etc.)
    impl = quality.implementation or {}
    impl_meta = impl.get("meta", {}) if isinstance(impl, dict) else {}
    for k, v in (impl_meta or {}).items():
        if k not in meta:
            meta[k] = v

    return meta


def to_great_expectations(
    odcs: OpenDataContractStandard,
    schema_name: str,
    expectation_suite_name: str | None = None,
    engine: str | None = None,
    sql_server_type: str = "snowflake",
) -> str:
    """Converts a data contract model to a Great Expectations suite.

    Args:
        odcs (OpenDataContractStandard): The data contract.
        schema_name (str): The schema/model name to export.
        expectation_suite_name (str | None): Optional suite name for the expectations.
        engine (str | None): Optional engine type (e.g., "pandas", "spark").
        sql_server_type (str): The type of SQL server (default is "snowflake").

    Returns:
        str: JSON string of the Great Expectations suite.
    """
    schema = next((s for s in odcs.schema_ if s.name == schema_name), None)
    if schema is None:
        raise RuntimeError(f"Schema '{schema_name}' not found in data contract.")

    contract_id = odcs.id or ""
    expectations = []
    if not expectation_suite_name:
        expectation_suite_name = "{schema_name}.{contract_version}".format(
            schema_name=schema_name, contract_version=odcs.version
        )

    if schema.quality:
        expectations.extend(get_quality_checks(schema.quality, None, contract_id))

    expectations.extend(model_to_expectations(schema.properties or [], engine, sql_server_type, contract_id))

    return to_suite(expectations, expectation_suite_name)


def to_suite(expectations: List[Dict[str, Any]], expectation_suite_name: str) -> str:
    return json.dumps(
        {
            "name": expectation_suite_name,
            "expectations": expectations,
            "meta": {},
        },
        indent=2,
    )


def model_to_expectations(
    properties: List[SchemaProperty],
    engine: str | None,
    sql_server_type: str,
    contract_id: str = "",
) -> List[Dict[str, Any]]:
    expectations = []
    for prop in properties:
        add_field_expectations(prop.name, prop, expectations, engine, sql_server_type, contract_id)
        if prop.quality:
            expectations.extend(get_quality_checks(prop.quality, prop.name, contract_id))
    return expectations


def add_field_expectations(
    field_name: str,
    prop: SchemaProperty,
    expectations: List[Dict[str, Any]],
    engine: str | None,
    sql_server_type: str,
    contract_id: str = "",
) -> List[Dict[str, Any]]:
    dn = _display_name(prop, field_name)
    prop_type = _get_type(prop)
    if prop_type is not None:
        if engine == GreatExpectationsEngine.spark.value:
            from datacontract.export.spark_exporter import to_spark_data_type

            field_type = to_spark_data_type(prop).name
        elif engine == GreatExpectationsEngine.pandas.value:
            from datacontract.export.pandas_type_converter import convert_to_pandas_type

            field_type = convert_to_pandas_type(prop)
        elif engine == GreatExpectationsEngine.sql.value:
            from datacontract.export.sql_type_converter import convert_to_sql_type

            field_type = convert_to_sql_type(prop, sql_server_type)
        else:
            field_type = prop_type
        expectations.append(
            to_column_types_exp(
                field_name,
                field_type,
                _build_constraint_meta(
                    contract_id,
                    field_name,
                    "column_type",
                    f"{dn} must be of type {field_type}",
                    f"{dn} must be of type {field_type}",
                    "conformity",
                ),
            )
        )

    # primaryKey: true → NOT_NULL + UNIQUE; required/unique standalone rules are skipped
    if prop.primaryKey:
        expectations.append(
            to_column_not_null_exp(
                field_name,
                _build_constraint_meta(
                    contract_id,
                    field_name,
                    "primary_key_not_null",
                    f"{dn} must be filled (primary key)",
                    f"{dn} is a primary key and must not contain null values",
                    "completeness",
                ),
            )
        )
        expectations.append(
            to_column_unique_exp(
                field_name,
                _build_constraint_meta(
                    contract_id,
                    field_name,
                    "primary_key_unique",
                    f"{dn} must be unique (primary key)",
                    f"{dn} is a primary key and must contain unique values",
                    "uniqueness",
                ),
            )
        )

    # required: true → NOT_NULL (skipped when primaryKey already covers it)
    if prop.required and not prop.primaryKey:
        expectations.append(
            to_column_not_null_exp(
                field_name,
                _build_constraint_meta(
                    contract_id,
                    field_name,
                    "not_null",
                    f"{dn} must be filled",
                    f"{dn} must be not null values",
                    "completeness",
                ),
            )
        )

    # unique: true → UNIQUE (skipped when primaryKey already covers it)
    if prop.unique and not prop.primaryKey:
        expectations.append(
            to_column_unique_exp(
                field_name,
                _build_constraint_meta(
                    contract_id,
                    field_name,
                    "unique",
                    f"{dn} must be unique",
                    f"{dn} must contain unique values",
                    "uniqueness",
                ),
            )
        )

    # logicalTypeOptions: minLength / maxLength
    min_length = _get_logical_type_option(prop, "minLength")
    max_length = _get_logical_type_option(prop, "maxLength")
    if min_length is not None or max_length is not None:
        if min_length is not None and max_length is not None:
            rule_name = "length_range"
            rule_name_label = f"{dn} length must be between {min_length} and {max_length}"
        elif min_length is not None:
            rule_name = "min_length"
            rule_name_label = f"{dn} length must be at least {min_length}"
        else:
            rule_name = "max_length"
            rule_name_label = f"{dn} length must be at most {max_length}"
        expectations.append(
            to_column_length_exp(
                field_name,
                min_length,
                max_length,
                _build_constraint_meta(
                    contract_id, field_name, rule_name, rule_name_label, rule_name_label, "conformity"
                ),
            )
        )

    # logicalTypeOptions: minimum / maximum (numeric or date)
    minimum = _get_logical_type_option(prop, "minimum")
    maximum = _get_logical_type_option(prop, "maximum")
    if minimum is not None or maximum is not None:
        if minimum is not None and maximum is not None:
            rule_name = "value_range"
            rule_name_label = f"{dn} must be between {minimum} and {maximum}"
        elif minimum is not None:
            rule_name = "minimum"
            rule_name_label = f"{dn} must be at least {minimum}"
        else:
            rule_name = "maximum"
            rule_name_label = f"{dn} must be at most {maximum}"
        expectations.append(
            to_column_min_max_exp(
                field_name,
                minimum,
                maximum,
                _build_constraint_meta(
                    contract_id,
                    field_name,
                    rule_name,
                    rule_name_label,
                    f"{dn} value must be between {minimum} and {maximum}"
                    if rule_name == "value_range"
                    else rule_name_label,
                    "conformity",
                ),
            )
        )

    # logicalTypeOptions: exclusiveMinimum / exclusiveMaximum
    exclusive_min = _get_logical_type_option(prop, "exclusiveMinimum")
    if exclusive_min is not None:
        meta = _build_constraint_meta(
            contract_id,
            field_name,
            "exclusive_min",
            f"{dn} must be strictly greater than {exclusive_min}",
            f"{dn} value must be strictly greater than {exclusive_min}",
            "conformity",
        )
        meta["exclusive"] = True
        expectations.append(to_column_min_max_exp(field_name, exclusive_min, None, meta))

    exclusive_max = _get_logical_type_option(prop, "exclusiveMaximum")
    if exclusive_max is not None:
        meta = _build_constraint_meta(
            contract_id,
            field_name,
            "exclusive_max",
            f"{dn} must be strictly less than {exclusive_max}",
            f"{dn} value must be strictly less than {exclusive_max}",
            "conformity",
        )
        meta["exclusive"] = True
        expectations.append(to_column_min_max_exp(field_name, None, exclusive_max, meta))

    # logicalTypeOptions: pattern (regex validation)
    pattern = _get_logical_type_option(prop, "pattern")
    if pattern is not None:
        expectations.append(
            to_column_regex_exp(
                field_name,
                pattern,
                _build_constraint_meta(
                    contract_id,
                    field_name,
                    "pattern_match",
                    f"{dn} must match pattern {pattern}",
                    f"{dn} values must match the pattern {pattern}",
                    "conformity",
                ),
            )
        )

    # logicalTypeOptions: format (maps to known regex patterns for common string formats)
    format_val = _get_logical_type_option(prop, "format")
    if format_val is not None:
        regex = _get_format_regex(format_val)
        if regex:
            expectations.append(
                to_column_regex_exp(
                    field_name,
                    regex,
                    _build_constraint_meta(
                        contract_id,
                        field_name,
                        "format_check",
                        f"{dn} must be a valid {format_val}",
                        f"{dn} values must be in {format_val} format",
                        "conformity",
                    ),
                )
            )

    # logicalTypeOptions: enum (from logicalTypeOptions or customProperties)
    enum_values = _get_logical_type_option(prop, "enum") or _get_enum_from_custom_properties(prop)
    if enum_values is not None and len(enum_values) != 0:
        expectations.append(
            to_column_enum_exp(
                field_name,
                enum_values,
                _build_constraint_meta(
                    contract_id,
                    field_name,
                    "enum_values",
                    f"{dn} must belong to allowed values",
                    f"{dn} must be in the set of allowed values",
                    "conformity",
                ),
            )
        )

    return expectations


def add_column_order_exp(properties: List[SchemaProperty], expectations: List[Dict[str, Any]]):
    column_names = [prop.name for prop in properties]
    expectations.append(
        {
            "type": "expect_table_columns_to_match_ordered_list",
            "kwargs": {"column_list": column_names},
            "meta": {},
        }
    )


def to_column_types_exp(field_name, field_type, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "type": "expect_column_values_to_be_of_type",
        "kwargs": {"column": field_name, "type_": field_type},
        "meta": meta or {},
    }


def to_column_not_null_exp(field_name: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "type": "expect_column_values_to_not_be_null",
        "kwargs": {"column": field_name},
        "meta": meta or {},
    }


def to_column_unique_exp(field_name: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    return {
        "type": "expect_column_values_to_be_unique",
        "kwargs": {"column": field_name},
        "meta": meta or {},
    }


def to_column_length_exp(
    field_name: str,
    min_length: Optional[int],
    max_length: Optional[int],
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {"column": field_name}
    if min_length is not None:
        kwargs["min_value"] = min_length
    if max_length is not None:
        kwargs["max_value"] = max_length
    return {
        "type": "expect_column_value_lengths_to_be_between",
        "kwargs": kwargs,
        "meta": meta or {},
    }


def to_column_min_max_exp(
    field_name: str,
    minimum,
    maximum,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    kwargs: Dict[str, Any] = {"column": field_name}
    if minimum is not None:
        kwargs["min_value"] = minimum
    if maximum is not None:
        kwargs["max_value"] = maximum
    return {
        "type": "expect_column_values_to_be_between",
        "kwargs": kwargs,
        "meta": meta or {},
    }


def to_column_enum_exp(
    field_name: str,
    enum_list: List[str],
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "type": "expect_column_values_to_be_in_set",
        "kwargs": {"column": field_name, "value_set": enum_list},
        "meta": meta or {},
    }


def to_column_regex_exp(
    field_name: str,
    regex: str,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    return {
        "type": "expect_column_values_to_match_regex",
        "kwargs": {"column": field_name, "regex": regex},
        "meta": meta or {},
    }


def get_quality_checks(
    qualities: List[DataQuality],
    field_name: Optional[str] = None,
    contract_id: str = "",
) -> List[Dict[str, Any]]:
    """Retrieves quality checks defined in a data contract and enriches their meta.

    Fixes the column duplication bug: column is placed only in kwargs, never at the root level.

    Args:
        qualities (List[DataQuality]): List of quality objects from the model specification.
        field_name (str | None): Column name if the quality list is attached to a specific column.
        contract_id (str): The data contract ID, used to build expectation_id.

    Returns:
        List[Dict[str, Any]]: List of enriched expectation dicts.
    """
    quality_specification = []
    for quality in qualities:
        if (
            quality is not None
            and quality.engine is not None
            and quality.engine.lower() in ("great-expectations", "greatexpectations")
        ):
            impl = quality.implementation
            if not isinstance(impl, dict):
                continue

            kwargs = dict(impl.get("kwargs") or {})
            # Add column to kwargs (not root level) only when not already present
            if field_name is not None and "column" not in kwargs:
                kwargs["column"] = field_name

            expectation = {
                "type": impl.get("type"),
                "kwargs": kwargs,
                "meta": _extract_quality_meta(quality, contract_id, field_name),
            }
            quality_specification.append(expectation)
    return quality_specification
