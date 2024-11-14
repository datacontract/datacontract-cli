"""
This module provides functionalities to export data contracts to Great Expectations suites.
It includes definitions for exporting different types of data (pandas, Spark, SQL) into
Great Expectations expectations format.
"""

import json
from enum import Enum
from typing import Any, Dict, List

import yaml

from datacontract.export.exporter import (
    Exporter,
    _check_models_for_export,
)
from datacontract.export.pandas_type_converter import convert_to_pandas_type
from datacontract.export.spark_converter import to_spark_data_type
from datacontract.export.sql_type_converter import convert_to_sql_type
from datacontract.model.data_contract_specification import (
    DataContractSpecification,
    Field,
    Quality,
)


class GreatExpectationsEngine(Enum):
    """Enum to represent the type of data engine for expectations.

    Attributes:
        pandas (str): Represents the Pandas engine type.
        spark (str): Represents the Spark engine type.
        sql (str): Represents the SQL engine type.
    """

    pandas = "pandas"
    spark = "spark"
    sql = "sql"


class GreatExpectationsExporter(Exporter):
    """Exporter class to convert data contracts to Great Expectations suites.

    Methods:
        export: Converts a data contract model to a Great Expectations suite.

    """

    def export(self, data_contract, model, server, sql_server_type, export_args) -> dict:
        """Exports a data contract model to a Great Expectations suite.

        Args:
            data_contract (DataContractSpecification): The data contract specification.
            model (str): The model name to export.
            server (str): The server information.
            sql_server_type (str): Type of SQL server (e.g., "snowflake").
            export_args (dict): Additional arguments for export, such as "suite_name" and "engine".

        Returns:
            dict: A dictionary representation of the Great Expectations suite.
        """
        expectation_suite_name = export_args.get("suite_name")
        engine = export_args.get("engine")
        model_name, model_value = _check_models_for_export(data_contract, model, self.export_format)
        sql_server_type = "snowflake" if sql_server_type == "auto" else sql_server_type
        return to_great_expectations(data_contract, model_name, expectation_suite_name, engine, sql_server_type)


def to_great_expectations(
    data_contract_spec: DataContractSpecification,
    model_key: str,
    expectation_suite_name: str | None = None,
    engine: str | None = None,
    sql_server_type: str = "snowflake",
) -> str:
    """Converts a data contract model to a Great Expectations suite.

    Args:
        data_contract_spec (DataContractSpecification): The data contract specification.
        model_key (str): The model key.
        expectation_suite_name (str | None): Optional suite name for the expectations.
        engine (str | None): Optional engine type (e.g., "pandas", "spark").
        sql_server_type (str): The type of SQL server (default is "snowflake").

    Returns:
        str: JSON string of the Great Expectations suite.
    """
    expectations = []
    if not expectation_suite_name:
        expectation_suite_name = "{model_key}.{contract_version}".format(
            model_key=model_key, contract_version=data_contract_spec.info.version
        )
    model_value = data_contract_spec.models.get(model_key)
    quality_checks = get_quality_checks(data_contract_spec.quality)
    expectations.extend(model_to_expectations(model_value.fields, engine, sql_server_type))
    expectations.extend(checks_to_expectations(quality_checks, model_key))
    model_expectation_suite = to_suite(expectations, expectation_suite_name)

    return model_expectation_suite


def to_suite(expectations: List[Dict[str, Any]], expectation_suite_name: str) -> str:
    """Converts a list of expectations to a JSON-formatted suite.

    Args:
        expectations (List[Dict[str, Any]]): List of expectations.
        expectation_suite_name (str): Name of the expectation suite.

    Returns:
        str: JSON string of the expectation suite.
    """
    return json.dumps(
        {
            "data_asset_type": "null",
            "expectation_suite_name": expectation_suite_name,
            "expectations": expectations,
            "meta": {},
        },
        indent=2,
    )


def model_to_expectations(fields: Dict[str, Field], engine: str | None, sql_server_type: str) -> List[Dict[str, Any]]:
    """Converts model fields to a list of expectations.

    Args:
        fields (Dict[str, Field]): Dictionary of model fields.
        engine (str | None): Engine type (e.g., "pandas", "spark").
        sql_server_type (str): SQL server type.

    Returns:
        List[Dict[str, Any]]: List of expectations.
    """
    expectations = []
    add_column_order_exp(fields, expectations)
    for field_name, field in fields.items():
        add_field_expectations(field_name, field, expectations, engine, sql_server_type)
    return expectations


def add_field_expectations(
    field_name,
    field: Field,
    expectations: List[Dict[str, Any]],
    engine: str | None,
    sql_server_type: str,
) -> List[Dict[str, Any]]:
    """Adds expectations for a specific field based on its properties.

    Args:
        field_name (str): The name of the field.
        field (Field): The field object.
        expectations (List[Dict[str, Any]]): The expectations list to update.
        engine (str | None): Engine type (e.g., "pandas", "spark").
        sql_server_type (str): SQL server type.

    Returns:
        List[Dict[str, Any]]: Updated list of expectations.
    """
    if field.type is not None:
        if engine == GreatExpectationsEngine.spark.value:
            field_type = to_spark_data_type(field).__class__.__name__
        elif engine == GreatExpectationsEngine.pandas.value:
            field_type = convert_to_pandas_type(field)
        elif engine == GreatExpectationsEngine.sql.value:
            field_type = convert_to_sql_type(field, sql_server_type)
        else:
            field_type = field.type
        expectations.append(to_column_types_exp(field_name, field_type))
    if field.unique:
        expectations.append(to_column_unique_exp(field_name))
    if field.maxLength is not None or field.minLength is not None:
        expectations.append(to_column_length_exp(field_name, field.minLength, field.maxLength))
    if field.minimum is not None or field.maximum is not None:
        expectations.append(to_column_min_max_exp(field_name, field.minimum, field.maximum))

    return expectations


def add_column_order_exp(fields: Dict[str, Field], expectations: List[Dict[str, Any]]):
    """Adds expectation for column ordering.

    Args:
        fields (Dict[str, Field]): Dictionary of fields.
        expectations (List[Dict[str, Any]]): The expectations list to update.
    """
    expectations.append(
        {
            "expectation_type": "expect_table_columns_to_match_ordered_list",
            "kwargs": {"column_list": list(fields.keys())},
            "meta": {},
        }
    )


def to_column_types_exp(field_name, field_type) -> Dict[str, Any]:
    """Creates a column type expectation.

    Args:
        field_name (str): The name of the field.
        field_type (str): The type of the field.

    Returns:
        Dict[str, Any]: Column type expectation.
    """
    return {
        "expectation_type": "expect_column_values_to_be_of_type",
        "kwargs": {"column": field_name, "type_": field_type},
        "meta": {},
    }


def to_column_unique_exp(field_name) -> Dict[str, Any]:
    """Creates a column uniqueness expectation.

    Args:
        field_name (str): The name of the field.

    Returns:
        Dict[str, Any]: Column uniqueness expectation.
    """
    return {
        "expectation_type": "expect_column_values_to_be_unique",
        "kwargs": {"column": field_name},
        "meta": {},
    }


def to_column_length_exp(field_name, min_length, max_length) -> Dict[str, Any]:
    """Creates a column length expectation.

    Args:
        field_name (str): The name of the field.
        min_length (int | None): Minimum length.
        max_length (int | None): Maximum length.

    Returns:
        Dict[str, Any]: Column length expectation.
    """
    return {
        "expectation_type": "expect_column_value_lengths_to_be_between",
        "kwargs": {
            "column": field_name,
            "min_value": min_length,
            "max_value": max_length,
        },
        "meta": {},
    }


def to_column_min_max_exp(field_name, minimum, maximum) -> Dict[str, Any]:
    """Creates a column min-max value expectation.

    Args:
        field_name (str): The name of the field.
        minimum (float | None): Minimum value.
        maximum (float | None): Maximum value.

    Returns:
        Dict[str, Any]: Column min-max value expectation.
    """
    return {
        "expectation_type": "expect_column_values_to_be_between",
        "kwargs": {"column": field_name, "min_value": minimum, "max_value": maximum},
        "meta": {},
    }


def get_quality_checks(quality: Quality) -> Dict[str, Any]:
    """Retrieves quality checks defined in a data contract.

    Args:
        quality (Quality): Quality object from the data contract.

    Returns:
        Dict[str, Any]: Dictionary of quality checks.
    """
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
    """Converts quality checks to a list of expectations.

    Args:
        quality_checks (Dict[str, Any]): Dictionary of quality checks by model.
        model_key (str): The model key.

    Returns:
        List[Dict[str, Any]]: List of expectations for the model.
    """
    if quality_checks is None or model_key not in quality_checks:
        return []

    model_quality_checks = quality_checks[model_key]

    if model_quality_checks is None:
        return []

    if isinstance(model_quality_checks, str):
        expectation_list = json.loads(model_quality_checks)
        return expectation_list
    return []
