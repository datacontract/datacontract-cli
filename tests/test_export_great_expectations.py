import json
from typing import Any, Dict

import pytest
from datacontract_specification.model import DataContractSpecification
from open_data_contract_standard.model import OpenDataContractStandard
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.export.great_expectations_exporter import to_great_expectations
from datacontract.imports.dcs_importer import convert_dcs_to_odcs
from datacontract.lint import resolve

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "./fixtures/export/datacontract.odcs.yaml",
            "--format",
            "great-expectations",
        ],
    )
    assert result.exit_code == 0


@pytest.fixture
def data_contract_basic() -> OpenDataContractStandard:
    return OpenDataContractStandard.from_file("fixtures/export/datacontract.odcs.yaml")


@pytest.fixture
def data_contract_complex() -> OpenDataContractStandard:
    dcs = DataContractSpecification.from_file("fixtures/export/rdf/datacontract-complex.yaml")
    return convert_dcs_to_odcs(dcs)


@pytest.fixture
def odcs() -> OpenDataContractStandard:
    return resolve.resolve_data_contract_from_location(
        "./fixtures/great-expectations/odcs.yaml"
    )


@pytest.fixture
def data_contract_great_expectations_quality_yaml() -> OpenDataContractStandard:
    return resolve.resolve_data_contract_from_location(
        "./fixtures/great-expectations/datacontract_quality_yaml.yaml",
    )


@pytest.fixture
def data_contract_great_expectations_quality_column() -> OpenDataContractStandard:
    return resolve.resolve_data_contract_from_location(
        "./fixtures/great-expectations/datacontract_quality_column.yaml",
    )


@pytest.fixture
def expected_json_suite() -> Dict[str, Any]:
    return {
        "name": "orders.1.0.0",
        "expectations": [
            {
                "type": "expect_table_row_count_to_be_between",
                "kwargs": {"min_value": 10},
                "meta": {},
            },
            {
                "type": "expect_table_columns_to_match_ordered_list",
                "kwargs": {"column_list": ["order_id", "processed_timestamp"]},
                "meta": {},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_id", "type_": "string"},
                "meta": {},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "processed_timestamp", "type_": "timestamp"},
                "meta": {},
            },
        ],
        "meta": {},
    }


@pytest.fixture
def expected_json_suite_table_quality() -> Dict[str, Any]:
    return {
        "name": "orders.1.0.0",
        "expectations": [
            {"type": "expect_table_row_count_to_be_between", "kwargs": {"min_value": 10}, "meta": {}},
            {
                "type": "expect_table_columns_to_match_ordered_list",
                "kwargs": {"column_list": ["order_id"]},
                "meta": {},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_id", "type_": "string"},
                "meta": {},
            },
        ],
        "meta": {},
    }


@pytest.fixture
def expected_json_suite_with_enum() -> Dict[str, Any]:
    return {
        "name": "orders.1.1.1",
        "expectations": [
            {
                "type": "expect_table_columns_to_match_ordered_list",
                "kwargs": {"column_list": ["id", "type"]},
                "meta": {},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "id", "type_": "string"},
                "meta": {},
            },
            {"type": "expect_column_values_to_be_unique", "kwargs": {"column": "id"}, "meta": {}},
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "type", "type_": "string"},
                "meta": {},
            },
            {
                "type": "expect_column_values_to_be_in_set",
                "kwargs": {"column": "type", "value_set": ["A", "B", "C", "D", "E"]},
                "meta": {},
            },
            {
                "type": "expect_column_value_lengths_to_equal",
                "kwargs": {"value": 1},
                "meta": {"notes": "Ensures that column length is 1."},
                "column": "type",
            },
        ],
        "meta": {},
    }


@pytest.fixture
def expected_spark_engine() -> Dict[str, Any]:
    return {
        "name": "orders.1.0.0",
        "expectations": [
            {
                "type": "expect_table_row_count_to_be_between",
                "kwargs": {"min_value": 10},
                "meta": {},
            },
            {
                "type": "expect_table_columns_to_match_ordered_list",
                "kwargs": {"column_list": ["order_id", "processed_timestamp"]},
                "meta": {},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_id", "type_": "StringType"},
                "meta": {},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "processed_timestamp", "type_": "TimestampType"},
                "meta": {},
            },
        ],
        "meta": {},
    }


@pytest.fixture
def expected_pandas_engine() -> Dict[str, Any]:
    return {
        "name": "orders.1.0.0",
        "expectations": [
            {
                "type": "expect_table_row_count_to_be_between",
                "kwargs": {"min_value": 10},
                "meta": {},
            },
            {
                "type": "expect_table_columns_to_match_ordered_list",
                "kwargs": {"column_list": ["order_id", "processed_timestamp"]},
                "meta": {},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_id", "type_": "str"},
                "meta": {},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "processed_timestamp", "type_": "datetime64[ns]"},
                "meta": {},
            },
        ],
        "meta": {},
    }


@pytest.fixture
def expected_sql_engine() -> Dict[str, Any]:
    return {
        "name": "orders.1.0.0",
        "expectations": [
            {
                "type": "expect_table_row_count_to_be_between",
                "kwargs": {"min_value": 10},
                "meta": {},
            },
            {
                "type": "expect_table_columns_to_match_ordered_list",
                "kwargs": {"column_list": ["order_id", "processed_timestamp"]},
                "meta": {},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_id", "type_": "STRING"},
                "meta": {},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "processed_timestamp", "type_": "TIMESTAMP_TZ"},
                "meta": {},
            },
        ],
        "meta": {},
    }


@pytest.fixture
def expected_sql_trino_engine() -> Dict[str, Any]:
    return {
        "name": "orders.1.0.0",
        "expectations": [
            {
                "type": "expect_table_row_count_to_be_between",
                "kwargs": {"min_value": 10},
                "meta": {},
            },
            {
                "type": "expect_table_columns_to_match_ordered_list",
                "kwargs": {"column_list": ["order_id", "processed_timestamp"]},
                "meta": {},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_id", "type_": "varchar"},
                "meta": {},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {
                    "column": "processed_timestamp",
                    "type_": "timestamp(3) with time zone",
                },
                "meta": {},
            },
        ],
        "meta": {},
    }


def test_to_great_expectation(data_contract_basic: OpenDataContractStandard):
    expected_json_suite = {
        "name": "orders.1.0.0",
        "expectations": [
            {
                "type": "expect_table_columns_to_match_ordered_list",
                "kwargs": {"column_list": ["order_id", "order_total", "order_status"]},
                "meta": {},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_id", "type_": "varchar"},
                "meta": {},
            },
            {
                "type": "expect_column_values_to_be_unique",
                "kwargs": {"column": "order_id"},
                "meta": {},
            },
            {
                "type": "expect_column_value_lengths_to_be_between",
                "kwargs": {"column": "order_id", "min_value": 8, "max_value": 10},
                "meta": {},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_total", "type_": "bigint"},
                "meta": {},
            },
            {
                "type": "expect_column_values_to_be_between",
                "kwargs": {
                    "column": "order_total",
                    "min_value": 0,
                    "max_value": 1000000,
                },
                "meta": {},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_status", "type_": "text"},
                "meta": {},
            },
            {
                "type": "expect_column_values_to_be_in_set",
                "kwargs": {"column": "order_status", "value_set": ["pending", "shipped", "delivered"]},
                "meta": {},
            },
        ],
        "meta": {},
    }

    result_orders = to_great_expectations(data_contract_basic, "orders")
    assert result_orders == json.dumps(expected_json_suite, indent=2)


def test_to_great_expectation_complex(data_contract_complex: OpenDataContractStandard):
    """
    Test with 2 model definitions in the contract
    """

    expected_orders = {
        "name": "orders.1.0.0",
        "expectations": [
            {
                "type": "expect_table_columns_to_match_ordered_list",
                "kwargs": {
                    "column_list": [
                        "order_id",
                        "order_timestamp",
                        "order_total",
                        "customer_id",
                        "customer_email_address",
                    ]
                },
                "meta": {},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_id", "type_": "text"},
                "meta": {},
            },
            {
                "type": "expect_column_values_to_be_unique",
                "kwargs": {"column": "order_id"},
                "meta": {},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_timestamp", "type_": "timestamp"},
                "meta": {},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_total", "type_": "long"},
                "meta": {},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "customer_id", "type_": "text"},
                "meta": {},
            },
            {
                "type": "expect_column_value_lengths_to_be_between",
                "kwargs": {"column": "customer_id", "min_value": 10, "max_value": 20},
                "meta": {},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "customer_email_address", "type_": "text"},
                "meta": {},
            },
        ],
        "meta": {},
    }

    expected_line_items = {
        "name": "line_items.1.0.0",
        "expectations": [
            {
                "type": "expect_table_columns_to_match_ordered_list",
                "kwargs": {"column_list": ["lines_item_id", "order_id", "sku"]},
                "meta": {},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "lines_item_id", "type_": "text"},
                "meta": {},
            },
            {
                "type": "expect_column_values_to_be_unique",
                "kwargs": {"column": "lines_item_id"},
                "meta": {},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_id", "type_": "text"},
                "meta": {},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "sku", "type_": "text"},
                "meta": {},
            },
        ],
        "meta": {},
    }
    result_orders = to_great_expectations(data_contract_complex, "orders")
    assert result_orders == json.dumps(expected_orders, indent=2)

    result_line_items = to_great_expectations(data_contract_complex, "line_items")

    assert result_line_items == json.dumps(expected_line_items, indent=2)


def test_to_great_expectation_quality(
    odcs: OpenDataContractStandard,
    expected_json_suite: Dict[str, Any],
):
    """
    Test with Quality definition in the contract
    """

    result = to_great_expectations(odcs, "orders")
    assert result == json.dumps(expected_json_suite, indent=2)


def test_to_great_expectation_custom_name(
    odcs: OpenDataContractStandard,
):
    """
    Test with Quality definition in the contract
    """
    expected = {
        "name": "my_expectation_suite_name",
        "expectations": [
            {
                "type": "expect_table_row_count_to_be_between",
                "kwargs": {"min_value": 10},
                "meta": {},
            },
            {
                "type": "expect_table_columns_to_match_ordered_list",
                "kwargs": {"column_list": ["order_id", "processed_timestamp"]},
                "meta": {},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_id", "type_": "string"},
                "meta": {},
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "processed_timestamp", "type_": "timestamp"},
                "meta": {},
            },
        ],
        "meta": {},
    }

    result = to_great_expectations(
        odcs,
        schema_name="orders",
        expectation_suite_name="my_expectation_suite_name",
    )
    assert result == json.dumps(expected, indent=2)


def test_to_great_expectation_engine_spark(
    odcs: OpenDataContractStandard,
    expected_spark_engine: Dict[str, Any],
):
    """
    Test with Spark engine
    """
    result = to_great_expectations(
        odcs,
        schema_name="orders",
        engine="spark",
    )
    assert result == json.dumps(expected_spark_engine, indent=2)


def test_to_great_expectation_engine_pandas(
    odcs: OpenDataContractStandard,
    expected_pandas_engine: Dict[str, Any],
):
    """
    Test with pandas engine
    """
    result = to_great_expectations(
        odcs,
        schema_name="orders",
        engine="pandas",
    )
    assert result == json.dumps(expected_pandas_engine, indent=2)


def test_to_great_expectation_engine_sql(
    odcs: OpenDataContractStandard,
    expected_sql_engine: Dict[str, Any],
):
    """
    Test with sql engine
    """
    result = to_great_expectations(
        odcs,
        schema_name="orders",
        engine="sql",
    )
    assert result == json.dumps(expected_sql_engine, indent=2)


def test_to_great_expectation_engine_sql_trino(
    odcs: OpenDataContractStandard,
    expected_sql_trino_engine: Dict[str, Any],
):
    """
    Test with sql engine and sql server trino trino
    """
    result = to_great_expectations(
        odcs,
        schema_name="orders",
        engine="sql",
        sql_server_type="trino",
    )
    assert result == json.dumps(expected_sql_trino_engine, indent=2)


def test_cli_with_spark_engine(expected_spark_engine: Dict[str, Any]):
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "./fixtures/great-expectations/odcs.yaml",
            "--format",
            "great-expectations",
            "--engine",
            "spark",
        ],
    )
    assert result.output.replace("\n", "") == json.dumps(expected_spark_engine, indent=2).replace("\n", "")


def test_cli_with_pandas_engine(expected_pandas_engine: Dict[str, Any]):
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "./fixtures/great-expectations/odcs.yaml",
            "--format",
            "great-expectations",
            "--engine",
            "pandas",
        ],
    )
    assert result.output.replace("\n", "") == json.dumps(expected_pandas_engine, indent=2).replace("\n", "")


def test_cli_with_sql_engine(expected_sql_engine: Dict[str, Any]):
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "./fixtures/great-expectations/odcs.yaml",
            "--format",
            "great-expectations",
            "--engine",
            "sql",
        ],
    )
    assert result.output.replace("\n", "") == json.dumps(expected_sql_engine, indent=2).replace("\n", "")


def test_cli_with_sql_trino_engine(expected_sql_trino_engine: Dict[str, Any]):
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "./fixtures/great-expectations/odcs.yaml",
            "--format",
            "great-expectations",
            "--engine",
            "sql",
            "--sql-server-type",
            "trino",
        ],
    )
    assert result.output.replace("\n", "") == json.dumps(expected_sql_trino_engine, indent=2).replace("\n", "")


def test_to_great_expectation_quality_yaml(
    data_contract_great_expectations_quality_yaml: OpenDataContractStandard,
    expected_json_suite_table_quality: Dict[str, Any],
):
    """
    Test with Quality definition in a model quality list
    """
    result = to_great_expectations(data_contract_great_expectations_quality_yaml, "orders")
    assert result == json.dumps(expected_json_suite_table_quality, indent=2)


def test_to_great_expectation_quality_column(
    data_contract_great_expectations_quality_column: OpenDataContractStandard,
    expected_json_suite_with_enum: Dict[str, Any],
):
    """
    Test with quality definition in a field quality list
    """
    result = to_great_expectations(data_contract_great_expectations_quality_column, "orders")
    assert result == json.dumps(expected_json_suite_with_enum, indent=2)
