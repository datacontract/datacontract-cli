SELECT
  order_id AS order_id,
  DATETIME(order_timestamp, "Asia/Tokyo") AS order_timestamp,
  order_total AS order_total,
  customer_id AS customer_id,
  customer_email_address AS customer_email_address,
  DATETIME(processed_timestamp, "Asia/Tokyo") AS processed_timestamp,
FROM
  {{ ref('orders') }}
