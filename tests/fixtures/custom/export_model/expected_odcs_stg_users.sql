
select
  try_cast(user_id as varchar) as user_id
from {{ source('orders-unit-test', 'users') }}