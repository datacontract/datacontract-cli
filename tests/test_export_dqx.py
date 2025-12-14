import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(app, ["export", "./fixtures/dqx/datacontract.odcs.yaml", "--format", "dqx"])
    assert result.exit_code == 0


def test_to_dqx():
    actual = DataContract(data_contract_file="fixtures/dqx/datacontract.odcs.yaml").export("dqx")
    # Expected quality rules (based on the data contract)
    expected_rules = [
        {"check": {"arguments": {"column": "interaction_id"}, "function": "is_not_null"}, "criticality": "error"},
        {"check": {"arguments": {"column": "user_id"}, "function": "is_not_null"}, "criticality": "error"},
        {
            "check": {
                "arguments": {"columns": ["user_id"], "ref_columns": ["id"], "ref_table": "catalog1.schema1.user"},
                "function": "foreign_key",
            },
            "criticality": "error",
        },
        {"check": {"arguments": {"columns": ["user_id"]}, "function": "is_unique"}, "criticality": "error"},
        {
            "check": {
                "arguments": {"allowed": ["click", "view", "purchase", "like", "share"], "column": "interaction_type"},
                "function": "is_in_list",
            },
            "criticality": "error",
        },
        {
            "check": {
                "arguments": {"column": "interaction_timestamp", "timestamp_format": "yyyy-MM-dd HH:mm:ss"},
                "function": "is_valid_timestamp",
            },
            "criticality": "error",
        },
        {
            "check": {"arguments": {"column": "interaction_timestamp", "offset": "1h"}, "function": "not_in_future"},
            "criticality": "warning",
        },
        {"check": {"arguments": {"column": "item_id"}, "function": "is_not_null"}, "criticality": "minor"},
        {
            "check": {
                "arguments": {"column": "interaction_value", "max_limit": 1000, "min_limit": 0},
                "function": "is_in_range",
            },
            "criticality": "minor",
        },
        {
            "check": {
                "arguments": {"column": "location", "regex": "^[A-Za-z]+(?:[\\s-][A-Za-z]+)*$"},
                "function": "regex_match",
            },
            "criticality": "minor",
        },
        {
            "check": {
                "arguments": {"allowed": ["mobile", "desktop", "tablet"], "column": "device"},
                "function": "is_in_list",
            },
            "criticality": "minor",
        },
        {
            "check": {
                "arguments": {"column": "interaction_date", "date_format": "yyyy-MM-dd"},
                "function": "is_valid_date",
            },
            "criticality": "error",
        },
        {
            "check": {
                "arguments": {"column": "time_since_last_interaction", "days": 30},
                "function": "is_older_than_n_days",
            },
            "criticality": "minor",
        },
        {
            "check": {
                "arguments": {"column": "is_active", "expression": "is_active IN ('true', 'false')"},
                "function": "sql_expression",
            },
            "criticality": "minor",
        },
        {
            "check": {
                "arguments": {"column": "user_profile.age", "max_limit": 120, "min_limit": 13},
                "function": "is_in_range",
            },
            "criticality": "minor",
        },
        {
            "check": {
                "arguments": {"allowed": ["male", "female", "other"], "column": "user_profile.gender"},
                "function": "is_in_list",
            },
            "criticality": "minor",
        },
        {
            "check": {
                "arguments": {"column": "user_profile.location_details.country", "regex": "^[A-Z]{2}$"},
                "function": "regex_match",
            },
            "criticality": "minor",
        },
        {
            "check": {"arguments": {"column": "related_items"}, "function": "is_not_null_and_not_empty_array"},
            "criticality": "minor",
        },
        {
            "check": {
                "arguments": {"column": "interaction_context.page_url", "regex": "^https?://.+$"},
                "function": "regex_match",
            },
            "criticality": "minor",
        },
        {
            "check": {
                "arguments": {
                    "allowed": ["mobile", "desktop", "tablet", "tv"],
                    "column": "interaction_context.device_type",
                },
                "function": "is_in_list",
            },
            "criticality": "minor",
        },
        {
            "check": {
                "for_each_column": ["user_id", "interaction_id", "interaction_type", "interaction_timestamp"],
                "function": "is_not_null",
            },
            "criticality": "error",
            "filter": "interaction_type IN ('click', 'view', 'purchase')",
        },
        {
            "check": {
                "arguments": {"column": "interaction_value", "max_limit": 1000, "min_limit": 0},
                "function": "is_in_range",
            },
            "criticality": "warning",
            "filter": "interaction_type = 'purchase'",
        },
        {
            "check": {"arguments": {"allowed": ["mobile", "tablet"], "column": "device"}, "function": "is_in_list"},
            "criticality": "minor",
            "filter": "device = 'mobile'",
        },
        {
            "check": {
                "arguments": {"column": "user_profile.age", "max_limit": 120, "min_limit": 13},
                "function": "is_in_range",
            },
            "criticality": "minor",
            "filter": "user_profile.age IS NOT NULL",
        },
        {
            "check": {"arguments": {"columns": ["user_id", "interaction_date"]}, "function": "is_unique"},
            "criticality": "error",
        },
        {
            "check": {
                "arguments": {"aggr_type": "max", "column": "interaction_value", "limit": 1000},
                "function": "is_aggr_not_greater_than",
            },
            "criticality": "error",
            "filter": "interaction_type = 'purchase'",
        },
        {
            "check": {
                "arguments": {"aggr_type": "min", "column": "user_profile.age", "group_by": ["user_id"], "limit": 21},
                "function": "is_aggr_not_less_than",
            },
            "criticality": "error",
        },
        {
            "check": {
                "arguments": {"aggr_type": "count", "column": "interaction_date", "limit": 24},
                "function": "is_aggr_equal",
            },
            "criticality": "error",
        },
        {
            "check": {
                "arguments": {"columns": ["user_id"], "ref_columns": ["id"], "ref_df_name": "df_user"},
                "function": "foreign_key",
            },
            "criticality": "error",
        },
        {
            "check": {
                "arguments": {"columns": ["user_id"], "ref_columns": ["id"], "ref_table": "catalog1.schema1.user"},
                "function": "foreign_key",
            },
            "criticality": "error",
        },
    ]
    assert yaml.safe_load(actual) == expected_rules


def test_extract_none_from_datacontract_without_quality():
    actual = DataContract(data_contract_file="fixtures/dqx/datacontract_missing_quality.odcs.yaml").export("dqx")

    # Expected quality rules (based on the data contract)
    expected_rules = []

    assert yaml.safe_load(actual) == expected_rules
