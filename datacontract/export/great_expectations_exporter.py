"""
This module provides functionalities to export data contracts to Great Expectations suites.
It includes definitions for exporting different types of data (pandas, Spark, SQL) into
Great Expectations expectations format.
"""

import json
from enum import Enum
from typing import Any, Dict, List, Optional

from open_data_contract_standard.model import DataQuality, OpenDataContractStandard, SchemaProperty

from datacontract.export.exporter import (
    Exporter,
    _check_schema_name_for_export,
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

    def export(self, data_contract, schema_name, server, sql_server_type, export_args) -> str:
        """Exports a data contract model to a Great Expectations suite.

        Args:
            data_contract (OpenDataContractStandard): The data contract specification.
            model (str): The model name to export.
            server (str): The server information.
            sql_server_type (str): Type of SQL server (e.g., "snowflake").
            export_args (dict): Additional arguments for export, such as "suite_name" and "engine".

        Returns:
            str: JSON string of the Great Expectations suite.
        """
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
    # Find the schema by name
    schema = next((s for s in odcs.schema_ if s.name == schema_name), None)
    if schema is None:
        raise RuntimeError(f"Schema '{schema_name}' not found in data contract.")

    expectations = []
    if not expectation_suite_name:
        expectation_suite_name = "{schema_name}.{contract_version}".format(
            schema_name=schema_name, contract_version=odcs.version
        )

    # Get quality checks from schema-level quality
    if schema.quality:
        expectations.extend(get_quality_checks(schema.quality))

    # Get expectations from model fields
    expectations.extend(model_to_expectations(schema.properties or [], engine, sql_server_type))

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
            "name": expectation_suite_name,
            "expectations": expectations,
            "meta": {},
        },
        indent=2,
    )


def model_to_expectations(properties: List[SchemaProperty], engine: str | None, sql_server_type: str) -> List[Dict[str, Any]]:
    """Converts model properties to a list of expectations.

    Args:
        properties (List[SchemaProperty]): List of model properties.
        engine (str | None): Engine type (e.g., "pandas", "spark").
        sql_server_type (str): SQL server type.

    Returns:
        List[Dict[str, Any]]: List of expectations.
    """
    expectations = []
    add_column_order_exp(properties, expectations)
    for prop in properties:
        add_field_expectations(prop.name, prop, expectations, engine, sql_server_type)
        if prop.quality:
            expectations.extend(get_quality_checks(prop.quality, prop.name))
    return expectations


def add_field_expectations(
    field_name: str,
    prop: SchemaProperty,
    expectations: List[Dict[str, Any]],
    engine: str | None,
    sql_server_type: str,
) -> List[Dict[str, Any]]:
    """Adds expectations for a specific field based on its properties.

    Args:
        field_name (str): The name of the field.
        prop (SchemaProperty): The property object.
        expectations (List[Dict[str, Any]]): The expectations list to update.
        engine (str | None): Engine type (e.g., "pandas", "spark").
        sql_server_type (str): SQL server type.

    Returns:
        List[Dict[str, Any]]: Updated list of expectations.
    """
    prop_type = _get_type(prop)
    if prop_type is not None:
        if engine == GreatExpectationsEngine.spark.value:
            from datacontract.export.spark_exporter import to_spark_data_type

            field_type = to_spark_data_type(prop).__class__.__name__
        elif engine == GreatExpectationsEngine.pandas.value:
            from datacontract.export.pandas_type_converter import convert_to_pandas_type

            field_type = convert_to_pandas_type(prop)
        elif engine == GreatExpectationsEngine.sql.value:
            from datacontract.export.sql_type_converter import convert_to_sql_type

            field_type = convert_to_sql_type(prop, sql_server_type)
        else:
            field_type = prop_type
        expectations.append(to_column_types_exp(field_name, field_type))
    if prop.unique:
        expectations.append(to_column_unique_exp(field_name))

    min_length = _get_logical_type_option(prop, "minLength")
    max_length = _get_logical_type_option(prop, "maxLength")
    if min_length is not None or max_length is not None:
        expectations.append(to_column_length_exp(field_name, min_length, max_length))

    minimum = _get_logical_type_option(prop, "minimum")
    maximum = _get_logical_type_option(prop, "maximum")
    if minimum is not None or maximum is not None:
        expectations.append(to_column_min_max_exp(field_name, minimum, maximum))

    enum_values = _get_logical_type_option(prop, "enum") or _get_enum_from_custom_properties(prop)
    if enum_values is not None and len(enum_values) != 0:
        expectations.append(to_column_enum_exp(field_name, enum_values))

    return expectations


def add_column_order_exp(properties: List[SchemaProperty], expectations: List[Dict[str, Any]]):
    """Adds expectation for column ordering.

    Args:
        properties (List[SchemaProperty]): List of properties.
        expectations (List[Dict[str, Any]]): The expectations list to update.
    """
    column_names = [prop.name for prop in properties]
    expectations.append(
        {
            "type": "expect_table_columns_to_match_ordered_list",
            "kwargs": {"column_list": column_names},
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
        "type": "expect_column_values_to_be_of_type",
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
        "type": "expect_column_values_to_be_unique",
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
        "type": "expect_column_value_lengths_to_be_between",
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
        "type": "expect_column_values_to_be_between",
        "kwargs": {"column": field_name, "min_value": minimum, "max_value": maximum},
        "meta": {},
    }


def to_column_enum_exp(field_name, enum_list: List[str]) -> Dict[str, Any]:
    """Creates a expect_column_values_to_be_in_set expectation.

    Args:
        field_name (str): The name of the field.
        enum_list (Set[str]): enum list of value.

    Returns:
        Dict[str, Any]: Column value in set expectation.
    """
    return {
        "type": "expect_column_values_to_be_in_set",
        "kwargs": {"column": field_name, "value_set": enum_list},
        "meta": {},
    }


def get_quality_checks(qualities: List[DataQuality], field_name: str | None = None) -> List[Dict[str, Any]]:
    """Retrieves quality checks defined in a data contract.

    Args:
        qualities (List[DataQuality]): List of quality object from the model specification.
        field_name (str | None): field name if the quality list is attached to a specific field

    Returns:
        List[Dict[str, Any]]: List of quality check specifications.
    """
    quality_specification = []
    for quality in qualities:
        if quality is not None and quality.engine is not None and quality.engine.lower() in ("great-expectations", "greatexpectations"):
            ge_expectation = quality.implementation
            if field_name is not None and isinstance(ge_expectation, dict):
                ge_expectation["column"] = field_name
            quality_specification.append(ge_expectation)
    return quality_specification
