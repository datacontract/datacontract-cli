CREATE TABLE CHECKS_TESTCASE (
  CTC_ID                            NUMBER PRIMARY KEY,               -- Primary key
  DESCRIPTION                       VARCHAR2(30) NOT NULL,            -- Description
  AMOUNT                            NUMBER(10),                       -- Amount purchased
  QUALITY                           NUMBER,                           -- Percentage of checks passed
  CUSTOM_ATTRIBUTES                 CLOB,                             -- Custom attributes
	FIELD_VARCHAR                     VARCHAR2(100),                    -- Variable-length string
  FIELD_NVARCHAR                    NVARCHAR2(100),                   -- Variable-length Unicode string
  FIELD_NUMBER                      NUMBER,                           -- Number
  FIELD_FLOAT                       FLOAT,                            -- Float
  FIELD_DATE                        DATE,                             -- Date and Time down to second precision
  FIELD_BINARY_FLOAT                BINARY_FLOAT,                     -- 32-bit floating point number
  FIELD_BINARY_DOUBLE               BINARY_DOUBLE,                    -- 64-bit floating point number
  FIELD_TIMESTAMP                   TIMESTAMP,                        -- Timestamp with fractional second precision of 6, no timezones
  FIELD_TIMESTAMP_TZ                TIMESTAMP WITH TIME ZONE,         -- Timestamp with fractional second precision of 6, with timezones (TZ)
  FIELD_TIMESTAMP_LTZ               TIMESTAMP WITH LOCAL TIME ZONE,   -- Timestamp with fractional second precision of 6, with local timezone (LTZ)
  FIELD_INTERVAL_YEAR               INTERVAL YEAR TO MONTH,           -- Interval of time in years and months with default (2) precision
  FIELD_INTERVAL_DAY                INTERVAL DAY TO SECOND,           -- Interval of time in days, hours, minutes and seconds with default (2 / 6) precision
  FIELD_RAW                         RAW(1000),                        -- Large raw binary data
  FIELD_ROWID                       ROWID,                            -- Base 64 string representing a unique row address
  FIELD_UROWID                      UROWID,                           -- Base 64 string representing the logical address
  FIELD_CHAR                        CHAR(10),                         -- Fixed-length string
  FIELD_NCHAR                       NCHAR(10),                        -- Fixed-length Unicode string
  FIELD_CLOB                        CLOB,                             -- Character large object
  FIELD_NCLOB                       NCLOB,                            -- National character large object
  FIELD_BLOB                        BLOB,                             -- Binary large object
  FIELD_BFILE                       BFILE,                            -- Binary file
  CONSTRAINT check_quality_is_percentage CHECK (quality BETWEEN 0 AND 100),
  CONSTRAINT check_custom_attributes_is_json CHECK (CUSTOM_ATTRIBUTES IS JSON)
);

INSERT INTO CHECKS_TESTCASE (CTC_ID, DESCRIPTION, AMOUNT, QUALITY) VALUES (1,   'One',   1, 100);
INSERT INTO CHECKS_TESTCASE (CTC_ID, DESCRIPTION, AMOUNT, QUALITY) VALUES (2,   'Two',   2, 100);
INSERT INTO CHECKS_TESTCASE (CTC_ID, DESCRIPTION, AMOUNT, QUALITY) VALUES (3, 'Three',   3, 100);
INSERT INTO CHECKS_TESTCASE (CTC_ID, DESCRIPTION, AMOUNT, QUALITY) VALUES (4,  'Four',   4, 100);
INSERT INTO CHECKS_TESTCASE (CTC_ID, DESCRIPTION, AMOUNT, QUALITY) VALUES (5,  'Five',   5, 100);
INSERT INTO CHECKS_TESTCASE (CTC_ID, DESCRIPTION, AMOUNT, QUALITY) VALUES (6,   'Six',   6, 100);
INSERT INTO CHECKS_TESTCASE (CTC_ID, DESCRIPTION, AMOUNT, QUALITY) VALUES (7, 'Seven', 100,  95);
INSERT INTO CHECKS_TESTCASE (CTC_ID, DESCRIPTION, AMOUNT, QUALITY) VALUES (8, 'Eight',   8, 100);
INSERT INTO CHECKS_TESTCASE (CTC_ID, DESCRIPTION, AMOUNT, QUALITY, CUSTOM_ATTRIBUTES)
  VALUES (9, 'Nine',  50,  10, '{ "quality": "junk", "description": "Spare parts" }')
