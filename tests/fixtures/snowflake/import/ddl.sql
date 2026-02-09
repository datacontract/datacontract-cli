-- https://docs.snowflake.com/en/sql-reference-data-types
CREATE OR REPLACE TABLE mytable (
    field_primary_key INT PRIMARY KEY,           -- Primary key
    field_not_null INT NOT NULL,                 -- Not null
    field_char CHAR(10),                         -- Fixed-length string
    field_varchar VARCHAR(100),                  -- Variable-length string
    field_text TEXT,                             -- Large variable-length string (alias for VARCHAR(16777216))
    field_string STRING,                         -- Alias for VARCHAR(16777216)
    field_nchar CHAR(10),                        -- Fixed-length string (no separate NCHAR)
    field_nvarchar VARCHAR(100),                 -- Variable-length string (no separate NVARCHAR)
    field_ntext TEXT,                            -- Large variable-length string
    field_tinyint SMALLINT,                      -- Snowflake doesn't have TINYINT, use SMALLINT
    field_smallint SMALLINT,                     -- Integer (-32,768 to 32,767)
    field_int INT,                               -- Integer (-2.1B to 2.1B)
    field_bigint BIGINT,                         -- Large integer
    field_decimal DECIMAL(10, 2),                -- Fixed precision decimal
    field_numeric NUMERIC(10, 2),                -- Same as DECIMAL
    field_number NUMBER(38, 0),                  -- Default numeric type (more flexible than DECIMAL)
    field_double DOUBLE,                         -- Double precision floating-point (synonym for FLOAT)
    field_float FLOAT,                           -- Approximate floating-point
    field_real FLOAT,                            -- Snowflake doesn't have REAL, use DOUBLE as synonym of FLOAT
    field_bit BOOLEAN,                           -- Boolean (TRUE/FALSE)
    field_date DATE,                             -- Date only (YYYY-MM-DD)
    field_time TIME,                             -- Time only (HH:MM:SS)
    field_datetime2 TIMESTAMP_NTZ,               -- Timestamp without timezone
    field_smalldatetime TIMESTAMP_NTZ,           -- Timestamp without timezone
    field_datetimeoffset TIMESTAMP_TZ,           -- Timestamp with timezone
    field_timestamp_ltz TIMESTAMP_LTZ,           -- Timestamp with local timezone
    field_binary BINARY(16),                     -- Fixed-length binary
    field_varbinary BINARY(100),                 -- Variable-length binary
    field_uniqueidentifier VARCHAR(36),          -- GUID stored as string
    field_xml VARIANT,                           -- Semi-structured data (XML as VARIANT)
    field_json VARIANT,                          -- Semi-structured data (native JSON support)
    field_object OBJECT,                         -- Semi-structured object (key-value pairs)
    field_array ARRAY,                           -- Semi-structured array
    field_geography GEOGRAPHY,                   -- Geospatial data (points, lines, polygons)
    field_geometry GEOMETRY,                     -- Geospatial data (planar coordinates)
    field_vector VECTOR(FLOAT, 16)               -- Vector data for ML/AI (16-dimensional float vector)
);