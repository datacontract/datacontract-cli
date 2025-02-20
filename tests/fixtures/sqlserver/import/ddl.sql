CREATE TABLE [dbo].[my_table]
(
  field_primary_key      INT PRIMARY KEY,  -- Primary key
  field_not_null         INT NOT NULL,     -- Not null
  field_char             CHAR(10),         -- Fixed-length string
  field_varchar          VARCHAR(100),     -- Variable-length string
  field_text             VARCHAR(MAX),     -- Large variable-length string
  field_nchar            NCHAR(10),        -- Fixed-length Unicode string
  field_nvarchar         NVARCHAR(100),    -- Variable-length Unicode string
  field_ntext            NVARCHAR(MAX),    -- Large variable-length Unicode string

  field_tinyint          TINYINT,          -- Integer (0-255)
  field_smallint         SMALLINT,         -- Integer (-32,768 to 32,767)
  field_int              INT,              -- Integer (-2.1B to 2.1B)
  field_bigint           BIGINT,           -- Large integer (-9 quintillion to 9 quintillion)

  field_decimal          DECIMAL(10, 2),   -- Fixed precision decimal
  field_numeric          NUMERIC(10, 2),   -- Same as DECIMAL
  field_float            FLOAT,            -- Approximate floating-point
  field_real             REAL,             -- Smaller floating-point

  field_bit              BIT,              -- Boolean-like (0 or 1)

  field_date             DATE,             -- Date only (YYYY-MM-DD)
  field_time             TIME,             -- Time only (HH:MM:SS)
  field_datetime2        DATETIME2,        -- More precise datetime
  field_smalldatetime    SMALLDATETIME,    -- Less precise datetime
  field_datetimeoffset   DATETIMEOFFSET,   -- Datetime with time zone

  field_binary           BINARY(16),       -- Fixed-length binary
  field_varbinary        VARBINARY(100),   -- Variable-length binary

  field_uniqueidentifier UNIQUEIDENTIFIER, -- GUID

  field_xml              XML,              -- XML data
  field_json             JSON,             -- JSON (Stored as text)

--   field_sql_variant SQL_VARIANT          -- Stores different data types
);