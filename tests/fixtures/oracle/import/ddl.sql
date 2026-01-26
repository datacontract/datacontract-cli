-- https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/Data-Types.html

CREATE TABLE field_showcase
(
  field_primary_key           INT PRIMARY KEY,                  -- Primary key
  field_not_null              INT NOT NULL,                     -- Not null
  field_varchar               VARCHAR2,                         -- Variable-length string
  field_nvarchar              NVARCHAR2,                        -- Variable-length Unicode string
  field_number                NUMBER,                           -- Number
  field_float                 FLOAT,                            -- Float
  field_date                  DATE,                             -- Date and Time down to second precision
  field_binary_float          BINARY_FLOAT,                     -- 32-bit floating point number
  field_binary_double         BINARY_DOUBLE,                    -- 64-bit floating point number
  field_timestamp             TIMESTAMP,                        -- Timestamp with fractional second precision of 6, no timezones
  field_timestamp_tz          TIMESTAMP WITH TIME ZONE,         -- Timestamp with fractional second precision of 6, with timezones (TZ)
  field_timestamp_ltz         TIMESTAMP WITH LOCAL TIME ZONE,   -- Timestamp with fractional second precision of 6, with local timezone (LTZ)
  field_interval_year         INTERVAL YEAR TO MONTH,           -- Interval of time in years and months with default (2) precision
  field_interval_day          INTERVAL DAY TO SECOND,           -- Interval of time in days, hours, minutes and seconds with default (2 / 6) precision
  field_raw                   RAW,                              -- Large raw binary data
  field_rowid                 ROWID,                            -- Base 64 string representing a unique row address
  field_urowid                UROWID,                           -- Base 64 string representing the logical address
  field_char                  CHAR(10),                         -- Fixed-length string
  field_nchar                 NCHAR(10),                        -- Fixed-length Unicode string
  field_clob                  CLOB,                             -- Character large object
  field_nclob                 NCLOB,                            -- National character large object
  field_blob                  BLOB,                             -- Binary large object
  field_bfile                 BFILE                             -- Binary file
)