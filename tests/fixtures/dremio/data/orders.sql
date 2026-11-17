-- __TABLE__ is replaced by the path of the table, a folder below $scratch
CREATE TABLE __TABLE__ AS
SELECT 'ORD-0001' AS order_id, CAST('C-1' AS VARCHAR) AS customer_id, 'open' AS order_status, 'EUR' AS currency, CAST(19.99 AS DECIMAL(10,2)) AS order_total, 1 AS quantity, CAST(1 AS BIGINT) AS line_count, CAST(NULL AS DOUBLE) AS discount, false AS is_gift, DATE '2026-09-01' AS order_date, TIMESTAMP '2026-09-01 10:00:00' AS order_timestamp, ARRAY['new'] AS tags, CONVERT_FROM('{"city": "Berlin", "zip": "10115"}', 'JSON') AS shipping, 'eu' AS region
UNION ALL
SELECT 'ORD-0002', 'C-2', 'shipped', 'EUR', CAST(250.00 AS DECIMAL(10,2)), 3, CAST(2 AS BIGINT), CAST(0.1 AS DOUBLE), true, DATE '2026-09-02', TIMESTAMP '2026-09-02 11:30:00', ARRAY['vip', 'gift'], CONVERT_FROM('{"city": "Paris", "zip": "75001"}', 'JSON'), 'eu'
UNION ALL
SELECT 'ORD-0003', CAST(NULL AS VARCHAR), 'shipped', 'EUR', CAST(5.50 AS DECIMAL(10,2)), 2, CAST(1 AS BIGINT), CAST(NULL AS DOUBLE), false, DATE '2026-09-03', TIMESTAMP '2026-09-03 12:45:00', ARRAY['none'], CONVERT_FROM('{"city": "Rome", "zip": "00118"}', 'JSON'), 'eu'
UNION ALL
SELECT 'ORD-0004', 'C-1', 'cancelled', 'USD', CAST(1200.00 AS DECIMAL(10,2)), 10, CAST(4 AS BIGINT), CAST(0.25 AS DOUBLE), false, DATE '2026-09-04', TIMESTAMP '2026-09-04 08:15:00', ARRAY['bulk'], CONVERT_FROM('{"city": "Austin", "zip": "73301"}', 'JSON'), 'us'
UNION ALL
SELECT 'ORD-0005', 'C-3', 'open', 'USD', CAST(75.00 AS DECIMAL(10,2)), 1, CAST(1 AS BIGINT), CAST(NULL AS DOUBLE), true, DATE '2026-09-05', TIMESTAMP '2026-09-05 09:00:00', ARRAY['gift'], CONVERT_FROM('{"city": "Boston", "zip": "02108"}', 'JSON'), 'us'
