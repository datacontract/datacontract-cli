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
            "great-expectations",
            "./fixtures/export/datacontract.odcs.yaml",
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
    return resolve.resolve_data_contract_from_location("./fixtures/great-expectations/odcs.yaml")


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
    _col_meta = lambda col, typ: {  # noqa: E731
        "expectation_id": f"my-data-contract-id.{col}.{col}_must_be_of_type_{typ}",
        "rule_location": "quality_column",
        "name": f"{col} must be of type {typ}",
        "description": f"{col} must be of type {typ}",
        "dimension": "conformity",
    }
    _not_null = lambda col: {  # noqa: E731
        "expectation_id": f"my-data-contract-id.{col}.{col}_must_be_filled",
        "rule_location": "quality_column",
        "name": f"{col} must be filled",
        "description": f"{col} must be not null values",
        "dimension": "completeness",
    }
    return {
        "name": "orders.1.0.0",
        "expectations": [
            {
                "type": "expect_table_row_count_to_be_between",
                "kwargs": {"min_value": 10},
                "meta": {
                    "expectation_id": "my-data-contract-id.quality_rule",
                    "rule_location": "quality_table",
                },
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_id", "type_": "string"},
                "meta": _col_meta("order_id", "string"),
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "order_id"},
                "meta": _not_null("order_id"),
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "processed_timestamp", "type_": "timestamp"},
                "meta": _col_meta("processed_timestamp", "timestamp"),
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "processed_timestamp"},
                "meta": _not_null("processed_timestamp"),
            },
        ],
        "meta": {},
    }


@pytest.fixture
def expected_json_suite_table_quality() -> Dict[str, Any]:
    return {
        "name": "orders.1.0.0",
        "expectations": [
            {
                "type": "expect_table_row_count_to_be_between",
                "kwargs": {"min_value": 10},
                "meta": {
                    "expectation_id": "my-data-contract-id.quality_rule",
                    "rule_location": "quality_table",
                },
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_id", "type_": "string"},
                "meta": {
                    "expectation_id": "my-data-contract-id.order_id.order_id_must_be_of_type_string",
                    "rule_location": "quality_column",
                    "name": "order_id must be of type string",
                    "description": "order_id must be of type string",
                    "dimension": "conformity",
                },
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "order_id"},
                "meta": {
                    "expectation_id": "my-data-contract-id.order_id.order_id_must_be_filled",
                    "rule_location": "quality_column",
                    "name": "order_id must be filled",
                    "description": "order_id must be not null values",
                    "dimension": "completeness",
                },
            },
        ],
        "meta": {},
    }


@pytest.fixture
def expected_json_suite_with_enum() -> Dict[str, Any]:
    return {
        "name": "orders.1.1.1",
        "expectations": [
            # --- id: string, primaryKey+required+unique → only primaryKey rules ---
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "id", "type_": "string"},
                "meta": {
                    "expectation_id": "my-data-contract-id.id.id_must_be_of_type_string",
                    "rule_location": "quality_column",
                    "name": "id must be of type string",
                    "description": "id must be of type string",
                    "dimension": "conformity",
                },
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "id"},
                "meta": {
                    "expectation_id": "my-data-contract-id.id.id_must_be_filled_primary_key",
                    "rule_location": "quality_column",
                    "name": "id must be filled (primary key)",
                    "description": "id is a primary key and must not contain null values",
                    "dimension": "completeness",
                },
            },
            {
                "type": "expect_column_values_to_be_unique",
                "kwargs": {"column": "id"},
                "meta": {
                    "expectation_id": "my-data-contract-id.id.id_must_be_unique_primary_key",
                    "rule_location": "quality_column",
                    "name": "id must be unique (primary key)",
                    "description": "id is a primary key and must contain unique values",
                    "dimension": "uniqueness",
                },
            },
            # --- type: string, required, enum + quality block ---
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "type", "type_": "string"},
                "meta": {
                    "expectation_id": "my-data-contract-id.type.type_must_be_of_type_string",
                    "rule_location": "quality_column",
                    "name": "type must be of type string",
                    "description": "type must be of type string",
                    "dimension": "conformity",
                },
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "type"},
                "meta": {
                    "expectation_id": "my-data-contract-id.type.type_must_be_filled",
                    "rule_location": "quality_column",
                    "name": "type must be filled",
                    "description": "type must be not null values",
                    "dimension": "completeness",
                },
            },
            {
                "type": "expect_column_values_to_be_in_set",
                "kwargs": {"column": "type", "value_set": ["A", "B", "C", "D", "E"]},
                "meta": {
                    "expectation_id": "my-data-contract-id.type.type_must_belong_to_allowed_values",
                    "rule_location": "quality_column",
                    "name": "type must belong to allowed values",
                    "description": "type must be in the set of allowed values",
                    "dimension": "conformity",
                },
            },
            # Bug fix: column is in kwargs, not at root level
            {
                "type": "expect_column_value_lengths_to_equal",
                "kwargs": {"value": 1, "column": "type"},
                "meta": {
                    "expectation_id": "my-data-contract-id.type.accepted_values_for_type",
                    "rule_location": "quality_column",
                    "description": "Accepted Values for type",
                    "notes": "Ensures that column length is 1.",
                },
            },
        ],
        "meta": {},
    }


@pytest.fixture
def expected_spark_engine() -> Dict[str, Any]:
    _not_null = lambda col: {  # noqa: E731
        "rule_location": "quality_column",
        "name": f"{col} must be filled",
        "description": f"{col} must be not null values",
        "dimension": "completeness",
    }
    return {
        "name": "orders.1.0.0",
        "expectations": [
            {
                "type": "expect_table_row_count_to_be_between",
                "kwargs": {"min_value": 10},
                "meta": {
                    "expectation_id": "my-data-contract-id.quality_rule",
                    "rule_location": "quality_table",
                },
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_id", "type_": "StringType"},
                "meta": {
                    "expectation_id": "my-data-contract-id.order_id.order_id_must_be_of_type_stringtype",
                    "rule_location": "quality_column",
                    "name": "order_id must be of type StringType",
                    "description": "order_id must be of type StringType",
                    "dimension": "conformity",
                },
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "order_id"},
                "meta": {
                    "expectation_id": "my-data-contract-id.order_id.order_id_must_be_filled",
                    **_not_null("order_id"),
                },
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "processed_timestamp", "type_": "TimestampType"},
                "meta": {
                    "expectation_id": "my-data-contract-id.processed_timestamp.processed_timestamp_must_be_of_type_timestamptype",
                    "rule_location": "quality_column",
                    "name": "processed_timestamp must be of type TimestampType",
                    "description": "processed_timestamp must be of type TimestampType",
                    "dimension": "conformity",
                },
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "processed_timestamp"},
                "meta": {
                    "expectation_id": "my-data-contract-id.processed_timestamp.processed_timestamp_must_be_filled",
                    **_not_null("processed_timestamp"),
                },
            },
        ],
        "meta": {},
    }


@pytest.fixture
def expected_pandas_engine() -> Dict[str, Any]:
    _not_null = lambda col: {  # noqa: E731
        "rule_location": "quality_column",
        "name": f"{col} must be filled",
        "description": f"{col} must be not null values",
        "dimension": "completeness",
    }
    return {
        "name": "orders.1.0.0",
        "expectations": [
            {
                "type": "expect_table_row_count_to_be_between",
                "kwargs": {"min_value": 10},
                "meta": {
                    "expectation_id": "my-data-contract-id.quality_rule",
                    "rule_location": "quality_table",
                },
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_id", "type_": "str"},
                "meta": {
                    "expectation_id": "my-data-contract-id.order_id.order_id_must_be_of_type_str",
                    "rule_location": "quality_column",
                    "name": "order_id must be of type str",
                    "description": "order_id must be of type str",
                    "dimension": "conformity",
                },
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "order_id"},
                "meta": {
                    "expectation_id": "my-data-contract-id.order_id.order_id_must_be_filled",
                    **_not_null("order_id"),
                },
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "processed_timestamp", "type_": "datetime64[ns]"},
                "meta": {
                    "expectation_id": "my-data-contract-id.processed_timestamp.processed_timestamp_must_be_of_type_datetime64_ns",
                    "rule_location": "quality_column",
                    "name": "processed_timestamp must be of type datetime64[ns]",
                    "description": "processed_timestamp must be of type datetime64[ns]",
                    "dimension": "conformity",
                },
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "processed_timestamp"},
                "meta": {
                    "expectation_id": "my-data-contract-id.processed_timestamp.processed_timestamp_must_be_filled",
                    **_not_null("processed_timestamp"),
                },
            },
        ],
        "meta": {},
    }


@pytest.fixture
def expected_sql_engine() -> Dict[str, Any]:
    _not_null = lambda col: {  # noqa: E731
        "rule_location": "quality_column",
        "name": f"{col} must be filled",
        "description": f"{col} must be not null values",
        "dimension": "completeness",
    }
    return {
        "name": "orders.1.0.0",
        "expectations": [
            {
                "type": "expect_table_row_count_to_be_between",
                "kwargs": {"min_value": 10},
                "meta": {
                    "expectation_id": "my-data-contract-id.quality_rule",
                    "rule_location": "quality_table",
                },
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_id", "type_": "STRING"},
                "meta": {
                    "expectation_id": "my-data-contract-id.order_id.order_id_must_be_of_type_string",
                    "rule_location": "quality_column",
                    "name": "order_id must be of type STRING",
                    "description": "order_id must be of type STRING",
                    "dimension": "conformity",
                },
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "order_id"},
                "meta": {
                    "expectation_id": "my-data-contract-id.order_id.order_id_must_be_filled",
                    **_not_null("order_id"),
                },
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "processed_timestamp", "type_": "TIMESTAMP_TZ"},
                "meta": {
                    "expectation_id": "my-data-contract-id.processed_timestamp.processed_timestamp_must_be_of_type_timestamp_tz",
                    "rule_location": "quality_column",
                    "name": "processed_timestamp must be of type TIMESTAMP_TZ",
                    "description": "processed_timestamp must be of type TIMESTAMP_TZ",
                    "dimension": "conformity",
                },
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "processed_timestamp"},
                "meta": {
                    "expectation_id": "my-data-contract-id.processed_timestamp.processed_timestamp_must_be_filled",
                    **_not_null("processed_timestamp"),
                },
            },
        ],
        "meta": {},
    }


@pytest.fixture
def expected_sql_trino_engine() -> Dict[str, Any]:
    _not_null = lambda col: {  # noqa: E731
        "rule_location": "quality_column",
        "name": f"{col} must be filled",
        "description": f"{col} must be not null values",
        "dimension": "completeness",
    }
    return {
        "name": "orders.1.0.0",
        "expectations": [
            {
                "type": "expect_table_row_count_to_be_between",
                "kwargs": {"min_value": 10},
                "meta": {
                    "expectation_id": "my-data-contract-id.quality_rule",
                    "rule_location": "quality_table",
                },
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_id", "type_": "varchar"},
                "meta": {
                    "expectation_id": "my-data-contract-id.order_id.order_id_must_be_of_type_varchar",
                    "rule_location": "quality_column",
                    "name": "order_id must be of type varchar",
                    "description": "order_id must be of type varchar",
                    "dimension": "conformity",
                },
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "order_id"},
                "meta": {
                    "expectation_id": "my-data-contract-id.order_id.order_id_must_be_filled",
                    **_not_null("order_id"),
                },
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {
                    "column": "processed_timestamp",
                    "type_": "timestamp(3) with time zone",
                },
                "meta": {
                    "expectation_id": "my-data-contract-id.processed_timestamp.processed_timestamp_must_be_of_type_timestamp_3_with_time_zone",
                    "rule_location": "quality_column",
                    "name": "processed_timestamp must be of type timestamp(3) with time zone",
                    "description": "processed_timestamp must be of type timestamp(3) with time zone",
                    "dimension": "conformity",
                },
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "processed_timestamp"},
                "meta": {
                    "expectation_id": "my-data-contract-id.processed_timestamp.processed_timestamp_must_be_filled",
                    **_not_null("processed_timestamp"),
                },
            },
        ],
        "meta": {},
    }


def test_to_great_expectation(data_contract_basic: OpenDataContractStandard):
    # Use column names for all expectation naming (businessName is ignored)
    _oid = "order_id"
    _ot = "order_total"
    _os = "order_status"
    expected_json_suite = {
        "name": "orders.1.0.0",
        "expectations": [
            # --- order_id: varchar, primaryKey+required+unique → only primaryKey rules ---
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_id", "type_": "varchar"},
                "meta": {
                    "expectation_id": "orders-unit-test.order_id.order_id_must_be_of_type_varchar",
                    "rule_location": "quality_column",
                    "name": f"{_oid} must be of type varchar",
                    "description": f"{_oid} must be of type varchar",
                    "dimension": "conformity",
                },
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "order_id"},
                "meta": {
                    "expectation_id": "orders-unit-test.order_id.order_id_must_be_filled_primary_key",
                    "rule_location": "quality_column",
                    "name": f"{_oid} must be filled (primary key)",
                    "description": f"{_oid} is a primary key and must not contain null values",
                    "dimension": "completeness",
                },
            },
            {
                "type": "expect_column_values_to_be_unique",
                "kwargs": {"column": "order_id"},
                "meta": {
                    "expectation_id": "orders-unit-test.order_id.order_id_must_be_unique_primary_key",
                    "rule_location": "quality_column",
                    "name": f"{_oid} must be unique (primary key)",
                    "description": f"{_oid} is a primary key and must contain unique values",
                    "dimension": "uniqueness",
                },
            },
            {
                "type": "expect_column_value_lengths_to_be_between",
                "kwargs": {"column": "order_id", "min_value": 8, "max_value": 10},
                "meta": {
                    "expectation_id": "orders-unit-test.order_id.order_id_length_must_be_between_8_and_10",
                    "rule_location": "quality_column",
                    "name": f"{_oid} length must be between 8 and 10",
                    "description": f"{_oid} length must be between 8 and 10",
                    "dimension": "conformity",
                },
            },
            {
                "type": "expect_column_values_to_match_regex",
                "kwargs": {"column": "order_id", "regex": "^B[0-9]+$"},
                "meta": {
                    "expectation_id": "orders-unit-test.order_id.order_id_must_match_pattern_b_0_9",
                    "rule_location": "quality_column",
                    "name": f"{_oid} must match pattern ^B[0-9]+$",
                    "description": f"{_oid} values must match the pattern ^B[0-9]+$",
                    "dimension": "conformity",
                },
            },
            # --- order_total: bigint, required, minimum+maximum ---
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_total", "type_": "bigint"},
                "meta": {
                    "expectation_id": "orders-unit-test.order_total.order_total_must_be_of_type_bigint",
                    "rule_location": "quality_column",
                    "name": f"{_ot} must be of type bigint",
                    "description": f"{_ot} must be of type bigint",
                    "dimension": "conformity",
                },
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "order_total"},
                "meta": {
                    "expectation_id": "orders-unit-test.order_total.order_total_must_be_filled",
                    "rule_location": "quality_column",
                    "name": f"{_ot} must be filled",
                    "description": f"{_ot} must be not null values",
                    "dimension": "completeness",
                },
            },
            {
                "type": "expect_column_values_to_be_between",
                "kwargs": {"column": "order_total", "min_value": 0, "max_value": 1000000},
                "meta": {
                    "expectation_id": "orders-unit-test.order_total.order_total_must_be_between_0_and_1000000",
                    "rule_location": "quality_column",
                    "name": f"{_ot} must be between 0 and 1000000",
                    "description": f"{_ot} value must be between 0 and 1000000",
                    "dimension": "conformity",
                },
            },
            # --- order_status: text, primaryKey+required → only primaryKey rules, then enum ---
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_status", "type_": "text"},
                "meta": {
                    "expectation_id": "orders-unit-test.order_status.order_status_must_be_of_type_text",
                    "rule_location": "quality_column",
                    "name": f"{_os} must be of type text",
                    "description": f"{_os} must be of type text",
                    "dimension": "conformity",
                },
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "order_status"},
                "meta": {
                    "expectation_id": "orders-unit-test.order_status.order_status_must_be_filled_primary_key",
                    "rule_location": "quality_column",
                    "name": f"{_os} must be filled (primary key)",
                    "description": f"{_os} is a primary key and must not contain null values",
                    "dimension": "completeness",
                },
            },
            {
                "type": "expect_column_values_to_be_unique",
                "kwargs": {"column": "order_status"},
                "meta": {
                    "expectation_id": "orders-unit-test.order_status.order_status_must_be_unique_primary_key",
                    "rule_location": "quality_column",
                    "name": f"{_os} must be unique (primary key)",
                    "description": f"{_os} is a primary key and must contain unique values",
                    "dimension": "uniqueness",
                },
            },
            {
                "type": "expect_column_values_to_be_in_set",
                "kwargs": {"column": "order_status", "value_set": ["pending", "shipped", "delivered"]},
                "meta": {
                    "expectation_id": "orders-unit-test.order_status.order_status_must_belong_to_allowed_values",
                    "rule_location": "quality_column",
                    "name": f"{_os} must belong to allowed values",
                    "description": f"{_os} must be in the set of allowed values",
                    "dimension": "conformity",
                },
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
    _uuid_regex = r"^[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}$"
    _email_regex = r"^[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$"
    _cid = "orders-latest"

    def _sk(text: str) -> str:
        import re as _re

        r = _re.sub(r"[^a-z0-9_]", "_", text.strip().lower())
        return _re.sub(r"_+", "_", r).strip("_")

    def _col_type(col, dn, t):
        return {
            "expectation_id": f"{_cid}.{col}.{_sk(dn + ' must be of type ' + t)}",
            "rule_location": "quality_column",
            "name": f"{dn} must be of type {t}",
            "description": f"{dn} must be of type {t}",
            "dimension": "conformity",
        }

    def _not_null(col, dn):
        return {
            "expectation_id": f"{_cid}.{col}.{_sk(dn + ' must be filled')}",
            "rule_location": "quality_column",
            "name": f"{dn} must be filled",
            "description": f"{dn} must be not null values",
            "dimension": "completeness",
        }

    def _unique_meta(col, dn):
        return {
            "expectation_id": f"{_cid}.{col}.{_sk(dn + ' must be unique')}",
            "rule_location": "quality_column",
            "name": f"{dn} must be unique",
            "description": f"{dn} must contain unique values",
            "dimension": "uniqueness",
        }

    # order_id uses column name for display (businessName "Order ID" is ignored)
    oid = "order_id"

    expected_orders = {
        "name": "orders.1.0.0",
        "expectations": [
            # order_id: text, required, unique, format=uuid
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_id", "type_": "text"},
                "meta": _col_type("order_id", oid, "text"),
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "order_id"},
                "meta": _not_null("order_id", oid),
            },
            {
                "type": "expect_column_values_to_be_unique",
                "kwargs": {"column": "order_id"},
                "meta": _unique_meta("order_id", oid),
            },
            {
                "type": "expect_column_values_to_match_regex",
                "kwargs": {"column": "order_id", "regex": _uuid_regex},
                "meta": {
                    "expectation_id": f"{_cid}.order_id.{_sk(oid + ' must be a valid uuid')}",
                    "rule_location": "quality_column",
                    "name": f"{oid} must be a valid uuid",
                    "description": f"{oid} values must be in uuid format",
                    "dimension": "conformity",
                },
            },
            # order_timestamp: timestamp, required
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_timestamp", "type_": "timestamp"},
                "meta": _col_type("order_timestamp", "order_timestamp", "timestamp"),
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "order_timestamp"},
                "meta": _not_null("order_timestamp", "order_timestamp"),
            },
            # order_total: long, required
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_total", "type_": "long"},
                "meta": _col_type("order_total", "order_total", "long"),
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "order_total"},
                "meta": _not_null("order_total", "order_total"),
            },
            # customer_id: text, minLength+maxLength
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "customer_id", "type_": "text"},
                "meta": _col_type("customer_id", "customer_id", "text"),
            },
            {
                "type": "expect_column_value_lengths_to_be_between",
                "kwargs": {"column": "customer_id", "min_value": 10, "max_value": 20},
                "meta": {
                    "expectation_id": f"{_cid}.customer_id.{_sk('customer_id length must be between 10 and 20')}",
                    "rule_location": "quality_column",
                    "name": "customer_id length must be between 10 and 20",
                    "description": "customer_id length must be between 10 and 20",
                    "dimension": "conformity",
                },
            },
            # customer_email_address: text, required, format=email
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "customer_email_address", "type_": "text"},
                "meta": _col_type("customer_email_address", "customer_email_address", "text"),
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "customer_email_address"},
                "meta": _not_null("customer_email_address", "customer_email_address"),
            },
            {
                "type": "expect_column_values_to_match_regex",
                "kwargs": {"column": "customer_email_address", "regex": _email_regex},
                "meta": {
                    "expectation_id": f"{_cid}.customer_email_address.{_sk('customer_email_address must be a valid email')}",
                    "rule_location": "quality_column",
                    "name": "customer_email_address must be a valid email",
                    "description": "customer_email_address values must be in email format",
                    "dimension": "conformity",
                },
            },
        ],
        "meta": {},
    }

    # sku uses column name for display (businessName "Stock Keeping Unit" is ignored)
    sku_dn = "sku"

    expected_line_items = {
        "name": "line_items.1.0.0",
        "expectations": [
            # lines_item_id: text, required, unique
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "lines_item_id", "type_": "text"},
                "meta": _col_type("lines_item_id", "lines_item_id", "text"),
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "lines_item_id"},
                "meta": _not_null("lines_item_id", "lines_item_id"),
            },
            {
                "type": "expect_column_values_to_be_unique",
                "kwargs": {"column": "lines_item_id"},
                "meta": _unique_meta("lines_item_id", "lines_item_id"),
            },
            # order_id: text, format=uuid (from definition ref)
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_id", "type_": "text"},
                "meta": _col_type("order_id", oid, "text"),
            },
            {
                "type": "expect_column_values_to_match_regex",
                "kwargs": {"column": "order_id", "regex": _uuid_regex},
                "meta": {
                    "expectation_id": f"{_cid}.order_id.{_sk(oid + ' must be a valid uuid')}",
                    "rule_location": "quality_column",
                    "name": f"{oid} must be a valid uuid",
                    "description": f"{oid} values must be in uuid format",
                    "dimension": "conformity",
                },
            },
            # sku: text, pattern from definition ref
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "sku", "type_": "text"},
                "meta": _col_type("sku", sku_dn, "text"),
            },
            {
                "type": "expect_column_values_to_match_regex",
                "kwargs": {"column": "sku", "regex": "^[A-Za-z0-9]{8,14}$"},
                "meta": {
                    "expectation_id": f"{_cid}.sku.{_sk(sku_dn + ' must match pattern ^[A-Za-z0-9]{8,14}$')}",
                    "rule_location": "quality_column",
                    "name": f"{sku_dn} must match pattern ^[A-Za-z0-9]{{8,14}}$",
                    "description": f"{sku_dn} values must match the pattern ^[A-Za-z0-9]{{8,14}}$",
                    "dimension": "conformity",
                },
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
    Test with Quality definition in the contract and custom suite name
    """
    _not_null = lambda col: {  # noqa: E731
        "expectation_id": f"my-data-contract-id.{col}.{col}_must_be_filled",
        "rule_location": "quality_column",
        "name": f"{col} must be filled",
        "description": f"{col} must be not null values",
        "dimension": "completeness",
    }
    _col_type = lambda col, t: {  # noqa: E731
        "expectation_id": f"my-data-contract-id.{col}.{col}_must_be_of_type_{t}",
        "rule_location": "quality_column",
        "name": f"{col} must be of type {t}",
        "description": f"{col} must be of type {t}",
        "dimension": "conformity",
    }
    expected = {
        "name": "my_expectation_suite_name",
        "expectations": [
            {
                "type": "expect_table_row_count_to_be_between",
                "kwargs": {"min_value": 10},
                "meta": {
                    "expectation_id": "my-data-contract-id.quality_rule",
                    "rule_location": "quality_table",
                },
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "order_id", "type_": "string"},
                "meta": _col_type("order_id", "string"),
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "order_id"},
                "meta": _not_null("order_id"),
            },
            {
                "type": "expect_column_values_to_be_of_type",
                "kwargs": {"column": "processed_timestamp", "type_": "timestamp"},
                "meta": _col_type("processed_timestamp", "timestamp"),
            },
            {
                "type": "expect_column_values_to_not_be_null",
                "kwargs": {"column": "processed_timestamp"},
                "meta": _not_null("processed_timestamp"),
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
            "great-expectations",
            "./fixtures/great-expectations/odcs.yaml",
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
            "great-expectations",
            "./fixtures/great-expectations/odcs.yaml",
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
            "great-expectations",
            "./fixtures/great-expectations/odcs.yaml",
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
            "great-expectations",
            "./fixtures/great-expectations/odcs.yaml",
            "--engine",
            "sql",
            "--dialect",
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


# ─── New feature tests ──────────────────────────────────────────────────────────


@pytest.fixture
def data_contract_all_constraints() -> OpenDataContractStandard:
    return resolve.resolve_data_contract_from_location(
        "./fixtures/great-expectations/datacontract_all_constraints.yaml",
    )


@pytest.fixture
def data_contract_quality_meta() -> OpenDataContractStandard:
    return resolve.resolve_data_contract_from_location(
        "./fixtures/great-expectations/datacontract_quality_meta.yaml",
    )


def test_primary_key_generates_not_null_and_unique(data_contract_all_constraints: OpenDataContractStandard):
    """primaryKey: true must generate both NOT_NULL and UNIQUE expectations; standalone required/unique are suppressed."""
    result = json.loads(to_great_expectations(data_contract_all_constraints, "products"))
    pk_not_null = next(
        e
        for e in result["expectations"]
        if e["type"] == "expect_column_values_to_not_be_null"
        and e.get("meta", {}).get("expectation_id")
        == "test-all-constraints.product_id.product_id_must_be_filled_primary_key"
    )
    assert pk_not_null["meta"]["rule_location"] == "quality_column"
    assert pk_not_null["meta"]["dimension"] == "completeness"
    assert "must be filled (primary key)" in pk_not_null["meta"]["name"]

    pk_unique = next(
        e
        for e in result["expectations"]
        if e["type"] == "expect_column_values_to_be_unique"
        and e.get("meta", {}).get("expectation_id")
        == "test-all-constraints.product_id.product_id_must_be_unique_primary_key"
    )
    assert pk_unique["meta"]["dimension"] == "uniqueness"

    # Standalone required and unique must NOT be generated when primaryKey is set
    standalone_ids = {e.get("meta", {}).get("expectation_id") for e in result["expectations"]}
    assert "test-all-constraints.product_id.product_id_must_be_filled" not in standalone_ids
    assert "test-all-constraints.product_id.product_id_must_be_unique" not in standalone_ids


def test_required_generates_not_null(data_contract_all_constraints: OpenDataContractStandard):
    """required: true must generate a NOT_NULL expectation using businessName or column name."""
    result = json.loads(to_great_expectations(data_contract_all_constraints, "products"))
    required_not_null = next(
        e
        for e in result["expectations"]
        if e["type"] == "expect_column_values_to_not_be_null"
        and e.get("meta", {}).get("expectation_id") == "test-all-constraints.email.email_must_be_filled"
    )
    assert required_not_null["meta"]["rule_location"] == "quality_column"
    assert required_not_null["meta"]["dimension"] == "completeness"
    assert "must be filled" in required_not_null["meta"]["name"]
    assert "must be not null values" in required_not_null["meta"]["description"]


def test_unique_generates_unique_expectation(data_contract_all_constraints: OpenDataContractStandard):
    """unique: true must generate a UNIQUE expectation; when primaryKey=true it becomes primary_key_unique instead."""
    result = json.loads(to_great_expectations(data_contract_all_constraints, "products"))
    # product_id has primaryKey=true so it gets primary_key_unique, not standalone unique
    unique_exp = next(
        e
        for e in result["expectations"]
        if e["type"] == "expect_column_values_to_be_unique"
        and e.get("meta", {}).get("expectation_id")
        == "test-all-constraints.product_id.product_id_must_be_unique_primary_key"
    )
    assert unique_exp["meta"]["dimension"] == "uniqueness"
    assert unique_exp["meta"]["rule_location"] == "quality_column"
    assert "must be unique (primary key)" in unique_exp["meta"]["name"]


def test_string_length_range(data_contract_all_constraints: OpenDataContractStandard):
    """minLength+maxLength must produce a single length_range expectation with human-readable meta."""
    result = json.loads(to_great_expectations(data_contract_all_constraints, "products"))
    length_exp = next(
        e
        for e in result["expectations"]
        if e["type"] == "expect_column_value_lengths_to_be_between"
        and e.get("kwargs", {}).get("column") == "product_id"
    )
    assert length_exp["kwargs"]["min_value"] == 5
    assert length_exp["kwargs"]["max_value"] == 20
    assert (
        length_exp["meta"]["expectation_id"]
        == "test-all-constraints.product_id.product_id_length_must_be_between_5_and_20"
    )
    assert length_exp["meta"]["dimension"] == "conformity"
    assert "length must be between 5 and 20" in length_exp["meta"]["name"]


def test_string_pattern(data_contract_all_constraints: OpenDataContractStandard):
    """pattern must generate a regex expectation with human-readable meta."""
    result = json.loads(to_great_expectations(data_contract_all_constraints, "products"))
    regex_exp = next(
        e
        for e in result["expectations"]
        if e["type"] == "expect_column_values_to_match_regex" and e.get("kwargs", {}).get("column") == "product_id"
    )
    assert regex_exp["kwargs"]["regex"] == "^PRD-[0-9]+$"
    assert (
        regex_exp["meta"]["expectation_id"] == "test-all-constraints.product_id.product_id_must_match_pattern_prd_0_9"
    )
    assert regex_exp["meta"]["dimension"] == "conformity"
    assert "must match pattern" in regex_exp["meta"]["name"]


def test_string_format_email(data_contract_all_constraints: OpenDataContractStandard):
    """format: email must generate a regex expectation with human-readable name."""
    result = json.loads(to_great_expectations(data_contract_all_constraints, "products"))
    email_exp = next(
        e
        for e in result["expectations"]
        if e["type"] == "expect_column_values_to_match_regex" and e.get("kwargs", {}).get("column") == "email"
    )
    assert "@" in email_exp["kwargs"]["regex"]
    assert email_exp["meta"]["expectation_id"] == "test-all-constraints.email.email_must_be_a_valid_email"
    assert "must be a valid email" in email_exp["meta"]["name"]
    assert "email format" in email_exp["meta"]["description"]


def test_string_format_url(data_contract_all_constraints: OpenDataContractStandard):
    """format: url must generate a regex expectation."""
    result = json.loads(to_great_expectations(data_contract_all_constraints, "products"))
    url_exp = next(
        e
        for e in result["expectations"]
        if e["type"] == "expect_column_values_to_match_regex" and e.get("kwargs", {}).get("column") == "website"
    )
    assert url_exp["meta"]["expectation_id"] == "test-all-constraints.website.website_must_be_a_valid_url"


def test_numeric_value_range(data_contract_all_constraints: OpenDataContractStandard):
    """minimum+maximum must produce a single value_range expectation with human-readable meta."""
    result = json.loads(to_great_expectations(data_contract_all_constraints, "products"))
    range_exp = next(
        e
        for e in result["expectations"]
        if e["type"] == "expect_column_values_to_be_between"
        and e.get("kwargs", {}).get("column") == "quantity"
        and e.get("meta", {}).get("expectation_id")
        == "test-all-constraints.quantity.quantity_must_be_between_0_and_9999"
    )
    assert range_exp["kwargs"]["min_value"] == 0
    assert range_exp["kwargs"]["max_value"] == 9999
    assert range_exp["meta"]["dimension"] == "conformity"
    assert "must be between 0 and 9999" in range_exp["meta"]["name"]


def test_exclusive_min_max(data_contract_all_constraints: OpenDataContractStandard):
    """exclusiveMinimum and exclusiveMaximum must each produce an expectation with exclusive=true in meta."""
    result = json.loads(to_great_expectations(data_contract_all_constraints, "products"))

    excl_min = next(
        e
        for e in result["expectations"]
        if e.get("meta", {}).get("expectation_id")
        == "test-all-constraints.quantity.quantity_must_be_strictly_greater_than_1"
    )
    assert excl_min["type"] == "expect_column_values_to_be_between"
    assert excl_min["kwargs"]["min_value"] == -1
    assert excl_min["meta"]["exclusive"] is True

    excl_max = next(
        e
        for e in result["expectations"]
        if e.get("meta", {}).get("expectation_id")
        == "test-all-constraints.quantity.quantity_must_be_strictly_less_than_10000"
    )
    assert excl_max["kwargs"]["max_value"] == 10000
    assert excl_max["meta"]["exclusive"] is True


def test_enum_values(data_contract_all_constraints: OpenDataContractStandard):
    """enum in customProperties must generate an in_set expectation with human-readable meta."""
    result = json.loads(to_great_expectations(data_contract_all_constraints, "products"))
    enum_exp = next(
        e
        for e in result["expectations"]
        if e["type"] == "expect_column_values_to_be_in_set" and e.get("kwargs", {}).get("column") == "category"
    )
    assert set(enum_exp["kwargs"]["value_set"]) == {"electronics", "clothing", "food"}
    assert enum_exp["meta"]["expectation_id"] == "test-all-constraints.category.category_must_belong_to_allowed_values"
    assert enum_exp["meta"]["dimension"] == "conformity"
    assert "must belong to allowed values" in enum_exp["meta"]["name"]


def test_date_value_range(data_contract_all_constraints: OpenDataContractStandard):
    """minimum/maximum on date columns must produce a between expectation."""
    result = json.loads(to_great_expectations(data_contract_all_constraints, "products"))
    date_exp = next(
        e
        for e in result["expectations"]
        if e["type"] == "expect_column_values_to_be_between" and e.get("kwargs", {}).get("column") == "event_date"
    )
    assert date_exp["kwargs"]["min_value"] == "2020-01-01"
    assert date_exp["kwargs"]["max_value"] == "2030-12-31"
    assert (
        date_exp["meta"]["expectation_id"]
        == "test-all-constraints.event_date.event_date_must_be_between_2020_01_01_and_2030_12_31"
    )


def test_table_quality_enriched_meta(data_contract_all_constraints: OpenDataContractStandard):
    """Table-level quality blocks must have enriched meta with rule_location=quality_table."""
    result = json.loads(to_great_expectations(data_contract_all_constraints, "products"))
    row_count_exp = next(e for e in result["expectations"] if e["type"] == "expect_table_row_count_to_be_between")
    assert row_count_exp["meta"]["rule_location"] == "quality_table"
    assert row_count_exp["meta"]["expectation_id"] == "test-all-constraints.row_count_check"
    assert row_count_exp["kwargs"]["min_value"] == 1
    assert row_count_exp["kwargs"]["max_value"] == 1000000


def test_quality_meta_custom_properties(data_contract_quality_meta: OpenDataContractStandard):
    """customProperties in quality blocks must be flattened into the expectation meta."""
    result = json.loads(to_great_expectations(data_contract_quality_meta, "orders"))
    status_exp = next(e for e in result["expectations"] if e["type"] == "expect_column_values_to_be_in_set")
    assert status_exp["meta"]["ruleWeight"] == 10
    assert status_exp["meta"]["businessOwner"] == "revenue-team"
    assert status_exp["meta"]["expectation_id"] == "test-quality-meta.subscription_status.subscription_status_values"
    assert status_exp["meta"]["rule_location"] == "quality_column"


def test_column_not_duplicated_outside_kwargs(data_contract_quality_meta: OpenDataContractStandard):
    """Bug fix: column must only appear in kwargs, never at the root expectation level."""
    result = json.loads(to_great_expectations(data_contract_quality_meta, "orders"))
    for expectation in result["expectations"]:
        assert "column" not in expectation or expectation["column"] == expectation.get("kwargs", {}).get("column"), (
            f"column key found outside kwargs in expectation: {expectation}"
        )
        # Stricter: column must not exist at root (only in kwargs)
        root_keys = set(expectation.keys())
        assert "column" not in root_keys, f"'column' should not be a root key: {expectation}"


def test_quality_column_already_in_kwargs_not_duplicated():
    """When column is already provided in quality kwargs, it must not be added again."""
    from open_data_contract_standard.model import OpenDataContractStandard

    yaml_content = """
kind: DataContract
apiVersion: v3.1.0
id: test-dup
version: 1.0.0
schema:
  - name: tbl
    properties:
      - name: my_col
        logicalType: string
        quality:
          - type: custom
            engine: great-expectations
            description: Check Values
            implementation:
              type: expect_column_values_to_be_in_set
              kwargs:
                column: my_col
                value_set: [A, B]
              meta: {}
"""
    import os
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        path = f.name
    try:
        contract = OpenDataContractStandard.from_file(path)
        result = json.loads(to_great_expectations(contract, "tbl"))
        col_exp = next(e for e in result["expectations"] if e["type"] == "expect_column_values_to_be_in_set")
        # column must appear exactly once in kwargs
        assert col_exp["kwargs"]["column"] == "my_col"
        assert "column" not in col_exp  # not at root level
    finally:
        os.unlink(path)


def test_expectation_id_uses_contract_id():
    """The expectation_id must always be prefixed with the contract's id field."""
    from open_data_contract_standard.model import OpenDataContractStandard

    yaml_content = """
kind: DataContract
apiVersion: v3.1.0
id: my-special-contract-id
version: 2.0.0
schema:
  - name: tbl
    properties:
      - name: col_a
        logicalType: string
        required: true
"""
    import os
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        path = f.name
    try:
        contract = OpenDataContractStandard.from_file(path)
        result = json.loads(to_great_expectations(contract, "tbl"))
        not_null_exp = next(e for e in result["expectations"] if e["type"] == "expect_column_values_to_not_be_null")
        assert not_null_exp["meta"]["expectation_id"].startswith("my-special-contract-id.")
    finally:
        os.unlink(path)


def test_column_name_always_used_ignores_business_name():
    """Column name should always be used for expectation naming, businessName is always ignored."""
    from open_data_contract_standard.model import OpenDataContractStandard

    yaml_content = """
kind: DataContract
apiVersion: v3.1.0
id: test-column-naming
version: 1.0.0
schema:
  - name: tbl
    properties:
      - name: article_code
        logicalType: string
        businessName: NoBV
        required: true
        unique: true
      - name: currency_rate
        logicalType: number
        businessName: Exchange rate value
        required: true
      - name: invoice_id
        logicalType: string
        businessName: Rental Invoice Identifier
        required: true
"""
    import os
    import tempfile

    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        path = f.name
    try:
        contract = OpenDataContractStandard.from_file(path)
        result = json.loads(to_great_expectations(contract, "tbl"))

        # Test 1: article_code with businessName: NoBV should use column name
        article_code_type_exp = next(
            e
            for e in result["expectations"]
            if e["type"] == "expect_column_values_to_be_of_type" and e["kwargs"]["column"] == "article_code"
        )
        assert article_code_type_exp["meta"]["name"] == "article_code must be of type string"
        assert (
            article_code_type_exp["meta"]["expectation_id"]
            == "test-column-naming.article_code.article_code_must_be_of_type_string"
        )

        # Test 2: article_code not_null should use column name (NoBV ignored)
        article_code_not_null = next(
            e
            for e in result["expectations"]
            if e["type"] == "expect_column_values_to_not_be_null" and e["kwargs"]["column"] == "article_code"
        )
        assert article_code_not_null["meta"]["name"] == "article_code must be filled"
        assert (
            article_code_not_null["meta"]["expectation_id"]
            == "test-column-naming.article_code.article_code_must_be_filled"
        )

        # Test 3: article_code unique should use column name (NoBV ignored)
        article_code_unique = next(
            e
            for e in result["expectations"]
            if e["type"] == "expect_column_values_to_be_unique" and e["kwargs"]["column"] == "article_code"
        )
        assert article_code_unique["meta"]["name"] == "article_code must be unique"
        assert (
            article_code_unique["meta"]["expectation_id"]
            == "test-column-naming.article_code.article_code_must_be_unique"
        )

        # Test 4: currency_rate with valid businessName should STILL use column name (businessName always ignored)
        currency_rate_type_exp = next(
            e
            for e in result["expectations"]
            if e["type"] == "expect_column_values_to_be_of_type" and e["kwargs"]["column"] == "currency_rate"
        )
        assert currency_rate_type_exp["meta"]["name"] == "currency_rate must be of type number"
        assert (
            currency_rate_type_exp["meta"]["expectation_id"]
            == "test-column-naming.currency_rate.currency_rate_must_be_of_type_number"
        )
        # Verify businessName is NOT used
        assert "exchange_rate" not in currency_rate_type_exp["meta"]["name"].lower()
        assert "exchange_rate" not in currency_rate_type_exp["meta"]["expectation_id"].lower()

        # Test 5: currency_rate not_null should use column name
        currency_rate_not_null = next(
            e
            for e in result["expectations"]
            if e["type"] == "expect_column_values_to_not_be_null" and e["kwargs"]["column"] == "currency_rate"
        )
        assert currency_rate_not_null["meta"]["name"] == "currency_rate must be filled"
        assert (
            currency_rate_not_null["meta"]["expectation_id"]
            == "test-column-naming.currency_rate.currency_rate_must_be_filled"
        )

        # Test 6: invoice_id with businessName "Rental Invoice Identifier" should use column name
        invoice_id_type_exp = next(
            e
            for e in result["expectations"]
            if e["type"] == "expect_column_values_to_be_of_type" and e["kwargs"]["column"] == "invoice_id"
        )
        assert invoice_id_type_exp["meta"]["name"] == "invoice_id must be of type string"
        assert (
            invoice_id_type_exp["meta"]["expectation_id"]
            == "test-column-naming.invoice_id.invoice_id_must_be_of_type_string"
        )
        # Verify businessName is NOT used
        assert "rental" not in invoice_id_type_exp["meta"]["name"].lower()
        assert "rental" not in invoice_id_type_exp["meta"]["expectation_id"].lower()

        # Test 7: invoice_id not_null should use column name
        invoice_id_not_null = next(
            e
            for e in result["expectations"]
            if e["type"] == "expect_column_values_to_not_be_null" and e["kwargs"]["column"] == "invoice_id"
        )
        assert invoice_id_not_null["meta"]["name"] == "invoice_id must be filled"
        assert (
            invoice_id_not_null["meta"]["expectation_id"] == "test-column-naming.invoice_id.invoice_id_must_be_filled"
        )
    finally:
        os.unlink(path)
