"""Pure helpers that map ODCS field/model attributes to dbt data_tests.

Shared between `datacontract export dbt` and (eventually) `datacontract dbt sync`
so the two paths cannot drift while both emit dbt tests.
"""

import json
from typing import Any, List, Optional

from open_data_contract_standard.model import SchemaProperty


def _get_custom_property_value(prop: SchemaProperty, key: str) -> Optional[str]:
    if prop.customProperties is None:
        return None
    for cp in prop.customProperties:
        if cp.property == key:
            return cp.value
    return None


def _get_logical_type_option(prop: SchemaProperty, key: str) -> Any:
    if prop.logicalTypeOptions is None:
        return None
    return prop.logicalTypeOptions.get(key)


def _get_enum_values(prop: SchemaProperty) -> Optional[list]:
    """Resolve enum values from logicalTypeOptions, customProperties, or quality.invalidValues."""

    # First check logicalTypeOptions
    enum_values = _get_logical_type_option(prop, "enum")
    if enum_values:
        return enum_values
    # Then check customProperties
    enum_str = _get_custom_property_value(prop, "enum")
    if enum_str:
        try:
            if isinstance(enum_str, list):
                return enum_str
            return json.loads(enum_str)
        except (json.JSONDecodeError, TypeError):
            pass
    # Finally check quality rules for invalidValues with validValues
    if prop.quality:
        for q in prop.quality:
            if q.metric == "invalidValues" and q.arguments:
                valid_values = q.arguments.get("validValues")
                if valid_values:
                    return valid_values
    return None


def get_table_name_and_column_name(references: str) -> tuple:
    parts = references.split(".")
    if len(parts) < 2:
        return None, parts[0]
    return parts[-2], parts[-1]


def field_to_data_tests(
    prop: SchemaProperty,
    *,
    is_primary_key: bool = False,
    is_single_pk: bool = False,
    supports_constraints: bool = False,
    source_name: Optional[str] = None,
) -> List[Any]:
    """Build the list of dbt data_tests for an ODCS property.

    When ``supports_constraints`` is True, the caller is expected to emit
    ``not_null`` / ``unique`` as dbt column ``constraints`` instead, so they
    are skipped here.
    """
    tests: List[Any] = []

    if not supports_constraints:
        if prop.required or is_primary_key:
            tests.append("not_null")
        if prop.unique or (is_primary_key and is_single_pk):
            tests.append("unique")

    enum_values = _get_enum_values(prop)
    if enum_values and len(enum_values) > 0:
        tests.append({"accepted_values": {"values": enum_values}})

    min_length = _get_logical_type_option(prop, "minLength")
    max_length = _get_logical_type_option(prop, "maxLength")
    if min_length is not None or max_length is not None:
        length_test = {}
        if min_length is not None:
            length_test["min_value"] = min_length
        if max_length is not None:
            length_test["max_value"] = max_length
        tests.append({"dbt_expectations.expect_column_value_lengths_to_be_between": length_test})

    pattern = _get_logical_type_option(prop, "pattern")
    if pattern is not None:
        tests.append({"dbt_expectations.expect_column_values_to_match_regex": {"regex": pattern}})

    minimum = _get_logical_type_option(prop, "minimum")
    maximum = _get_logical_type_option(prop, "maximum")
    exclusive_minimum = _get_logical_type_option(prop, "exclusiveMinimum")
    exclusive_maximum = _get_logical_type_option(prop, "exclusiveMaximum")

    if (minimum is not None or maximum is not None) and exclusive_minimum is None and exclusive_maximum is None:
        range_test = {}
        if minimum is not None:
            range_test["min_value"] = minimum
        if maximum is not None:
            range_test["max_value"] = maximum
        tests.append({"dbt_expectations.expect_column_values_to_be_between": range_test})
    elif (exclusive_minimum is not None or exclusive_maximum is not None) and minimum is None and maximum is None:
        range_test = {}
        if exclusive_minimum is not None:
            range_test["min_value"] = exclusive_minimum
        if exclusive_maximum is not None:
            range_test["max_value"] = exclusive_maximum
        range_test["strictly"] = True
        tests.append({"dbt_expectations.expect_column_values_to_be_between": range_test})
    else:
        if minimum is not None:
            tests.append({"dbt_expectations.expect_column_values_to_be_between": {"min_value": minimum}})
        if maximum is not None:
            tests.append({"dbt_expectations.expect_column_values_to_be_between": {"max_value": maximum}})
        if exclusive_minimum is not None:
            tests.append(
                {
                    "dbt_expectations.expect_column_values_to_be_between": {
                        "min_value": exclusive_minimum,
                        "strictly": True,
                    }
                }
            )
        if exclusive_maximum is not None:
            tests.append(
                {
                    "dbt_expectations.expect_column_values_to_be_between": {
                        "max_value": exclusive_maximum,
                        "strictly": True,
                    }
                }
            )

    references = None
    if prop.relationships:
        for rel in prop.relationships:
            if hasattr(rel, "to") and rel.to:
                references = rel.to
                break
    if references is not None:
        table_name, column_name = get_table_name_and_column_name(references)
        if table_name is not None and column_name is not None:
            tests.append(
                {
                    "relationships": {
                        "to": f"""source("{source_name}", "{table_name}")""",
                        "field": f"{column_name}",
                    }
                }
            )

    return tests
