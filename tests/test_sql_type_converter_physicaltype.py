"""Tests for physicalType handling in sql_type_converter.

Validates the fix for https://github.com/datacontract/datacontract-cli/issues/1039:
- SchemaProperty.physicalType is now properly accessible in convert_to_sql_type()
- When only physicalType is set (no logicalType), it is used as a direct SQL type
  passthrough (e.g. user-specified native types like "TIMESTAMP(6)")
- When both are set, physicalType drives the server-specific type mapping
  (preserving precision like int vs long)
- Oracle converter uses physicalType directly for native Oracle types
- Server-specific type overrides via customProperties still work
"""

from open_data_contract_standard.model import CustomProperty, SchemaProperty

from datacontract.export.sql_type_converter import (
    convert_to_sql_type,
    convert_type_to_oracle,
)


class TestPhysicalTypeDirectPassthrough:
    """When only physicalType is set (no logicalType), it should be used
    as a direct SQL type passthrough."""

    def test_physical_type_only_passthrough(self):
        """physicalType without logicalType is treated as native SQL type."""
        prop = SchemaProperty(
            name="custom_field",
            physicalType="VARCHAR(255)",
        )
        assert convert_to_sql_type(prop, "snowflake") == "VARCHAR(255)"

    def test_physical_type_only_complex_type(self):
        """Complex native SQL types should be passed through as-is."""
        prop = SchemaProperty(
            name="duration",
            physicalType="INTERVAL YEAR(2) TO MONTH",
        )
        assert convert_to_sql_type(prop, "oracle") == "INTERVAL YEAR(2) TO MONTH"

    def test_physical_type_only_timestamp(self):
        prop = SchemaProperty(
            name="ts_field",
            physicalType="TIMESTAMP(6) WITH TIME ZONE",
        )
        assert convert_to_sql_type(prop, "postgres") == "TIMESTAMP(6) WITH TIME ZONE"

    def test_custom_property_physical_type_override(self):
        """A physicalType set in customProperties should be used as direct
        passthrough (same as legacy DCS config['physicalType'])."""
        prop = SchemaProperty(
            name="special_field",
            logicalType="string",
            customProperties=[
                CustomProperty(property="physicalType", value="NVARCHAR(MAX)"),
            ],
        )
        assert convert_to_sql_type(prop, "postgres") == "NVARCHAR(MAX)"


class TestPhysicalTypeWithLogicalType:
    """When both physicalType and logicalType are set, physicalType drives
    the server-specific type mapping (preserving precision)."""

    def test_long_maps_to_bigint_databricks(self):
        """DCS 'long' preserved as physicalType should map to BIGINT."""
        prop = SchemaProperty(
            name="order_total",
            logicalType="integer",
            physicalType="long",
        )
        assert convert_to_sql_type(prop, "databricks") == "BIGINT"

    def test_int_maps_to_int_databricks(self):
        """DCS 'int' preserved as physicalType should map to INT."""
        prop = SchemaProperty(
            name="count",
            logicalType="integer",
            physicalType="int",
        )
        assert convert_to_sql_type(prop, "databricks") == "INT"

    def test_text_maps_to_text_snowflake(self):
        """DCS 'text' preserved as physicalType should map to TEXT."""
        prop = SchemaProperty(
            name="name",
            logicalType="string",
            physicalType="text",
        )
        assert convert_to_sql_type(prop, "snowflake") == "TEXT"

    def test_double_maps_to_double_precision_postgres(self):
        prop = SchemaProperty(
            name="amount",
            logicalType="number",
            physicalType="double",
        )
        assert convert_to_sql_type(prop, "postgres") == "double precision"

    def test_string_maps_to_varchar_sqlserver(self):
        prop = SchemaProperty(
            name="name",
            logicalType="string",
            physicalType="string",
        )
        assert convert_to_sql_type(prop, "sqlserver") == "varchar"


class TestLogicalTypeFallback:
    """When physicalType is not set, logicalType is used for mapping."""

    def test_logical_type_only_snowflake(self):
        prop = SchemaProperty(name="order_id", logicalType="integer")
        assert convert_to_sql_type(prop, "snowflake") == "NUMBER"

    def test_logical_type_only_postgres(self):
        prop = SchemaProperty(name="amount", logicalType="number")
        assert convert_to_sql_type(prop, "postgres") == "numeric"

    def test_logical_type_only_databricks(self):
        prop = SchemaProperty(name="name", logicalType="string")
        assert convert_to_sql_type(prop, "databricks") == "STRING"

    def test_logical_type_only_duckdb(self):
        prop = SchemaProperty(name="is_active", logicalType="boolean")
        assert convert_to_sql_type(prop, "local") == "BOOLEAN"


class TestConvertTypeToOracle:
    """Oracle converter uses physicalType directly for native Oracle types."""

    def test_oracle_uses_physical_type_directly(self):
        prop = SchemaProperty(
            name="ts_field",
            logicalType="date",
            physicalType="TIMESTAMP(6)",
        )
        assert convert_type_to_oracle(prop) == "TIMESTAMP(6)"

    def test_oracle_varchar2(self):
        prop = SchemaProperty(
            name="name_field",
            logicalType="string",
            physicalType="VARCHAR2",
        )
        assert convert_type_to_oracle(prop) == "VARCHAR2"

    def test_oracle_fallback_to_logical_type(self):
        prop = SchemaProperty(name="amount", logicalType="number")
        assert convert_type_to_oracle(prop) == "NUMBER"

    def test_oracle_custom_property_override(self):
        """oracleType in customProperties should take precedence."""
        prop = SchemaProperty(
            name="special",
            logicalType="string",
            physicalType="VARCHAR2",
            customProperties=[
                CustomProperty(property="oracleType", value="NCLOB"),
            ],
        )
        assert convert_type_to_oracle(prop) == "NCLOB"

    def test_oracle_timestamp_with_timezone(self):
        prop = SchemaProperty(
            name="created_at",
            logicalType="date",
            physicalType="TIMESTAMP(6) WITH TIME ZONE",
        )
        assert convert_type_to_oracle(prop) == "TIMESTAMP(6) WITH TIME ZONE"

    def test_oracle_interval_type(self):
        prop = SchemaProperty(
            name="duration",
            logicalType="integer",
            physicalType="INTERVAL YEAR(2) TO MONTH",
        )
        assert convert_type_to_oracle(prop) == "INTERVAL YEAR(2) TO MONTH"

    def test_oracle_no_type_set(self):
        prop = SchemaProperty(name="empty_field")
        assert convert_type_to_oracle(prop) is None


class TestServerSpecificOverrides:
    """Server-specific type overrides via customProperties should still work."""

    def test_snowflake_type_override(self):
        prop = SchemaProperty(
            name="geo_field",
            logicalType="string",
            customProperties=[
                CustomProperty(property="snowflakeType", value="GEOGRAPHY"),
            ],
        )
        assert convert_to_sql_type(prop, "snowflake") == "GEOGRAPHY"

    def test_postgres_type_override(self):
        prop = SchemaProperty(
            name="id_field",
            logicalType="string",
            customProperties=[
                CustomProperty(property="postgresType", value="uuid"),
            ],
        )
        assert convert_to_sql_type(prop, "postgres") == "uuid"

    def test_dataframe_decimal_with_precision(self):
        """Decimal type with precision/scale from logicalTypeOptions."""
        prop = SchemaProperty(
            name="amount",
            logicalType="number",
            physicalType="decimal",
            logicalTypeOptions={"precision": 10, "scale": 2},
        )
        assert convert_to_sql_type(prop, "dataframe") == "DECIMAL(10,2)"
