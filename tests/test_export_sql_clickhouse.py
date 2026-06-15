from datacontract.data_contract import DataContract


def test_to_sql_ddl_clickhouse():
    """Full DDL output with all supported type mappings."""
    actual = DataContract(data_contract_file="fixtures/clickhouse/datacontract.yaml").export(
        "sql", sql_server_type="clickhouse"
    )
    expected = """
-- Data Contract: clickhouse-orders
-- SQL Dialect: clickhouse
CREATE TABLE IF NOT EXISTS `orders` (
  `order_id` String COMMENT 'Primary key of the orders table.',
  `order_timestamp` DateTime64(6) COMMENT 'The business timestamp in UTC.',
  `customer_id` Nullable(String) COMMENT 'Unique identifier for the customer.',
  `total_amount` Nullable(Decimal(38,0)) COMMENT 'Total amount in cents.',
  `discount_rate` Nullable(Float32) COMMENT 'Discount rate applied.',
  `quantity` Int32 COMMENT 'Number of items ordered.',
  `is_active` Nullable(Bool) COMMENT 'Whether the order is active.',
  `tags` Nullable(Array(String)) COMMENT 'Order tags.'
)
ENGINE = MergeTree()
ORDER BY (order_id)
COMMENT 'One record per order.';
CREATE TABLE IF NOT EXISTS `events` (
  `event_id` String,
  `event_date` Date,
  `duration` Nullable(Float64),
  `status_code` Nullable(Int8)
)
ENGINE = MergeTree()
COMMENT 'Event tracking data.';
""".strip()
    assert actual == expected


def test_to_sql_ddl_clickhouse_with_custom_engine():
    """Custom ENGINE clause via --clickhouse-engine."""
    actual = DataContract(data_contract_file="fixtures/clickhouse/datacontract.yaml").export(
        "sql",
        sql_server_type="clickhouse",
        clickhouse_engine="ReplicatedMergeTree('/clickhouse/tables/1/orders', 'replica-1')",
    )
    assert "ENGINE = ReplicatedMergeTree('/clickhouse/tables/1/orders', 'replica-1')" in actual


def test_to_sql_ddl_clickhouse_with_custom_order_by():
    """Custom ORDER BY via --clickhouse-order-by."""
    actual = DataContract(data_contract_file="fixtures/clickhouse/datacontract.yaml").export(
        "sql",
        sql_server_type="clickhouse",
        clickhouse_order_by="order_timestamp DESC, order_id",
    )
    assert "ORDER BY (order_timestamp DESC, order_id)" in actual


def test_to_sql_ddl_clickhouse_auto_detect():
    """Auto-detect ClickHouse dialect from server type."""
    actual = DataContract(data_contract_file="fixtures/clickhouse/datacontract.yaml").export("sql")
    assert "-- SQL Dialect: clickhouse" in actual
    assert "ENGINE = MergeTree()" in actual
