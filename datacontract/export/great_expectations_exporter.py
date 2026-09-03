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
    "ipv4": r"^((25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)\.){3}(25[0-5]|2[0-4][0-9]|[01]?[0-9][0-9]?)$",
}

# Only these DataQuality fields are surfaced in the GE meta dict (allowlist, not exclude-list)
_QUALITY_META_ALLOWED_FIELDS = {
    "id",
    "name",
    "description",
    "dimension",
    "severity",
    "businessImpact",
    "customProperties",
    "scheduler",
    "schedule",
    "tags",
    "authoritativeDefinitions",
}


class GreatExpectationsEngine(str, Enum):
    """Supported execution engines for Great Expectations suites."""

    pandas = "pandas"
    spark = "spark"
    sql = "sql"


class GreatExpectationsExporter(Exporter):
    def export(self, data_contract, schema_name, server, sql_server_type, export_args) -> str:
        """Export a data contract as a Great Expectations suite JSON string.

        Args:
            data_contract: Data contract to export.
            schema_name: Name of the contract schema to export.
            server: Server configuration. Unused by this exporter.
            sql_server_type: SQL dialect used when the selected engine is SQL.
            export_args: Export options, including optional ``suite_name`` and ``engine`` values.

        Returns:
            str: Serialized Great Expectations expectation suite.
        """
        expectation_suite_name = export_args.get("suite_name")
        engine = export_args.get("engine")
        schema_name, _ = _check_schema_name_for_export(data_contract, schema_name, self.export_format)
        sql_server_type = "snowflake" if sql_server_type == "auto" else sql_server_type
        return to_great_expectations(data_contract, schema_name, expectation_suite_name, engine, sql_server_type)


def _get_logical_type_option(prop: SchemaProperty, key: str):
    """Get a value from a property's logical type options.

    Args:
        prop: Schema property containing logical type options.
        key: Option name to retrieve.

    Returns:
        Any | None: The option value, or ``None`` when options or the key are absent.
    """
    if prop.logicalTypeOptions is None:
        return None
    return prop.logicalTypeOptions.get(key)


def _get_enum_from_custom_properties(prop: SchemaProperty) -> Optional[List[str]]:
    """Get enum values from custom properties used by DCS imports.

    Args:
        prop: Schema property whose custom properties are inspected.

    Returns:
        list[str] | None: Declared enum values, or ``None`` when no enum is present.
    """
    if prop.customProperties is None:
        return None
    for cp in prop.customProperties:
        if cp.property == "enum" and cp.value:
            if isinstance(cp.value, list):
                return cp.value
            return json.loads(cp.value)
    return None


def _to_snake_case(text: str) -> str:
    """Convert text to a normalized snake-case identifier.

    Args:
        text: Input text to normalize.

    Returns:
        str: Lowercase identifier with non-alphanumeric characters replaced by underscores.
    """
    normalized = text.strip().lower()
    result = re.sub(r"[^a-z0-9_]", "_", normalized)
    return re.sub(r"_+", "_", result).strip("_")


def _build_expectation_id(contract_id: str, column_name: Optional[str], rule_name: str) -> str:
    """Build an expectation ID from contract, column, and rule identifiers.

    Args:
        contract_id: Data contract identifier.
        column_name: Column name for a column-level expectation, if applicable.
        rule_name: Normalized quality rule name.

    Returns:
        str: Dot-separated expectation identifier.
    """
    if column_name:
        return f"{contract_id}.{column_name}.{rule_name}"
    return f"{contract_id}.{rule_name}"


def _build_constraint_meta(
    contract_id: str,
    column_name: str,
    name: str,
    description: str,
    dimension: str,
) -> Dict[str, Any]:
    """Build metadata for an automatically generated constraint expectation.

    Args:
        contract_id: Data contract identifier.
        column_name: Column constrained by the expectation.
        name: Human-readable expectation name.
        description: Human-readable expectation description.
        dimension: Data quality dimension represented by the constraint.

    Returns:
        dict[str, Any]: Great Expectations metadata, including its generated identifier.
    """
    return {
        "expectation_id": _build_expectation_id(contract_id, column_name, _to_snake_case(name)),
        "data_contract_rule_location": {"origin": "schema_inferred", "scope": "column"},
        "name": name,
        "description": description,
        "dimension": dimension,
    }


def _extract_quality_meta(
    quality: DataQuality,
    contract_id: str,
    column_name: Optional[str],
) -> Dict[str, Any]:
    """Extract and enrich metadata from a contract quality block.

    Args:
        quality: Quality rule containing the source metadata.
        contract_id: Data contract identifier used in the expectation ID.
        column_name: Column name for column-level rules, if applicable.

    Returns:
        dict[str, Any]: Metadata suitable for a Great Expectations expectation.
    """
    # Use name field first (more stable), fall back to description, then generic default
    rule_name_raw = getattr(quality, "name", None) or quality.description or "quality_rule"
    rule_name = _to_snake_case(rule_name_raw)
    scope = "column" if column_name else "table"

    meta: Dict[str, Any] = {
        "expectation_id": _build_expectation_id(contract_id, column_name, rule_name),
        "data_contract_rule_location": {"origin": "quality_block", "scope": scope},
    }

    # Only surface allowlisted DataQuality fields in meta
    quality_dict = quality.model_dump(exclude_none=True)

    for key, value in quality_dict.items():
        if key not in _QUALITY_META_ALLOWED_FIELDS:
            continue
        if key == "customProperties" and isinstance(value, list):
            custom_properties = {}
            for cp in value:
                prop_key = cp.get("property") if isinstance(cp, dict) else getattr(cp, "property", None)
                prop_val = cp.get("value") if isinstance(cp, dict) else getattr(cp, "value", None)
                if prop_key:
                    custom_properties[prop_key] = prop_val
            if custom_properties:
                meta["data_contract_custom_properties"] = custom_properties
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

    column_names = [prop.name for prop in schema.properties or []]
    if column_names:
        expectations.append(
            _build_exp(
                "expect_table_columns_to_match_set",
                {"column_set": column_names},
                f"{schema_name} must contain exactly the contracted columns",
                {
                    "expectation_id": _build_expectation_id(contract_id, None, "column_set"),
                    "data_contract_rule_location": {"origin": "schema_inferred", "scope": "table"},
                    "name": f"{schema_name} must contain exactly the contracted columns",
                    "dimension": "conformity",
                },
            )
        )

    if schema.quality:
        expectations.extend(get_quality_checks(schema.quality, None, contract_id))

    for prop in schema.properties or []:
        add_field_expectations(prop.name, prop, expectations, engine, sql_server_type, contract_id)
        if prop.quality:
            expectations.extend(get_quality_checks(prop.quality, prop.name, contract_id))

    return json.dumps(
        {
            "name": expectation_suite_name,
            "expectations": expectations,
            "meta": {
                "contract_id": contract_id,
                "contract_version": odcs.version or "",
            },
        },
        indent=2,
    )


def add_field_expectations(
    field_name: str,
    prop: SchemaProperty,
    expectations: List[Dict[str, Any]],
    engine: str | None,
    sql_server_type: str,
    contract_id: str = "",
) -> List[Dict[str, Any]]:
    """Append expectations derived from one field definition.

    Args:
        field_name: Technical name of the field.
        prop: Schema property defining the field constraints.
        expectations: Collection to which generated expectations are appended.
        engine: Optional Great Expectations execution engine.
        sql_server_type: SQL dialect used for SQL engine type conversion.
        contract_id: Data contract identifier used in expectation metadata.

    Returns:
        list[dict[str, Any]]: The provided collection after generated expectations are appended.
    """
    prop_type = prop.physicalType or prop.logicalType
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
                    f"{field_name} must be of type {field_type}",
                    f"{field_name} must be of type {field_type}",
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
                    f"{field_name} must be filled (primary key)",
                    f"{field_name} is a primary key and must not contain null values",
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
                    f"{field_name} must be unique (primary key)",
                    f"{field_name} is a primary key and must contain unique values",
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
                    f"{field_name} must be filled",
                    f"{field_name} must be not null values",
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
                    f"{field_name} must be unique",
                    f"{field_name} must contain unique values",
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
            rule_name_label = f"{field_name} length must be between {min_length} and {max_length}"
        elif min_length is not None:
            rule_name = "min_length"
            rule_name_label = f"{field_name} length must be at least {min_length}"
        else:
            rule_name = "max_length"
            rule_name_label = f"{field_name} length must be at most {max_length}"
        expectations.append(
            to_column_length_exp(
                field_name,
                min_length,
                max_length,
                _build_constraint_meta(contract_id, field_name, rule_name_label, rule_name_label, "conformity"),
            )
        )

    # logicalTypeOptions: minimum / maximum / exclusiveMinimum / exclusiveMaximum (numeric or date).
    # All four merge into one expectation: Great Expectations keeps only the last
    # expect_column_values_to_be_between per column, so emitting several drops constraints.
    minimum = _get_logical_type_option(prop, "minimum")
    maximum = _get_logical_type_option(prop, "maximum")
    exclusive_minimum = _get_logical_type_option(prop, "exclusiveMinimum")
    exclusive_maximum = _get_logical_type_option(prop, "exclusiveMaximum")

    strict_min = False
    if exclusive_minimum is not None and (minimum is None or exclusive_minimum >= minimum):
        minimum, strict_min = exclusive_minimum, True
    strict_max = False
    if exclusive_maximum is not None and (maximum is None or exclusive_maximum <= maximum):
        maximum, strict_max = exclusive_maximum, True

    if minimum is not None or maximum is not None:
        min_label = f"strictly greater than {minimum}" if strict_min else f"at least {minimum}"
        max_label = f"strictly less than {maximum}" if strict_max else f"at most {maximum}"
        if minimum is not None and maximum is not None:
            rule_name = "value_range"
            if not strict_min and not strict_max:
                rule_name_label = f"{field_name} must be between {minimum} and {maximum}"
            else:
                rule_name_label = f"{field_name} must be {min_label} and {max_label}"
        elif minimum is not None:
            rule_name = "exclusive_min" if strict_min else "minimum"
            rule_name_label = f"{field_name} must be {min_label}"
        else:
            rule_name = "exclusive_max" if strict_max else "maximum"
            rule_name_label = f"{field_name} must be {max_label}"
        meta = _build_constraint_meta(
            contract_id,
            field_name,
            rule_name_label,
            f"{field_name} value must be between {minimum} and {maximum}"
            if rule_name == "value_range" and not strict_min and not strict_max
            else rule_name_label.replace(f"{field_name} must be", f"{field_name} value must be", 1),
            "conformity",
        )
        if strict_min or strict_max:
            meta["exclusive"] = True
        expectations.append(
            to_column_min_max_exp(
                field_name,
                minimum,
                maximum,
                meta,
                strict_min=strict_min,
                strict_max=strict_max,
            )
        )

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
                    f"{field_name} must match pattern {pattern}",
                    f"{field_name} values must match the pattern {pattern}",
                    "conformity",
                ),
            )
        )

    # logicalTypeOptions: format (maps to known regex patterns for common string formats)
    format_val = _get_logical_type_option(prop, "format")
    if format_val is not None:
        regex = _FORMAT_REGEX_MAP.get(format_val.lower())
        if regex:
            expectations.append(
                to_column_regex_exp(
                    field_name,
                    regex,
                    _build_constraint_meta(
                        contract_id,
                        field_name,
                        f"{field_name} must be a valid {format_val}",
                        f"{field_name} values must be in {format_val} format",
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
                    f"{field_name} must belong to allowed values",
                    f"{field_name} must be in the set of allowed values",
                    "conformity",
                ),
            )
        )

    return expectations


def _pop_description(meta: Optional[Dict[str, Any]]) -> tuple[Optional[str], Dict[str, Any]]:
    """Extract description from meta, returning it separately alongside the remaining meta."""
    meta_copy = dict(meta or {})
    return meta_copy.pop("description", None), meta_copy


def _build_exp(type_: str, kwargs: Dict[str, Any], description: Optional[str], meta: Dict[str, Any]) -> Dict[str, Any]:
    """Assemble an expectation dict, placing description at root level when present."""
    exp: Dict[str, Any] = {"type": type_}
    if description is not None:
        exp["description"] = description
    exp["kwargs"] = kwargs
    exp["meta"] = meta
    return exp


def to_column_types_exp(field_name, field_type, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a column type expectation.

    Args:
        field_name: Column validated by the expectation.
        field_type: Expected Great Expectations-compatible column type.
        meta: Optional metadata to attach to the expectation.

    Returns:
        dict[str, Any]: Great Expectations column-type expectation.
    """
    description, meta_copy = _pop_description(meta)
    return _build_exp(
        "expect_column_values_to_be_of_type",
        {"column": field_name, "type_": field_type},
        description,
        meta_copy,
    )


def to_column_not_null_exp(field_name: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a column non-null expectation.

    Args:
        field_name: Column validated by the expectation.
        meta: Optional metadata to attach to the expectation.

    Returns:
        dict[str, Any]: Great Expectations non-null expectation.
    """
    description, meta_copy = _pop_description(meta)
    return _build_exp("expect_column_values_to_not_be_null", {"column": field_name}, description, meta_copy)


def to_column_unique_exp(field_name: str, meta: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    """Create a column uniqueness expectation.

    Args:
        field_name: Column validated by the expectation.
        meta: Optional metadata to attach to the expectation.

    Returns:
        dict[str, Any]: Great Expectations uniqueness expectation.
    """
    description, meta_copy = _pop_description(meta)
    return _build_exp("expect_column_values_to_be_unique", {"column": field_name}, description, meta_copy)


def to_column_length_exp(
    field_name: str,
    min_length: Optional[int],
    max_length: Optional[int],
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a column value-length range expectation.

    Args:
        field_name: Column validated by the expectation.
        min_length: Inclusive minimum permitted value length.
        max_length: Inclusive maximum permitted value length.
        meta: Optional metadata to attach to the expectation.

    Returns:
        dict[str, Any]: Great Expectations value-length expectation.
    """
    kwargs: Dict[str, Any] = {"column": field_name}
    if min_length is not None:
        kwargs["min_value"] = min_length
    if max_length is not None:
        kwargs["max_value"] = max_length
    description, meta_copy = _pop_description(meta)
    return _build_exp("expect_column_value_lengths_to_be_between", kwargs, description, meta_copy)


def to_column_min_max_exp(
    field_name: str,
    minimum,
    maximum,
    meta: Optional[Dict[str, Any]] = None,
    strict_min: bool = False,
    strict_max: bool = False,
) -> Dict[str, Any]:
    """Create a column value-range expectation.

    Args:
        field_name: Column validated by the expectation.
        minimum: Lower bound, when defined.
        maximum: Upper bound, when defined.
        meta: Optional metadata to attach to the expectation.
        strict_min: Whether the lower bound is exclusive.
        strict_max: Whether the upper bound is exclusive.

    Returns:
        dict[str, Any]: Great Expectations value-range expectation.
    """
    kwargs: Dict[str, Any] = {"column": field_name}
    if minimum is not None:
        kwargs["min_value"] = minimum
        if strict_min:
            kwargs["strict_min"] = True
    if maximum is not None:
        kwargs["max_value"] = maximum
        if strict_max:
            kwargs["strict_max"] = True
    description, meta_copy = _pop_description(meta)
    return _build_exp("expect_column_values_to_be_between", kwargs, description, meta_copy)


def to_column_enum_exp(
    field_name: str,
    enum_list: List[str],
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a column allowed-values expectation.

    Args:
        field_name: Column validated by the expectation.
        enum_list: Permitted values for the column.
        meta: Optional metadata to attach to the expectation.

    Returns:
        dict[str, Any]: Great Expectations set-membership expectation.
    """
    description, meta_copy = _pop_description(meta)
    return _build_exp(
        "expect_column_values_to_be_in_set",
        {"column": field_name, "value_set": enum_list},
        description,
        meta_copy,
    )


def to_column_regex_exp(
    field_name: str,
    regex: str,
    meta: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """Create a column regular-expression expectation.

    Args:
        field_name: Column validated by the expectation.
        regex: Regular expression each non-null value must match.
        meta: Optional metadata to attach to the expectation.

    Returns:
        dict[str, Any]: Great Expectations regular-expression expectation.
    """
    description, meta_copy = _pop_description(meta)
    return _build_exp(
        "expect_column_values_to_match_regex",
        {"column": field_name, "regex": regex},
        description,
        meta_copy,
    )


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
            if not isinstance(impl, dict) or not impl.get("type"):
                continue

            kwargs = dict(impl.get("kwargs") or {})
            # Add column to kwargs (not root level) only when not already present
            if field_name is not None and "column" not in kwargs:
                kwargs["column"] = field_name

            meta = _extract_quality_meta(quality, contract_id, field_name)
            description, meta_copy = _pop_description(meta)
            expectation = _build_exp(impl["type"], kwargs, description, meta_copy)
            quality_specification.append(expectation)
    return quality_specification
