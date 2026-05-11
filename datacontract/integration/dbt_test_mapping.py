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


def get_logical_type_option(prop: SchemaProperty, key: str) -> Any:
    if prop.logicalTypeOptions is None:
        return None
    return prop.logicalTypeOptions.get(key)


def _get_enum_values(prop: SchemaProperty) -> Optional[list]:
    """Resolve enum values from logicalTypeOptions, customProperties, or quality.invalidValues."""

    # First check logicalTypeOptions
    enum_values = get_logical_type_option(prop, "enum")
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
