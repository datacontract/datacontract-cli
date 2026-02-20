import yaml
from open_data_contract_standard.model import DataQuality, Server

from datacontract.engines.data_contract_checks import (
    QuotingConfig,
    check_property_is_present,
    check_property_required,
    check_property_type,
    check_property_unique,
    prepare_query,
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
    quoting_config = QuotingConfig(quote_field_name=True, quote_model_name=True)
    server = Server(**{"type": "snowflake", "schema": "my_schema"})

    result = prepare_query(quality, "my_table", "name", quoting_config, server)

    assert result == 'SELECT "name" FROM "my_table"'


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
