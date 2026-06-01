import logging

import pytest
import yaml
from open_data_contract_standard.model import (
    DataQuality,
    OpenDataContractStandard,
    SchemaObject,
    SchemaProperty,
    Server,
    ServiceLevelAgreementProperty,
)

from datacontract.data_contract import DataContract
from datacontract.engines.data_contract_checks import (
    QuotingConfig,
    _escape_sql_string_values,
    check_property_enum,
    check_property_invalid_values,
    check_property_is_present,
    check_property_missing_values,
    check_property_not_equal,
    check_property_null_values,
    check_property_required,
    check_property_type,
    check_property_unique,
    check_row_count,
    create_checks,
    prepare_query,
    to_schema_checks,
    to_sla_freshness_check,
    to_sodacl_threshold,
)


def test_prepare_query_schema_placeholder():
    """Test that {schema} placeholder is replaced with server schema."""
    quality = DataQuality(type="sql", query="SELECT * FROM {schema}.{model}")
    server = Server(**{"type": "postgres", "schema": "my_schema"})

    result = prepare_query(quality, "my_table", None, QuotingConfig(), server)

    assert result == "SELECT * FROM my_schema.my_table"


def test_prepare_query_schema_placeholder_quoted():
    """Test that {schema} placeholder is quoted for postgres/sqlserver."""
    quality = DataQuality(type="sql", query="SELECT * FROM {schema}.{model}")
    server = Server(**{"type": "postgres", "schema": "my_schema"})
    quoting_config = QuotingConfig(quote_model_name=True)

    result = prepare_query(quality, "my_table", None, quoting_config, server)

    assert result == 'SELECT * FROM "my_schema"."my_table"'


def test_prepare_query_schema_placeholder_backticks():
    """Test that {schema} placeholder uses backticks for bigquery."""
    quality = DataQuality(type="sql", query="SELECT * FROM {schema}.{model}")
    server = Server(**{"type": "bigquery", "schema": "my_dataset"})
    quoting_config = QuotingConfig(quote_model_name_with_backticks=True)

    result = prepare_query(quality, "my_table", None, quoting_config, server)

    assert result == "SELECT * FROM `my_dataset`.`my_table`"


def test_prepare_query_schema_placeholder_no_server():
    """Test that {schema} falls back to model name when server is None."""
    quality = DataQuality(type="sql", query="SELECT * FROM {schema}")

    result = prepare_query(quality, "my_table", None, QuotingConfig(), None)

    assert result == "SELECT * FROM my_table"


def test_prepare_query_schema_placeholder_no_schema():
    """Test that {schema} falls back to model name when server has no schema."""
    quality = DataQuality(type="sql", query="SELECT * FROM {schema}")
    server = Server(type="postgres")

    result = prepare_query(quality, "my_table", None, QuotingConfig(), server)

    assert result == "SELECT * FROM my_table"


def test_prepare_query_schema_placeholder_with_dollar():
    """Test that ${schema} placeholder (with $) is replaced with server schema."""
    quality = DataQuality(type="sql", query="SELECT * FROM ${schema}.${model}")
    server = Server(**{"type": "postgres", "schema": "my_schema"})

    result = prepare_query(quality, "my_table", None, QuotingConfig(), server)

    assert result == "SELECT * FROM my_schema.my_table"


def test_prepare_query_all_placeholders_with_dollar():
    """Test that all placeholders work with $ prefix."""
    quality = DataQuality(type="sql", query="SELECT ${column} FROM ${schema}.${table}")
    server = Server(**{"type": "postgres", "schema": "my_schema"})

    result = prepare_query(quality, "my_table", "my_field", QuotingConfig(), server)

    assert result == "SELECT my_field FROM my_schema.my_table"


def test_prepare_query_object_placeholder():
    """Test that {object} and ${object} placeholders are replaced with the model name (ODCS spec terminology)."""
    quality = DataQuality(type="sql", query="SELECT COUNT(*) FROM {object} WHERE ${object} IS NOT NULL")

    result = prepare_query(quality, "my_table", None, QuotingConfig(), None)

    assert result == "SELECT COUNT(*) FROM my_table WHERE my_table IS NOT NULL"


def test_prepare_query_object_and_property_placeholders():
    """Test the canonical ODCS-spec example: SELECT COUNT(*) FROM {object} WHERE {property} IS NOT NULL."""
    quality = DataQuality(type="sql", query="SELECT COUNT(*) FROM {object} WHERE {property} IS NOT NULL")

    result = prepare_query(quality, "my_table", "my_field", QuotingConfig(), None)

    assert result == "SELECT COUNT(*) FROM my_table WHERE my_field IS NOT NULL"


def test_prepare_query_field_backtick_quoting():
    """Test that field placeholders use backticks for databricks."""
    quality = DataQuality(type="sql", query="SELECT {field} FROM {model}")
    quoting_config = QuotingConfig(quote_field_name_with_backticks=True)

    result = prepare_query(quality, "my_table", "loc/dep", quoting_config, None)

    assert result == "SELECT `loc/dep` FROM my_table"


def test_check_property_required_backtick_quoting():
    """Test that field names with special chars are backtick-quoted for databricks."""
    quoting_config = QuotingConfig(quote_field_name_with_backticks=True)

    check = check_property_required("my_table", "loc/dep", quoting_config)

    impl = yaml.safe_load(check.implementation)
    checks = impl["checks for my_table"]
    assert any("missing_count(`loc/dep`) = 0" in str(c) for c in checks)


def test_check_property_unique_backtick_quoting():
    """Test that field names with special chars are backtick-quoted for unique checks."""
    quoting_config = QuotingConfig(quote_field_name_with_backticks=True)

    check = check_property_unique("my_table", "loc/dep", quoting_config)

    impl = yaml.safe_load(check.implementation)
    checks = impl["checks for my_table"]
    assert any("duplicate_count(`loc/dep`) = 0" in str(c) for c in checks)


def test_check_property_is_present_no_backtick_quoting():
    """Test that field_is_present schema checks do not backtick-quote field names.

    Schema checks use metadata comparison, not SQL identifiers.
    """
    quoting_config = QuotingConfig(quote_field_name_with_backticks=True)

    check = check_property_is_present("my_table", "loc/dep", quoting_config)

    impl = yaml.safe_load(check.implementation)
    checks = impl["checks for my_table"]
    schema_check = checks[0]["schema"]
    assert schema_check["fail"]["when required column missing"] == ["loc/dep"]


def test_check_property_type_no_backtick_quoting():
    """Test that field_type schema checks do not backtick-quote field names.

    Schema checks use metadata comparison, not SQL identifiers.
    """
    quoting_config = QuotingConfig(quote_field_name_with_backticks=True)

    check = check_property_type("my_table", "loc/dep", "string", quoting_config)

    impl = yaml.safe_load(check.implementation)
    checks = impl["checks for my_table"]
    schema_check = checks[0]["schema"]
    assert schema_check["fail"]["when wrong column type"] == {"loc/dep": "string"}


def test_prepare_query_snowflake_field_quoting():
    """Test that field placeholders use double quotes for snowflake."""
    quality = DataQuality(type="sql", query="SELECT {field} FROM {model}")
    quoting_config = QuotingConfig(quote_model_name=True)
    server = Server(**{"type": "snowflake", "schema": "my_schema"})

    result = prepare_query(quality, "my_table", "name", quoting_config, server)

    assert result == 'SELECT name FROM "my_table"'


def test_prepare_query_snowflake_schema_model_quoting():
    """Test that schema and model placeholders use double quotes for snowflake."""
    quality = DataQuality(type="sql", query="SELECT * FROM {schema}.{model}")
    quoting_config = QuotingConfig(quote_field_name=True, quote_model_name=True)
    server = Server(**{"type": "snowflake", "schema": "my_schema"})

    result = prepare_query(quality, "my_table", None, quoting_config, server)

    assert result == 'SELECT * FROM "my_schema"."my_table"'


def test_check_property_required_snowflake_quoting():
    """Test that field names are double-quoted for snowflake required checks."""
    quoting_config = QuotingConfig(quote_field_name=True, quote_model_name=True)

    check = check_property_required("my_table", "name", quoting_config)

    impl = yaml.safe_load(check.implementation)
    checks = impl['checks for "my_table"']
    assert any('missing_count("name") = 0' in str(c) for c in checks)


def test_check_property_unique_snowflake_quoting():
    """Test that field names are double-quoted for snowflake unique checks."""
    quoting_config = QuotingConfig(quote_field_name=True, quote_model_name=True)

    check = check_property_unique("my_table", "name", quoting_config)

    impl = yaml.safe_load(check.implementation)
    checks = impl['checks for "my_table"']
    assert any('duplicate_count("name") = 0' in str(c) for c in checks)


def test_check_property_is_present_no_snowflake_quoting():
    """Test that field_is_present schema checks do not double-quote field names for snowflake.

    Schema checks use metadata comparison, not SQL identifiers.
    """
    quoting_config = QuotingConfig(quote_field_name=True, quote_model_name=True)

    check = check_property_is_present("my_table", "name", quoting_config)

    impl = yaml.safe_load(check.implementation)
    checks = impl['checks for "my_table"']
    schema_check = checks[0]["schema"]
    assert schema_check["fail"]["when required column missing"] == ["name"]


def test_check_property_required_duckdb_hyphenated_model_name():
    """Test that model names with hyphens are double-quoted in required checks for DuckDB-backed sources (s3/gcs/azure/local)."""
    quoting_config = QuotingConfig(quote_model_name=True)
    check = check_property_required("test-1", "name", quoting_config)
    impl = yaml.safe_load(check.implementation)
    checks = impl['checks for "test-1"']
    assert any("missing_count(name) = 0" in str(c) for c in checks)


def test_check_property_is_present_duckdb_hyphenated_model_name():
    """Test that model names with hyphens are double-quoted for DuckDB-backed sources (s3/gcs/azure/local)."""
    quoting_config = QuotingConfig(quote_model_name=True)
    check = check_property_is_present("test-1", "name", quoting_config)
    impl = yaml.safe_load(check.implementation)
    checks = impl['checks for "test-1"']
    schema_check = checks[0]["schema"]
    assert schema_check["fail"]["when required column missing"] == ["name"]


def _make_multi_schema_contract() -> OpenDataContractStandard:
    """Create a data contract with two schemas for testing schema_name filtering."""
    return OpenDataContractStandard(
        **{
            "apiVersion": "v3.1.0",
            "kind": "DataContract",
            "id": "test-schema-filter",
            "name": "Test Schema Filter",
            "version": "1.0.0",
            "status": "active",
            "schema": [
                {
                    "name": "orders",
                    "properties": [
                        {"name": "order_id", "logicalType": "string", "physicalType": "string", "required": True},
                        {"name": "amount", "logicalType": "integer", "physicalType": "integer"},
                    ],
                },
                {
                    "name": "line_items",
                    "properties": [
                        {"name": "line_item_id", "logicalType": "string", "physicalType": "string", "required": True},
                        {"name": "order_id", "logicalType": "string", "physicalType": "string"},
                    ],
                },
            ],
        }
    )


def test_create_checks_schema_name_all():
    """Test that schema_name='all' returns checks for all schemas."""
    contract = _make_multi_schema_contract()
    server = Server(type="postgres")

    checks = create_checks(contract, server, schema_name="all")

    models_in_checks = {c.model for c in checks if c.model is not None}
    assert "orders" in models_in_checks
    assert "line_items" in models_in_checks


def test_create_checks_schema_name_default():
    """Test that omitting schema_name returns checks for all schemas (default is 'all')."""
    contract = _make_multi_schema_contract()
    server = Server(type="postgres")

    checks = create_checks(contract, server)

    models_in_checks = {c.model for c in checks if c.model is not None}
    assert "orders" in models_in_checks
    assert "line_items" in models_in_checks


def test_create_checks_schema_name_filter_orders():
    """Test that schema_name='orders' returns only checks for the orders schema."""
    contract = _make_multi_schema_contract()
    server = Server(type="postgres")

    checks = create_checks(contract, server, schema_name="orders")

    models_in_checks = {c.model for c in checks if c.model is not None}
    assert "orders" in models_in_checks
    assert "line_items" not in models_in_checks


def test_create_checks_schema_name_filter_line_items():
    """Test that schema_name='line_items' returns only checks for the line_items schema."""
    contract = _make_multi_schema_contract()
    server = Server(type="postgres")

    checks = create_checks(contract, server, schema_name="line_items")

    models_in_checks = {c.model for c in checks if c.model is not None}
    assert "line_items" in models_in_checks
    assert "orders" not in models_in_checks


def test_create_checks_schema_name_nonexistent():
    """Test that a non-existent schema_name returns no schema checks (only servicelevel)."""
    contract = _make_multi_schema_contract()
    server = Server(type="postgres")

    checks = create_checks(contract, server, schema_name="nonexistent")

    models_in_checks = {c.model for c in checks if c.model is not None}
    assert "orders" not in models_in_checks
    assert "line_items" not in models_in_checks


def test_field_and_model_names_have_backticks_in_quality_bigquery():
    """Test that field and model names are encapsulated with backticks for BigQuery servers in quality checks"""
    data_contract = DataContract(data_contract_file="fixtures/bigquery/datacontract_with_quality_rules.odcs.yaml")
    checks = to_schema_checks(
        schema_object=data_contract.get_data_contract().schema_[0],
        server=Server(type="bigquery"),
    )
    quality_check = [check for check in checks if check.category == "quality"][0]
    impl = yaml.safe_load(quality_check.implementation)
    checks = impl["checks for `test_table`"]
    check_name = checks[0]["duplicate_count(`field_with_quality_rules`) = 0"]["name"]
    assert "test_table__field_with_quality_rules__field_duplicate_values" == check_name


def test_prepare_query_schema_placeholder_backticks_databricks():
    """Test that {schema} and {model} placeholders use backticks for databricks."""
    quality = DataQuality(type="sql", query="SELECT * FROM {schema}.{model}")
    server = Server(**{"type": "databricks", "schema": "my_schema"})
    quoting_config = QuotingConfig(quote_model_name_with_backticks=True)

    result = prepare_query(quality, "my_table", None, quoting_config, server)

    assert result == "SELECT * FROM `my_schema`.`my_table`"


def test_field_and_model_names_have_backticks_in_quality_databricks():
    """Test that field and model names are encapsulated with backticks for Databricks servers in quality checks."""
    data_contract = DataContract(data_contract_file="fixtures/bigquery/datacontract_with_quality_rules.odcs.yaml")
    checks = to_schema_checks(
        schema_object=data_contract.get_data_contract().schema_[0],
        server=Server(type="databricks"),
    )
    quality_check = [check for check in checks if check.category == "quality"][0]
    impl = yaml.safe_load(quality_check.implementation)
    checks = impl["checks for `test_table`"]
    check_name = checks[0]["duplicate_count(`field_with_quality_rules`) = 0"]["name"]
    assert "test_table__field_with_quality_rules__field_duplicate_values" == check_name


# --- Tests for single-quote escaping in SodaCL checks (issue #980) ---


def test_escape_sql_string_values_plain():
    """Values without quotes are returned unchanged."""
    assert _escape_sql_string_values(["active", "inactive"]) == ["active", "inactive"]


def test_escape_sql_string_values_single_quote():
    """Single quotes inside string values are doubled for SQL safety."""
    assert _escape_sql_string_values(["peter's", "normal"]) == ["peter''s", "normal"]


def test_escape_sql_string_values_multiple_quotes():
    """Multiple single quotes are all escaped."""
    assert _escape_sql_string_values(["it's a dog's life"]) == ["it''s a dog''s life"]


def test_escape_sql_string_values_non_string_passthrough():
    """Non-string values (int, None) are left untouched."""
    assert _escape_sql_string_values([42, None, "ok"]) == [42, None, "ok"]


def test_escape_sql_string_values_none_input():
    """None input returns None."""
    assert _escape_sql_string_values(None) is None


def test_check_property_invalid_values_escapes_single_quotes():
    """check_property_invalid_values escapes single quotes in valid_values for SodaCL."""
    check = check_property_invalid_values(
        model_name="orders",
        field_name="status",
        threshold="= 0",
        valid_values=["peter's", "normal"],
    )
    impl = yaml.safe_load(check.implementation)
    checks = impl["checks for orders"]
    check_config = checks[0]["invalid_count(status) = 0"]
    assert "peter''s" in check_config["valid values"]
    assert "normal" in check_config["valid values"]


def test_check_property_enum_escapes_single_quotes():
    """check_property_enum escapes single quotes in enum values for SodaCL."""
    check = check_property_enum(
        model_name="orders",
        field_name="status",
        enum=["it's fine", "ok"],
    )
    impl = yaml.safe_load(check.implementation)
    checks = impl["checks for orders"]
    check_config = checks[0]["invalid_count(status) = 0"]
    assert "it''s fine" in check_config["valid values"]
    assert "ok" in check_config["valid values"]


def test_check_property_not_equal_escapes_single_quotes():
    """check_property_not_equal escapes single quotes in the invalid value for SodaCL."""
    check = check_property_not_equal(
        model_name="orders",
        field_name="status",
        value="peter's",
    )
    impl = yaml.safe_load(check.implementation)
    checks = impl["checks for orders"]
    check_config = checks[0]["invalid_count(status) = 0"]
    assert "peter''s" in check_config["invalid values"]


def test_check_property_missing_values_escapes_single_quotes():
    """check_property_missing_values escapes single quotes in missing_values for SodaCL."""
    check = check_property_missing_values(
        model_name="orders",
        field_name="status",
        threshold="= 0",
        missing_values=["n/a", "peter's"],
    )
    impl = yaml.safe_load(check.implementation)
    checks = impl["checks for orders"]
    check_config = checks[0]["missing_count(status) = 0"]
    assert "peter''s" in check_config["missing values"]
    assert "n/a" in check_config["missing values"]


def _freshness_contract(model_name: str = "events"):
    return OpenDataContractStandard(
        kind="DataContract",
        apiVersion="v3.1.0",
        id="freshness-test",
        schema=[
            SchemaObject(
                name=model_name,
                properties=[SchemaProperty(name="ts", logicalType="timestamp")],
            )
        ],
    )


def _freshness_sla(element: str):
    return ServiceLevelAgreementProperty(property="freshness", element=element, value=24, unit="h")


def test_freshness_check_quotes_dollar_field_on_athena():
    """Athena pseudo-columns like $file_modified_time must be ANSI-quoted to parse."""
    contract = _freshness_contract("events")
    sla = _freshness_sla("events.$file_modified_time")
    server = Server(type="athena")

    check = to_sla_freshness_check(contract, sla, server)

    impl = yaml.safe_load(check.implementation)
    keys = list(impl["checks for events"][0].keys())
    assert keys == ['freshness("$file_modified_time") < 24h']


def test_freshness_check_leaves_dollar_field_bare_on_postgres():
    """Postgres allows `$` as a continuation char in bare identifiers; quoting it would
    force avoidable case-sensitivity on a case-folding dialect."""
    contract = _freshness_contract("orders")
    sla = _freshness_sla("orders.col$ext")
    server = Server(type="postgres")

    check = to_sla_freshness_check(contract, sla, server)

    impl = yaml.safe_load(check.implementation)
    keys = list(impl["checks for orders"][0].keys())
    assert keys == ["freshness(col$ext) < 24h"]


def test_freshness_check_backticks_special_field_on_databricks():
    """Backtick dialects (Databricks/Spark) reject `$` bare and need backtick-quoting."""
    contract = _freshness_contract("events")
    sla = _freshness_sla("events.$file_modified_time")
    server = Server(type="databricks")

    check = to_sla_freshness_check(contract, sla, server)

    impl = yaml.safe_load(check.implementation)
    keys = list(impl["checks for events"][0].keys())
    assert keys == ["freshness(`$file_modified_time`) < 24h"]


# --- Field-level physicalName resolution (ODCS) ---


def test_field_checks_use_physical_name_when_set():
    """When a property declares a physicalName, field checks must target it.

    physicalName is the actual column name in the system under test. The
    table level already prefers physicalName (to_schema_name); the field
    level must do the same, otherwise a contract with a logical name like
    `brand` and physicalName `BRAND` fails "required column missing" even
    though the BRAND column exists.
    """
    schema_object = SchemaObject(
        name="orders",
        properties=[SchemaProperty(name="brand", physicalName="BRAND", logicalType="string")],
    )

    checks = to_schema_checks(schema_object=schema_object, server=Server(type="snowflake"))

    present = next(c for c in checks if c.type == "field_is_present")
    assert present.field == "BRAND"
    # Key is "checks for <model>" (model name may be quoted per dialect) — read
    # it positionally rather than hardcoding the dialect-specific spelling.
    impl = yaml.safe_load(present.implementation)
    (sodacl_checks,) = impl.values()
    assert sodacl_checks[0]["schema"]["fail"]["when required column missing"] == ["BRAND"]

    type_check = next(c for c in checks if c.type == "field_type")
    assert type_check.field == "BRAND"


def test_field_checks_fall_back_to_name_without_physical_name():
    """Without physicalName, field checks use the logical name (unchanged)."""
    schema_object = SchemaObject(
        name="orders",
        properties=[SchemaProperty(name="sku", logicalType="string")],
    )

    checks = to_schema_checks(schema_object=schema_object, server=Server(type="snowflake"))

    present = next(c for c in checks if c.type == "field_is_present")
    assert present.field == "sku"


# ---------------------------------------------------------------------------
# Databricks varchar/map type-check skip (#1245, #1219)
# ---------------------------------------------------------------------------


def test_to_schema_checks_non_databricks_varchar_still_produces_type_check():
    """Non-Databricks server with varchar physicalType still emits a field_type check."""
    schema_object = SchemaObject(
        name="orders",
        properties=[SchemaProperty(name="name", physicalType="varchar(30)")],
    )
    server = Server(type="snowflake")

    checks = to_schema_checks(schema_object=schema_object, server=server)

    types = [c.type for c in checks]
    assert "field_type" in types


def test_to_schema_checks_databricks_struct_with_nested_varchar_skips_type_check():
    """Databricks struct column whose nested property has varchar physicalType skips type check.

    The parent physicalType (struct<varchar_field:string>) does not itself contain
    varchar as a type token, but the nested property does — so the parent check
    must be skipped too (issue #1245).
    """
    nested = SchemaProperty(name="varchar_field", physicalType="varchar(100)")
    schema_object = SchemaObject(
        name="complex_datatypes",
        properties=[
            SchemaProperty(
                name="struct_with_varchar_test",
                physicalType="struct<varchar_field:string>",
                properties=[nested],
            )
        ],
    )
    server = Server(type="databricks")

    checks = to_schema_checks(schema_object=schema_object, server=server)

    types = [c.type for c in checks]
    assert "field_is_present" in types
    assert "field_type" not in types


# --- Tests for to_sodacl_threshold function ---


@pytest.mark.parametrize(
    "unit,quality_kwargs,expected",
    [
        # Test percent unit appends %
        ("percent", {"mustBe": 5}, "= 5%"),
        ("percent", {"mustBeGreaterThan": 10}, "> 10%"),
        ("percent", {"mustBeGreaterOrEqualTo": 10}, ">= 10%"),
        ("percent", {"mustBeLessThan": 20}, "< 20%"),
        ("percent", {"mustBeLessOrEqualTo": 30}, "<= 30%"),
        ("percent", {"mustNotBe": 0}, "!= 0%"),
        ("percent", {"mustBeBetween": [5, 15]}, "between 5% and 15%"),
        ("percent", {"mustNotBeBetween": [80, 100]}, "not between 80% and 100%"),
        # Test case insensitivity
        ("PERCENT", {"mustBeLessThan": 10}, "< 10%"),
        ("Percent", {"mustBe": 15}, "= 15%"),
        # Test rows unit does not append %
        ("rows", {"mustBe": 100}, "= 100"),
        ("rows", {"mustBeGreaterThan": 50}, "> 50"),
        # Test default (None) does not append %
        (None, {"mustBe": 50}, "= 50"),
        (None, {"mustBeLessThan": 75}, "< 75"),
    ],
)
def test_to_sodacl_threshold_with_units(unit, quality_kwargs, expected):
    """Test that to_sodacl_threshold correctly handles different units and operators."""
    quality = DataQuality(unit=unit, **quality_kwargs)
    result = to_sodacl_threshold(quality)
    assert result == expected


def test_to_sodacl_threshold_invalid_unit(caplog):
    """Test that invalid unit returns None and raises a warning."""
    quality = DataQuality(unit="invalid", mustBe=5)
    with caplog.at_level(logging.WARNING):
        result = to_sodacl_threshold(quality)

    assert result is None
    assert "Unsupported quality.unit" in caplog.text


# --- Tests for unit handling in check_* functions ---


@pytest.mark.parametrize(
    "threshold,expected_metric,expected_check",
    [
        ("< 5%", "missing_percent", "missing_percent(status) < 5%"),
        ("< 10", "missing_count", "missing_count(status) < 10"),
    ],
)
def test_check_property_null_values_metric_selection(threshold, expected_metric, expected_check):
    """Test that check_property_null_values selects correct metric based on threshold."""
    check = check_property_null_values("orders", "status", threshold)

    assert check.model == "orders"
    assert check.field == "status"
    assert check.type == "field_null_values"
    assert expected_metric in check.name

    impl = yaml.safe_load(check.implementation)
    checks = impl["checks for orders"]
    check_keys = list(checks[0].keys())
    assert check_keys == [expected_check]


@pytest.mark.parametrize(
    "threshold,expected_metric,expected_check",
    [
        ("= 0%", "invalid_percent", "invalid_percent(status) = 0%"),
        ("= 0", "invalid_count", "invalid_count(status) = 0"),
    ],
)
def test_check_property_invalid_values_metric_selection(threshold, expected_metric, expected_check):
    """Test that check_property_invalid_values selects correct metric based on threshold."""
    check = check_property_invalid_values("orders", "status", threshold, valid_values=["active", "inactive"])

    assert check.model == "orders"
    assert check.field == "status"
    assert check.type == "field_invalid_values"
    assert expected_metric in check.name

    impl = yaml.safe_load(check.implementation)
    checks = impl["checks for orders"]
    check_keys = list(checks[0].keys())
    assert check_keys == [expected_check]


@pytest.mark.parametrize(
    "threshold,expected_metric,expected_check",
    [
        ("<= 2%", "missing_percent", "missing_percent(status) <= 2%"),
        ("<= 5", "missing_count", "missing_count(status) <= 5"),
    ],
)
def test_check_property_missing_values_metric_selection(threshold, expected_metric, expected_check):
    """Test that check_property_missing_values selects correct metric based on threshold."""
    check = check_property_missing_values("orders", "status", threshold, missing_values=["n/a", "null"])

    assert check.model == "orders"
    assert check.field == "status"
    assert check.type == "field_missing_values"
    assert expected_metric in check.name

    impl = yaml.safe_load(check.implementation)
    checks = impl["checks for orders"]
    check_keys = list(checks[0].keys())
    assert check_keys == [expected_check]


@pytest.mark.parametrize(
    "threshold",
    [
        "> 100%",
        "between 10% and 50%",
    ],
)
def test_check_row_count_with_percent_returns_none(threshold, caplog):
    """Test that check_row_count returns None when threshold contains '%'."""
    with caplog.at_level(logging.WARNING):
        result = check_row_count("orders", threshold, QuotingConfig())
    assert result is None
    assert "Row count threshold cannot be specified as a percentage." in caplog.text


def test_check_row_count_without_percent_works():
    """Test that check_row_count works normally without '%'."""
    check = check_row_count("orders", "> 1000", QuotingConfig())

    assert check is not None
    assert check.model == "orders"
    assert check.type == "row_count"

    # Parse the implementation to verify the SodaCL check
    impl = yaml.safe_load(check.implementation)
    checks = impl["checks for orders"]
    check_keys = list(checks[0].keys())
    assert check_keys == ["row_count > 1000"]
