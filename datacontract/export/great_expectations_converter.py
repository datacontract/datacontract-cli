import json
from typing import Dict, List, Any

import yaml

from datacontract.model.data_contract_specification import DataContractSpecification, Field, Quality
from datacontract.export.exporter import Exporter, _check_models_for_export


class GreateExpectationsExporter(Exporter):
    def export(self, data_contract, model, server, sql_server_type, export_args) -> dict:
        model_name, model_value = _check_models_for_export(data_contract, model, self.export_format)
        return to_great_expectations(
            data_contract,
            model_name,
        )


def to_great_expectations(data_contract_spec: DataContractSpecification, model_key: str) -> str:
    """
    Convert each model in the contract to a Great Expectation suite
    @param data_contract_spec: data contract to export to great expectations
    @param model_key: model to great expectations to
    @return: a dictionary of great expectation suites
    """
    expectations = []
    model_value = data_contract_spec.models.get(model_key)
    quality_checks = get_quality_checks(data_contract_spec.quality)
    expectations.extend(model_to_expectations(model_value.fields))
    expectations.extend(checks_to_expectations(quality_checks, model_key))
    model_expectation_suite = to_suite(model_key, data_contract_spec.info.version, expectations)

    return model_expectation_suite


def to_suite(
    model_key: str,
    contract_version: str,
    expectations: List[Dict[str, Any]],
) -> str:
    return json.dumps(
        {
            "data_asset_type": "null",
            "expectation_suite_name": "user-defined.{model_key}.{contract_version}".format(
                model_key=model_key, contract_version=contract_version
            ),
            "expectations": expectations,
            "meta": {},
        },
        indent=2,
    )


def model_to_expectations(fields: Dict[str, Field]) -> List[Dict[str, Any]]:
    """
    Convert the model information to expectations
    @param fields: model field
    @return: list of expectations
    """
    expectations = []
    add_column_order_exp(fields, expectations)
    for field_name, field in fields.items():
        add_field_expectations(field_name, field, expectations)
    return expectations


def add_field_expectations(field_name, field: Field, expectations: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if field.type is not None:
        expectations.append(to_column_types_exp(field_name, field.type))
    if field.unique:
        expectations.append(to_column_unique_exp(field_name))
    if field.maxLength is not None or field.minLength is not None:
        expectations.append(to_column_length_exp(field_name, field.minLength, field.maxLength))
    if field.minimum is not None or field.maximum is not None:
        expectations.append(to_column_min_max_exp(field_name, field.minimum, field.maximum))

    # TODO: all constraints
    return expectations


def add_column_order_exp(fields: Dict[str, Field], expectations: List[Dict[str, Any]]):
    expectations.append(
        {
            "expectation_type": "expect_table_columns_to_match_ordered_list",
            "kwargs": {"column_list": list(fields.keys())},
            "meta": {},
        }
    )


def to_column_types_exp(field_name, field_type) -> Dict[str, Any]:
    return {
        "expectation_type": "expect_column_values_to_be_of_type",
        "kwargs": {"column": field_name, "type_": field_type},
        "meta": {},
    }


def to_column_unique_exp(field_name) -> Dict[str, Any]:
    return {"expectation_type": "expect_column_values_to_be_unique", "kwargs": {"column": field_name}, "meta": {}}


def to_column_length_exp(field_name, min_length, max_length) -> Dict[str, Any]:
    return {
        "expectation_type": "expect_column_value_lengths_to_be_between",
        "kwargs": {"column": field_name, "min_value": min_length, "max_value": max_length},
        "meta": {},
    }


def to_column_min_max_exp(field_name, minimum, maximum) -> Dict[str, Any]:
    return {
        "expectation_type": "expect_column_values_to_be_between",
        "kwargs": {"column": field_name, "min_value": minimum, "max_value": maximum},
        "meta": {},
    }


def get_quality_checks(quality: Quality) -> Dict[str, Any]:
    if quality is None:
        return {}
    if quality.type is None:
        return {}
    if quality.type.lower() != "great-expectations":
        return {}
    if isinstance(quality.specification, str):
        quality_specification = yaml.safe_load(quality.specification)
    else:
        quality_specification = quality.specification
    return quality_specification


def checks_to_expectations(quality_checks: Dict[str, Any], model_key: str) -> List[Dict[str, Any]]:
    """
    Get the quality definition for each model to the model expectation list
    @param quality_checks: dictionary of quality checks by model
    @param model_key: id of the model
    @return: the list of expectations for that model
    """
    if quality_checks is None or model_key not in quality_checks:
        return []

    model_quality_checks = quality_checks[model_key]

    if model_quality_checks is None:
        return []

    if isinstance(model_quality_checks, str):
        expectation_list = json.loads(model_quality_checks)
        return expectation_list
