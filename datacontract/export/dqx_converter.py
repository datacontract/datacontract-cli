from typing import Any, Dict, List, Union

import yaml

from datacontract.export.exporter import Exporter, _check_models_for_export
from datacontract.model.data_contract_specification import DataContractSpecification, Field, Model, Quality


class DqxKeys:
    CHECK = "check"
    ARGUMENTS = "arguments"
    SPECIFICATION = "specification"
    COL_NAME = "column"
    COL_NAMES = "for_each_column"
    COLUMNS = "columns"
    FUNCTION = "function"


class DqxExporter(Exporter):
    """Exporter implementation for converting data contracts to DQX YAML file."""

    def export(
        self,
        data_contract: DataContractSpecification,
        model: Model,
        server: str,
        sql_server_type: str,
        export_args: Dict[str, Any],
    ) -> str:
        """Exports a data contract to DQX format."""
        model_name, model_value = _check_models_for_export(data_contract, model, self.export_format)
        return to_dqx_yaml(model_value)


def to_dqx_yaml(model_value: Model) -> str:
    """
    Converts the data contract's quality checks to DQX YAML format.

    Args:
        model_value (Model): The data contract to convert.

    Returns:
        str: YAML representation of the data contract's quality checks.
    """
    extracted_rules = extract_quality_rules(model_value)
    return yaml.dump(extracted_rules, sort_keys=False, allow_unicode=True, default_flow_style=False)


def process_quality_rule(rule: Quality, column_name: str) -> Dict[str, Any]:
    """
    Processes a single quality rule by injecting the column path into its arguments if absent.

    Args:
        rule (Quality): The quality rule to process.
        column_name (str): The full path to the current column.

    Returns:
        dict: The processed quality rule specification.
    """
    rule_data = rule.model_extra
    specification = rule_data[DqxKeys.SPECIFICATION]
    check = specification[DqxKeys.CHECK]

    arguments = check.setdefault(DqxKeys.ARGUMENTS, {})

    if DqxKeys.COL_NAME not in arguments and DqxKeys.COL_NAMES not in arguments and DqxKeys.COLUMNS not in arguments:
        if check[DqxKeys.FUNCTION] not in ("is_unique", "foreign_key"):
            arguments[DqxKeys.COL_NAME] = column_name
        else:
            arguments[DqxKeys.COLUMNS] = [column_name]

    return specification


def extract_quality_rules(data: Union[Model, Field, Quality], column_path: str = "") -> List[Dict[str, Any]]:
    """
    Recursively extracts all quality rules from a data contract structure.

    Args:
        data (Union[Model, Field, Quality]): The data contract model, field, or quality rule.
        column_path (str, optional): The current path in the schema hierarchy. Defaults to "".

    Returns:
        List[Dict[str, Any]]: A list of quality rule specifications.
    """
    quality_rules = []

    if isinstance(data, Quality):
        return [process_quality_rule(data, column_path)]

    if isinstance(data, (Model, Field)):
        for key, field in data.fields.items():
            current_path = build_column_path(column_path, key)

            if field.fields:
                # Field is a struct-like object, recurse deeper
                quality_rules.extend(extract_quality_rules(field, current_path))
            else:
                # Process quality rules at leaf fields
                for rule in field.quality:
                    quality_rules.append(process_quality_rule(rule, current_path))

        # Process any quality rules attached directly to this level
        for rule in data.quality:
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
