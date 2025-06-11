CREATE TABLE IF NOT EXISTS  ${database_name}.PUBLIC.my_table (
  -- https://docs.snowflake.com/en/sql-reference/intro-summary-data-types
  field_primary_key      NUMBER(38,0) NOT NULL autoincrement start 1 increment 1 noorder COMMENT 'Primary key',
  field_not_null         INT NOT NULL     COMMENT 'Not null',
  field_char             CHAR(10)         COMMENT 'Fixed-length string',
  field_character        CHARACTER(10)    COMMENT 'Fixed-length string',
  field_varchar          VARCHAR(100) WITH TAG (SNOWFLAKE.CORE.PRIVACY_CATEGORY='IDENTIFIER', SNOWFLAKE.CORE.SEMANTIC_CATEGORY='NAME') COMMENT 'Variable-length string',
 
  field_text             TEXT             COMMENT 'Large variable-length string',
  field_string           STRING           COMMENT 'Large variable-length Unicode string',

  field_tinyint          TINYINT          COMMENT 'Integer (0-255)',
  field_smallint         SMALLINT         COMMENT 'Integer (-32,768 to 32,767)',
  field_int              INT              COMMENT 'Integer (-2.1B to 2.1B)',
  field_integer          INTEGER          COMMENT 'Integer full name(-2.1B to 2.1B)',
  field_bigint           BIGINT           COMMENT 'Large integer (-9 quintillion to 9 quintillion)',

  field_decimal          DECIMAL(10, 2)   COMMENT 'Fixed precision decimal',
  field_numeric          NUMERIC(10, 2)   COMMENT 'Same as DECIMAL',

  field_float            FLOAT            COMMENT 'Approximate floating-point',
  field_float4           FLOAT4           COMMENT 'Approximate floating-point 4',
  field_float8           FLOAT8           COMMENT 'Approximate floating-point 8',
  field_real             REAL             COMMENT 'Smaller floating-point',
 
  field_boulean          BOOLEAN          COMMENT 'Boolean-like (0 or 1)',

  field_date             DATE             COMMENT 'Date only (YYYY-MM-DD)',
  field_time             TIME             COMMENT 'Time only (HH:MM:SS)',
  field_timestamp        TIMESTAMP        COMMENT 'More precise datetime',
  field_timestamp_ltz    TIMESTAMP_LTZ    COMMENT 'More precise datetime with local time zone; time zone, if provided, isn`t stored.',
  field_timestamp_ntz    TIMESTAMP_NTZ DEFAULT CURRENT_TIMESTAMP() COMMENT 'More precise datetime with no time zone; time zone, if provided, isn`t stored.',
  field_timestamp_tz     TIMESTAMP_TZ     COMMENT 'More precise datetime with time zone.',

  field_binary           BINARY(16)       COMMENT 'Fixed-length binary',
  field_varbinary        VARBINARY(100)   COMMENT 'Variable-length binary',

  field_variant          VARIANT          COMMENT 'VARIANT data',
  field_json             OBJECT           COMMENT 'JSON (Stored as text)',
  UNIQUE(field_not_null),
  PRIMARY KEY (field_primary_key)
) COMMENT = 'My Comment'
