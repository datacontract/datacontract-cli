from datacontract.engines.checks.physical_type_match import physical_type_matches
from datacontract.engines.ibis.native_type import (
    _rows,
    reconstruct_native_type,
    supports_native_type_introspection,
)


# --- physical_type_matches -------------------------------------------------
def test_uniqueidentifier_matches_on_sqlserver():
    ok, reason = physical_type_matches("uniqueidentifier", "uniqueidentifier", "tsql")
    assert ok is True
    assert reason == ""


def test_case_insensitive():
    ok, _ = physical_type_matches("UNIQUEIDENTIFIER", "uniqueidentifier", "tsql")
    assert ok is True


def test_dialect_aliases_match():
    # int ≡ integer, decimal ≡ numeric
    assert physical_type_matches("int", "integer", "postgres")[0] is True
    assert physical_type_matches("decimal(10,2)", "numeric(10,2)", "postgres")[0] is True


def test_length_enforced_only_when_declared():
    # Contract declares a length -> must match.
    ok, reason = physical_type_matches("varchar(255)", "varchar(100)", "tsql")
    assert ok is False
    assert "varchar(255)" in reason and "varchar(100)" in reason
    # Contract omits the length -> any length matches.
    assert physical_type_matches("varchar", "varchar(255)", "tsql")[0] is True


def test_timestamp_matches_timestamptz():
    # A declared timestamp is compatible with a timestamptz column (timezone
    # variance is not distinguished at the level most contracts are written at).
    assert physical_type_matches("timestamp", "timestamp with time zone", "postgres")[0] is True
    assert physical_type_matches("timestamp", "timestamptz", "postgres")[0] is True


def test_distinct_native_types_do_not_match():
    # varchar and nvarchar are genuinely different native types.
    ok, _ = physical_type_matches("varchar(255)", "nvarchar(255)", "tsql")
    assert ok is False


def test_wrong_base_type_fails():
    ok, reason = physical_type_matches("uniqueidentifier", "int", "tsql")
    assert ok is False
    assert "uniqueidentifier" in reason


def test_cross_dialect_physicaltype_is_skipped():
    # uniqueidentifier is not a Snowflake type -> cannot resolve -> skip (None).
    result, reason = physical_type_matches("uniqueidentifier", "varchar", "snowflake")
    assert result is None
    assert "snowflake" in reason.lower() or "not a valid type" in reason.lower()


def test_exotic_oracle_types_match_via_string_fallback():
    # sqlglot cannot parse these Oracle types; identical columns still match.
    assert physical_type_matches("ROWID", "ROWID", "oracle")[0] is True
    assert physical_type_matches("RAW", "RAW(2000)", "oracle")[0] is True
    assert physical_type_matches("INTERVAL DAY(2) TO SECOND(6)", "INTERVAL DAY(2) TO SECOND(6)", "oracle")[0] is True


def test_exotic_oracle_types_mismatch_when_different():
    # Both unparseable but genuinely different base types -> fail, not skip.
    assert physical_type_matches("ROWID", "UROWID", "oracle")[0] is False


def test_empty_expected_is_skipped():
    assert physical_type_matches("", "varchar", "tsql")[0] is None
    assert physical_type_matches(None, "varchar", "tsql")[0] is None


def test_bigquery_types_match():
    assert physical_type_matches("STRING", "STRING", "bigquery")[0] is True
    assert physical_type_matches("NUMERIC", "NUMERIC(10, 2)", "bigquery")[0] is True
    assert physical_type_matches("STRING", "INT64", "bigquery")[0] is False


def test_athena_types_match():
    assert physical_type_matches("varchar", "varchar(255)", "athena")[0] is True
    assert physical_type_matches("varchar(255)", "varchar(100)", "athena")[0] is False


# --- supports_native_type_introspection ------------------------------------
def test_supported_backends():
    for s in ["sqlserver", "postgres", "redshift", "snowflake", "databricks", "trino", "oracle", "athena", "bigquery"]:
        assert supports_native_type_introspection(s) is True


def test_unsupported_backends():
    for s in ["local", "s3", "mysql", "impala", "kafka", "dataframe", None]:
        assert supports_native_type_introspection(s) is False


# --- reconstruct_native_type ----------------------------------------------
def test_reconstruct_plain_type():
    assert reconstruct_native_type("uniqueidentifier") == "uniqueidentifier"


def test_reconstruct_with_char_length():
    assert reconstruct_native_type("varchar", char_len=255) == "varchar(255)"


def test_reconstruct_sqlserver_max_length():
    # SQL Server reports CHARACTER_MAXIMUM_LENGTH = -1 for varchar(max).
    assert reconstruct_native_type("varchar", char_len=-1) == "varchar(max)"


def test_reconstruct_decimal_precision_scale():
    assert reconstruct_native_type("decimal", num_precision=10, num_scale=2) == "decimal(10,2)"
    assert reconstruct_native_type("decimal", num_precision=10, num_scale=0) == "decimal(10)"


def test_reconstruct_integer_ignores_numeric_precision():
    # int reports numeric_precision 10, but int(10) is not a real declared type.
    assert reconstruct_native_type("int", num_precision=10, num_scale=0) == "int"


def test_reconstruct_none():
    assert reconstruct_native_type(None) is None


# --- _rows -----------------------------------------------------------------
class _SparkLikeDataFrame:
    """Iterating a Spark DataFrame yields Column objects, not rows; only
    ``collect()`` returns the rows."""

    def __iter__(self):
        raise AssertionError("must not iterate a Spark DataFrame")

    def collect(self):
        return [("postal_code", "string", None, None, None)]


class _SparkLikeConnection:
    def raw_sql(self, query):
        return _SparkLikeDataFrame()


def test_rows_collects_spark_dataframe():
    assert _rows(_SparkLikeConnection(), "select 1") == [("postal_code", "string", None, None, None)]
