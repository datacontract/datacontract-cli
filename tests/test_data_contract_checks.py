from datacontract.engines.data_contract_checks import period_to_seconds, prepare_query, QuotingConfig
from datacontract.model.data_contract_specification import Quality, Server


def test_prepare_query_schema_placeholder():
    """Test that {schema} placeholder is replaced with server schema."""
    quality = Quality(type="sql", query="SELECT * FROM {schema}.{model}")
    server = Server(**{"type": "postgres", "schema": "my_schema"})

    result = prepare_query(quality, "my_table", None, QuotingConfig(), server)

    assert result == "SELECT * FROM my_schema.my_table"


def test_prepare_query_schema_placeholder_quoted():
    """Test that {schema} placeholder is quoted for postgres/sqlserver."""
    quality = Quality(type="sql", query="SELECT * FROM {schema}.{model}")
    server = Server(**{"type": "postgres", "schema": "my_schema"})
    quoting_config = QuotingConfig(quote_model_name=True)

    result = prepare_query(quality, "my_table", None, quoting_config, server)

    assert result == 'SELECT * FROM "my_schema"."my_table"'


def test_prepare_query_schema_placeholder_backticks():
    """Test that {schema} placeholder uses backticks for bigquery."""
    quality = Quality(type="sql", query="SELECT * FROM {schema}.{model}")
    server = Server(**{"type": "bigquery", "schema": "my_dataset"})
    quoting_config = QuotingConfig(quote_model_name_with_backticks=True)

    result = prepare_query(quality, "my_table", None, quoting_config, server)

    assert result == "SELECT * FROM `my_dataset`.`my_table`"


def test_prepare_query_schema_placeholder_no_server():
    """Test that {schema} falls back to model name when server is None."""
    quality = Quality(type="sql", query="SELECT * FROM {schema}")

    result = prepare_query(quality, "my_table", None, QuotingConfig(), None)

    assert result == "SELECT * FROM my_table"


def test_prepare_query_schema_placeholder_no_schema():
    """Test that {schema} falls back to model name when server has no schema."""
    quality = Quality(type="sql", query="SELECT * FROM {schema}")
    server = Server(type="postgres")

    result = prepare_query(quality, "my_table", None, QuotingConfig(), server)

    assert result == "SELECT * FROM my_table"


def test_prepare_query_schema_placeholder_with_dollar():
    """Test that ${schema} placeholder (with $) is replaced with server schema."""
    quality = Quality(type="sql", query="SELECT * FROM ${schema}.${model}")
    server = Server(**{"type": "postgres", "schema": "my_schema"})

    result = prepare_query(quality, "my_table", None, QuotingConfig(), server)

    assert result == "SELECT * FROM my_schema.my_table"


def test_prepare_query_all_placeholders_with_dollar():
    """Test that all placeholders work with $ prefix."""
    quality = Quality(type="sql", query="SELECT ${field} FROM ${schema}.${table}")
    server = Server(**{"type": "postgres", "schema": "my_schema"})

    result = prepare_query(quality, "my_table", "my_field", QuotingConfig(), server)

    assert result == "SELECT my_field FROM my_schema.my_table"


def test_period_to_seconds():
    assert period_to_seconds("P1Y") == 31536000
    assert period_to_seconds("P1D") == 86400
    assert period_to_seconds("PT24H") == 86400
    assert period_to_seconds("1d") == 86400
    assert period_to_seconds("24h") == 86400
    assert period_to_seconds("60m") == 3600
