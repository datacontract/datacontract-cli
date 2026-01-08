from typing import Any, Dict, List, Union

import yaml
from open_data_contract_standard.model import DataQuality, OpenDataContractStandard, SchemaObject, SchemaProperty

from datacontract.export.exporter import Exporter, _check_schema_name_for_export


class DqxKeys:
    CHECK = "check"
    ARGUMENTS = "arguments"
    COL_NAME = "column"
    COL_NAMES = "for_each_column"
    COLUMNS = "columns"
    FUNCTION = "function"


class DqxExporter(Exporter):
    """Exporter implementation for converting data contracts to DQX YAML file."""

    def export(
        self,
        data_contract: OpenDataContractStandard,
        schema_name: str,
        server: str,
        sql_server_type: str,
        export_args: Dict[str, Any],
    ) -> str:
        """Exports a data contract to DQX format."""
        model_name, model_value = _check_schema_name_for_export(data_contract, schema_name, self.export_format)
        return to_dqx_yaml(model_value)


def to_dqx_yaml(model_value: SchemaObject) -> str:
    """
    Converts the data contract's quality checks to DQX YAML format.

    Args:
        model_value (SchemaObject): The schema object to convert.

    Returns:
        str: YAML representation of the data contract's quality checks.
    """
    extracted_rules = extract_quality_rules(model_value)
    return yaml.dump(extracted_rules, sort_keys=False, allow_unicode=True, default_flow_style=False)


def process_quality_rule(rule: DataQuality, column_name: str) -> Dict[str, Any]:
    """
    Processes a single quality rule by injecting the column path into its arguments if absent.

    Args:
        rule (DataQuality): The quality rule to process.
        column_name (str): The full path to the current column.

    Returns:
        dict: The processed quality rule specification.
    """
    implementation = rule.implementation
    check = implementation[DqxKeys.CHECK]

    if column_name:
        arguments = check.setdefault(DqxKeys.ARGUMENTS, {})

        if (
            DqxKeys.COL_NAME not in arguments
            and DqxKeys.COL_NAMES not in arguments
            and DqxKeys.COLUMNS not in arguments
        ):
            if check[DqxKeys.FUNCTION] not in ("is_unique", "foreign_key"):
                arguments[DqxKeys.COL_NAME] = column_name
            else:
                arguments[DqxKeys.COLUMNS] = [column_name]

    return implementation


def extract_quality_rules(data: Union[SchemaObject, SchemaProperty, DataQuality], column_path: str = "") -> List[Dict[str, Any]]:
    """
    Recursively extracts all quality rules from a data contract structure.

    Args:
        data (Union[SchemaObject, SchemaProperty, DataQuality]): The schema object, property, or quality rule.
        column_path (str, optional): The current path in the schema hierarchy. Defaults to "".

    Returns:
        List[Dict[str, Any]]: A list of quality rule specifications.
    """
    quality_rules = []

    if isinstance(data, DataQuality):
        return [process_quality_rule(data, column_path)]

    if isinstance(data, SchemaObject):
        # Process properties
        if data.properties:
            for prop in data.properties:
                current_path = build_column_path(column_path, prop.name)

                if prop.properties:
                    # Property is a struct-like object, recurse deeper
                    quality_rules.extend(extract_quality_rules_from_property(prop, current_path))
                else:
                    # Process quality rules at leaf properties
                    if prop.quality:
                        for rule in prop.quality:
                            quality_rules.append(process_quality_rule(rule, current_path))

        # Process any quality rules attached directly to the schema
        if data.quality:
            for rule in data.quality:
                quality_rules.append(process_quality_rule(rule, column_path))

    return quality_rules


def extract_quality_rules_from_property(prop: SchemaProperty, column_path: str) -> List[Dict[str, Any]]:
    """
    Recursively extracts quality rules from a property and its nested properties.

    Args:
        prop (SchemaProperty): The property to process.
        column_path (str): The current path in the schema hierarchy.

    Returns:
        List[Dict[str, Any]]: A list of quality rule specifications.
    """
    quality_rules = []

    # Process nested properties
    if prop.properties:
        for nested_prop in prop.properties:
            nested_path = build_column_path(column_path, nested_prop.name)

            if nested_prop.properties:
                # Recurse deeper
                quality_rules.extend(extract_quality_rules_from_property(nested_prop, nested_path))
            else:
                # Process quality rules at leaf properties
                if nested_prop.quality:
                    for rule in nested_prop.quality:
                        quality_rules.append(process_quality_rule(rule, nested_path))

    # Process quality rules at this property level
    if prop.quality:
        for rule in prop.quality:
            quality_rules.append(process_quality_rule(rule, column_path))

    return quality_rules


def build_column_path(current_path: str, key: str) -> str:
    """
    Builds the full column path by concatenating parent path with current key.

    Args:
        current_path (str): The current path prefix.
        key (str): The current field's key.

    Returns:
        str: The full path.
    """
    return f"{current_path}.{key}" if current_path else key
