import yaml
from open_data_contract_standard.model import DataQuality, OpenDataContractStandard, Server

from datacontract.data_contract import DataContract
from datacontract.engines.data_contract_checks import (
    QuotingConfig,
    _escape_sql_string_values,
    check_property_enum,
    check_property_invalid_values,
    check_property_is_present,
    check_property_missing_values,
    check_property_not_equal,
    check_property_required,
    check_property_type,
    check_property_unique,
    create_checks,
    prepare_query,
    to_schema_checks,
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
