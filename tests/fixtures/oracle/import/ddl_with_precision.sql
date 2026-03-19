-- Test Oracle DDL with NUMBER(precision, scale) types
-- https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/Data-Types.html

CREATE TABLE customers
(
  customer_id     NUMBER(9, 0),      -- Integer-like number with precision
  customer_score  NUMBER(5, 2),      -- Decimal number with precision and scale
  balance         NUMBER(15, 4),     -- Large decimal number
  amount          NUMBER(10),        -- Number with only precision
  plain_number    NUMBER             -- Plain number without precision or scale
)
