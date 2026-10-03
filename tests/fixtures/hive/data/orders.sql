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

INSERT INTO orders PARTITION (region = 'eu')
SELECT 'ORD-0001', 'C-1', 'open', 'EUR', 19.99, 1, 1, CAST(NULL AS DOUBLE), false, DATE '2026-09-01', TIMESTAMP '2026-09-01 10:00:00', array('new'), named_struct('city', 'Berlin', 'zip', '10115'), map('channel', 'web')
UNION ALL
SELECT 'ORD-0002', 'C-2', 'shipped', 'EUR', 250.00, 3, 2, 0.1, true, DATE '2026-09-02', TIMESTAMP '2026-09-02 11:30:00', array('vip', 'gift'), named_struct('city', 'Paris', 'zip', '75001'), map('channel', 'app')
UNION ALL
SELECT 'ORD-0003', CAST(NULL AS VARCHAR(10)), 'shipped', 'EUR', 5.50, 2, 1, CAST(NULL AS DOUBLE), false, DATE '2026-09-03', TIMESTAMP '2026-09-03 12:45:00', array('none'), named_struct('city', 'Rome', 'zip', '00118'), map('channel', 'web');

INSERT INTO orders PARTITION (region = 'us')
SELECT 'ORD-0004', 'C-1', 'cancelled', 'USD', 1200.00, 10, 4, 0.25, false, DATE '2026-09-04', TIMESTAMP '2026-09-04 08:15:00', array('bulk'), named_struct('city', 'Austin', 'zip', '73301'), map('channel', 'phone')
UNION ALL
SELECT 'ORD-0005', 'C-3', 'open', 'USD', 75.00, 1, 1, CAST(NULL AS DOUBLE), true, DATE '2026-09-05', TIMESTAMP '2026-09-05 09:00:00', array('gift'), named_struct('city', 'Boston', 'zip', '02108'), map('channel', 'web')
