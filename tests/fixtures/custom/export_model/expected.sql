
SELECT
  user_id AS user_id,
FROM {{ ref('users') }}