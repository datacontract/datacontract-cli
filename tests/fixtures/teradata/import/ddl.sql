CREATE TABLE my_table
(
  field_primary_key      INTEGER PRIMARY KEY,       -- Primary key
  field_not_null         INTEGER NOT NULL,          -- Not null
  field_byteint          BYTEINT,                   -- Single-byte integer
  field_smallint         SMALLINT,                  -- Small integer
  field_int              INTEGER,                   -- Regular integer
  field_bigint           BIGINT,                    -- Large integer
  field_decimal          DECIMAL(10, 2),            -- Fixed precision decimal
  field_numeric          NUMERIC(18, 4),            -- Numeric type
  field_float            FLOAT,                     -- Floating-point number
  field_double           DOUBLE,                    -- Double precision float
  field_char             CHAR(10),                  -- Fixed-length character
  field_varchar          VARCHAR(100),              -- Variable-length character
  field_date             DATE,                      -- Date only (YYYY-MM-DD)
  field_time             TIME,                      -- Time only (HH:MM:SS)
  field_timestamp        TIMESTAMP,                 -- Date and time
  field_interval_year_month INTERVAL YEAR TO MONTH, -- Year-month interval
  field_interval_day_second INTERVAL DAY TO SECOND, -- Day-second interval
  field_byte             BYTE(50),                  -- Fixed-length byte string
  field_varbyte          VARBYTE(100),              -- Variable-length byte string
  field_blob             BLOB,                      -- Binary large object
  field_clob             CLOB                       -- Character large object
);
