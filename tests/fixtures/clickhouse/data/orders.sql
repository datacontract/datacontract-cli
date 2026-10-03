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

INSERT INTO orders VALUES
    ('ORD-0001', 'C-1', 'open', 19.99, 1, NULL, false, '2026-09-01', '2026-09-01 10:00:00.000', ['new'], now()),
    ('ORD-0002', 'C-2', 'shipped', 250.00, 3, 0.1, true, '2026-09-02', '2026-09-02 11:30:00.250', ['vip', 'gift'], now()),
    ('ORD-0003', NULL, 'shipped', 5.50, 2, NULL, false, '2026-09-03', '2026-09-03 12:45:00.500', [], now()),
    ('ORD-0004', 'C-1', 'cancelled', 1200.00, 10, 0.25, false, '2026-09-04', '2026-09-04 08:15:00.000', ['bulk'], now()),
    ('ORD-0005', 'C-3', 'open', 75.00, 1, NULL, true, '2026-09-05', '2026-09-05 09:00:00.999', ['gift'], now());
