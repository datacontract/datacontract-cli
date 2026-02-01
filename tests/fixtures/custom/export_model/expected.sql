
SELECT
  line_item_id AS line_item_id,
  order_id AS order_id,
  sku AS sku,
FROM {{ ref('line_items') }}