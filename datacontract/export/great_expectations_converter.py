import json
from typing import Dict

import yaml

from datacontract.model.data_contract_specification import \
    DataContractSpecification, Field, Quality


def to_great_expectations(data_contract_spec: DataContractSpecification):
    great_expectation_jsons = {}
    expectations = []
    quality_checks = get_quality_checks(data_contract_spec.quality)
    for model_key, model_value in data_contract_spec.models.items():
        expectations.extend(model_to_expectations(model_value.fields))
        expectations.extend(checks_to_expectations(quality_checks, model_key))
        great_expectation_json = to_suite(model_key, expectations)
        great_expectation_jsons[model_key] = great_expectation_json

    return great_expectation_jsons


def to_suite(model_key: str, expectations: [], ) -> dict:
    return {
        "data_asset_type": "null",
        "expectation_suite_name": "user-defined." + model_key,
        "expectations": expectations,
        "meta": {
            "great_expectations_version": "0.17.23"
        }
    }


def model_to_expectations(fields: Dict[str, Field]) -> list:
    expectations = []
    add_column_order_exp(fields, expectations)
    for field_name, field in fields.items():
        add_field_expectations(field_name, field, expectations)
    return expectations


def add_field_expectations(field_name, field: Field, expectations: []) -> dict:
    if field.type is not None:
        expectations.append(to_column_types_exp(field_name, field.type))
    if field.unique is not None:
        expectations.append(to_column_unique_exp(field_name))
    if field.maxLength is not None or field.minLength is not None:
        expectations.append(to_column_length_exp(field_name, field.minLength, field.maxLength))
    if field.minimum is not None or field.maximum is not None:
        expectations.append(to_column_min_max_exp(field_name, field.minimum, field.maximum))

    # TODO: all constraints
    return expectations


def add_column_order_exp(fields: Dict[str, Field], expectations: []):
    expectations.append({"expectation_type": "expect_table_columns_to_match_ordered_list",
                         "kwargs": {
                             "column_list": list(fields.keys())
                         },
                         "meta": {}
                         })


def to_column_types_exp(field_name, field_type) -> dict:
    return {
        "expectation_type": "expect_column_values_to_be_of_type",
        "kwargs": {
            "column": field_name,
            "type_": field_type
        },
        "meta": {}
    }


def to_column_unique_exp(field_name) -> dict:
    return {
        "expectation_type": "expect_column_values_to_be_unique",
        "kwargs": {
            "column": field_name
        },
        "meta": {}
    }


def to_column_length_exp(field_name, min_length, max_length) -> dict:
    return {
        "expectation_type": "expect_column_value_lengths_to_be_between",
        "kwargs": {
            "column": field_name,
            "min_value": min_length,
            "max_value": max_length
        },
        "meta": {}
    }


def to_column_min_max_exp(field_name, minimum, maximum) -> dict:
    return {
        "expectation_type": "expect_column_values_to_be_between",
        "kwargs": {
            "column": field_name,
            "min_value": minimum,
            "max_value": maximum
        },
        "meta": {}
    }


def get_quality_checks(quality: Quality) -> dict:
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


def checks_to_expectations(quality_checks: {}, model_key: str) -> []:
    if quality_checks is None or model_key not in quality_checks:
        return []

    model_quality_checks = quality_checks[model_key]

    if model_quality_checks is None:
        return []

    if isinstance(model_quality_checks, str):
        expectation_list = json.loads(model_quality_checks)
        return expectation_list
