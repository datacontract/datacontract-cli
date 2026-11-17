-- __TABLE__ is replaced by the path of the table, a folder below $scratch
-- ORD-0001 twice, a malformed id, an unknown status, a negative total, a zero quantity, two missing customers
CREATE TABLE __TABLE__ AS
SELECT 'ORD-0001' AS order_id, CAST('C-1' AS VARCHAR) AS customer_id, 'open' AS order_status, 'EUR' AS currency, CAST(19.99 AS DECIMAL(10,2)) AS order_total, 1 AS quantity, CAST(1 AS BIGINT) AS line_count, CAST(NULL AS DOUBLE) AS discount, false AS is_gift, DATE '2026-09-01' AS order_date, TIMESTAMP '2026-09-01 10:00:00' AS order_timestamp, ARRAY['new'] AS tags, CONVERT_FROM('{"city": "Berlin", "zip": "10115"}', 'JSON') AS shipping, 'eu' AS region
UNION ALL
SELECT 'ORD-0001', CAST(NULL AS VARCHAR), 'shipped', 'EUR', CAST(250.00 AS DECIMAL(10,2)), 3, CAST(2 AS BIGINT), CAST(0.1 AS DOUBLE), true, DATE '2026-09-02', TIMESTAMP '2026-09-02 11:30:00', ARRAY['vip'], CONVERT_FROM('{"city": "Paris", "zip": "75001"}', 'JSON'), 'eu'
UNION ALL
SELECT 'order-3', CAST(NULL AS VARCHAR), 'lost', 'EUR', CAST(-5.50 AS DECIMAL(10,2)), 0, CAST(1 AS BIGINT), CAST(NULL AS DOUBLE), false, DATE '2026-09-03', TIMESTAMP '2026-09-03 12:45:00', ARRAY['none'], CONVERT_FROM('{"city": "Rome", "zip": "00118"}', 'JSON'), 'eu'
