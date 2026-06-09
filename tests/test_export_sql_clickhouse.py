from datacontract.data_contract import DataContract


def test_to_sql_ddl_clickhouse():
    """Full DDL output with all supported type mappings."""
    actual = DataContract(data_contract_file="fixtures/clickhouse/datacontract.yaml").export(
        "sql", sql_server_type="clickhouse"
    )
    expected = """
-- Data Contract: clickhouse-orders
-- SQL Dialect: clickhouse
CREATE TABLE orders (
  order_id String not null primary key COMMENT 'Primary key of the orders table.',
  order_timestamp DateTime64(3) not null COMMENT 'The business timestamp in UTC.',
  customer_id String COMMENT 'Unique identifier for the customer.',
  total_amount Decimal(38,0) COMMENT 'Total amount in cents.',
  discount_rate Float32 COMMENT 'Discount rate applied.',
  quantity Int32 not null COMMENT 'Number of items ordered.',
  is_active Bool COMMENT 'Whether the order is active.',
  tags Array(String) COMMENT 'Order tags.'
)
ENGINE = MergeTree()
ORDER BY (order_id)
COMMENT 'One record per order.';
CREATE TABLE events (
  event_id String not null,
  event_date Date not null,
  duration Float64,
  status_code Int8
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


def test_to_sql_ddl_clickhouse_no_pk_omits_order_by():
    """Tables without primary keys should omit ORDER BY."""
    actual = DataContract(data_contract_file="fixtures/clickhouse/datacontract.yaml").export(
        "sql", sql_server_type="clickhouse"
    )
    # events table has no PK, so no ORDER BY
    assert "ORDER BY" in actual  # orders table has one
    # Only one ORDER BY (for orders, which has a PK)
    assert actual.count("ORDER BY") == 1
