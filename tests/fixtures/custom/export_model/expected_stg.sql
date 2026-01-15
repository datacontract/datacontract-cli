
select
  try_cast(line_item_id as text) as line_item_id
  try_cast(order_id as text) as order_id
  try_cast(sku as text) as sku
from {{ source('orders-latest', 'line_items') }}