CREATE TABLE orders (
    order_id STRING,
    customer_id VARCHAR(10),
    order_status STRING,
    currency CHAR(3),
    order_total DECIMAL(10,2),
    quantity INT,
    line_count BIGINT,
    discount DOUBLE,
    is_gift BOOLEAN,
    order_date DATE,
    order_timestamp TIMESTAMP,
    tags ARRAY<STRING>,
    shipping STRUCT<city:STRING,zip:STRING>,
    attributes MAP<STRING,STRING>
)
PARTITIONED BY (region STRING)
STORED AS PARQUET;

-- ORD-0001 twice, a malformed id, an unknown status, a negative total, a zero quantity, two missing customers
INSERT INTO orders PARTITION (region = 'eu')
SELECT 'ORD-0001', 'C-1', 'open', 'EUR', 19.99, 1, 1, CAST(NULL AS DOUBLE), false, DATE '2026-09-01', TIMESTAMP '2026-09-01 10:00:00', array('new'), named_struct('city', 'Berlin', 'zip', '10115'), map('channel', 'web')
UNION ALL
SELECT 'ORD-0001', CAST(NULL AS VARCHAR(10)), 'shipped', 'EUR', 250.00, 3, 2, 0.1, true, DATE '2026-09-02', TIMESTAMP '2026-09-02 11:30:00', array('vip'), named_struct('city', 'Paris', 'zip', '75001'), map('channel', 'app')
UNION ALL
SELECT 'order-3', CAST(NULL AS VARCHAR(10)), 'lost', 'EUR', -5.50, 0, 1, CAST(NULL AS DOUBLE), false, DATE '2026-09-03', TIMESTAMP '2026-09-03 12:45:00', array('none'), named_struct('city', 'Rome', 'zip', '00118'), map('channel', 'web')
