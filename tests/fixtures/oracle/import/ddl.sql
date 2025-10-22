-- https://docs.oracle.com/en/database/oracle/oracle-database/19/sqlrf/Data-Types.html

CREATE TABLE [dbo].[my_table]
(
  field_primary_key           INT PRIMARY KEY,                  -- Primary key
  field_not_null              INT NOT NULL,                     -- Not null
  -- Max String size is 4000 for MAX_STRING_SIZE = STANDARD (Default)
  field_varchar               VARCHAR2(100),                    -- Variable-length string
  field_nvarchar              NVARCHAR2(100),                   -- Variable-length Unicode string
  -- First: Precision can vary 1-38, Second: Scale can vary from -84 tp 127
  field_number_small          NUMBER(1, 0),                     -- Very small number
  field_number_large          NUMBER(36, 20),                   -- Very large number
  field_float_small           FLOAT(1),                         -- Very small float
  field_float_large           FLOAT(126),                       -- Very large float
  field_date                  DATE,                             -- Date and Time down to second precision
  field_binary_float          BINARY_FLOAT,                     -- 32-bit floating point number
  field_binary_double         BINARY_DOUBLE,                    -- 64-bit floating point number
  field_timestamp_default     TIMESTAMP,                        -- Timestamp with fractional second precision of 6, no timezones
  field_timestamp_small       TIMESTAMP(0),                     -- Timestamp with no fractional seconds
  field_timestamp_large       TIMESTAMP(9),                     -- Timestamp with maximum fractional second precision
  field_timestamp_tz_default  TIMESTAMP WITH TIME ZONE,         -- Timestamp with fractional second precision of 6, with timezones (TZ)
  field_timestamp_tz_small    TIMESTAMP(0) WITH TIME ZONE,      -- Timestamp TZ with no fractional seconds
  field_timestamp_tz_large    TIMESTAMP(9) WITH TIME ZONE,      -- Timestamp TZ with maximum fractional second precision
  field_timestamp_ltz_default TIMESTAMP WITH LOCAL TIME ZONE,   -- Timestamp with fractional second precision of 6, with local timezone (LTZ)
  field_timestamp_ltz_small   TIMESTAMP(0) WITH LOCAL TIME ZONE,-- Timestamp LTZ with no fractional seconds
  field_timestamp_ltz_large   TIMESTAMP(9) WITH LOCAL TIME ZONE,-- Timestamp LTZ with maximum fractional second precision
  field_interval_year_default INTERVAL YEAR TO MONTH,           -- Interval of time in years and months with default (2) precision
  field_interval_year_small   INTERVAL YEAR(0) TO MONTH,        -- Interval of time in years and months with minimum precision
  field_interval_year_large   INTERVAL YEAR(9) TO MONTH,        -- Interval of time in years and months with maximum precision
  field_interval_day_default  INTERVAL DAY TO SECOND,           -- Interval of time in days, hours, minutes and seconds with default (2 / 6) precision
  field_interval_day_small    INTERVAL DAY(0) TO SECOND(0),     -- Interval of time in days, hours, minutes and seconds with minimum precision
  field_interval_day_large    INTERVAL DAY(9) TO SECOND(9),     -- Interval of time in days, hours, minutes and seconds with maximum precision
  field_raw             	    RAW(2000),                        -- Large raw binary data (Maximum for MAX_STRING_SIZE = STANDARD),
  field_rowid                 ROWID,                            -- Base 64 string representing a unique row address
  field_urowid                UROWID,                           -- Base 64 string representing the logical address
  field_char                  CHAR(10),                         -- Fixed-length string
  field_nchar                 NCHAR(10)                         -- Fixed-length Unicode string
  -- Clob, NClob, Blob and Bfile

  -- Longs are deprecated and it is encouraged not to use them and use clobs instead
  -- Also they are limited to one per table
)