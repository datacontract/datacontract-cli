CREATE TABLE orders
(
    order_id        String,
    customer_id     Nullable(String),
    order_status    LowCardinality(String),
    order_total     Decimal(10, 2),
    quantity        Int32,
    discount        Nullable(Float64),
    is_gift         Bool,
    order_date      Date,
    order_timestamp DateTime64(3, 'UTC'),
    tags            Array(String),
    updated_at      DateTime
)
ENGINE = MergeTree
ORDER BY order_id;

-- ORD-0001 twice, a malformed id, an unknown status, a negative total, a zero quantity, two missing customers
INSERT INTO orders VALUES
    ('ORD-0001', 'C-1', 'open', 19.99, 1, NULL, false, '2026-09-01', '2026-09-01 10:00:00.000', ['new'], now()),
    ('ORD-0001', NULL, 'shipped', 250.00, 3, 0.1, true, '2026-09-02', '2026-09-02 11:30:00.250', ['vip'], now()),
    ('order-3', NULL, 'lost', -5.50, 0, NULL, false, '2026-09-03', '2026-09-03 12:45:00.500', [], now());
