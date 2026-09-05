"""The allowed values of a property, from whichever place a contract declares them.

ODCS v3.2.0 (RFC 0033) declares them as ``enum``, a list of objects with at
least a ``value``. Older contracts and some importers use three other
representations, which stay readable: ``logicalTypeOptions.enum`` (a plain
list), an ``enum`` custom property (a list or a JSON string, from DCS), and the
``invalidValues`` quality rule with ``validValues``.
"""

import json
from typing import Any, Optional

from open_data_contract_standard.model import EnumValue, SchemaProperty


def get_enum_entries(prop: SchemaProperty, include_quality_rule: bool = True) -> Optional[list[EnumValue]]:
    """The allowed values as ``EnumValue`` entries, or ``None`` if the property has none.

    Values from the legacy representations become entries with only a ``value``.
    """
    if prop.enum:
        return list(prop.enum)
    values = _legacy_enum_values(prop, include_quality_rule)
    if values is None:
        return None
    return [EnumValue(value=value) for value in values]


def get_enum_values(prop: SchemaProperty, include_quality_rule: bool = True) -> Optional[list[Any]]:
    """The allowed values as a plain list, or ``None`` if the property has none.

    ``enum`` wins, then ``logicalTypeOptions.enum``, the ``enum`` custom property,
    and the ``invalidValues`` quality rule. Callers that turn the quality rules
    into checks of their own pass ``include_quality_rule=False``, so the rule is
    not checked twice.
    """
    if prop.enum:
        return [entry.value for entry in prop.enum]
    return _legacy_enum_values(prop, include_quality_rule)


def _legacy_enum_values(prop: SchemaProperty, include_quality_rule: bool) -> Optional[list[Any]]:
    if prop.logicalTypeOptions and prop.logicalTypeOptions.get("enum"):
        return list(prop.logicalTypeOptions["enum"])
    for custom_property in prop.customProperties or []:
        if custom_property.property == "enum" and custom_property.value:
            if isinstance(custom_property.value, list):
                return list(custom_property.value)
            try:
                parsed = json.loads(custom_property.value)
            except (json.JSONDecodeError, TypeError):
                continue
            if isinstance(parsed, list):
                return parsed
    for quality in (prop.quality or []) if include_quality_rule else []:
        if quality.metric == "invalidValues" and quality.arguments:
            valid_values = quality.arguments.get("validValues")
            if valid_values:
                return list(valid_values)
    return None
