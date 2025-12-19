CREATE TABLE customer_location
(
  id                             DECIMAL              NOT NULL,
  created_by                     VARCHAR(30)          NOT NULL,
  create_date                    TIMESTAMP            NOT NULL,
  changed_by                     VARCHAR(30),
  change_date                    TIMESTAMP,
  name                           VARCHAR(120)         NOT NULL,
  short_name                     VARCHAR(60),
  display_name                   VARCHAR(120)         NOT NULL,
  code                           VARCHAR(30)          NOT NULL,
  description                    VARCHAR(4000),
  language_id                    DECIMAL              NOT NULL,
  status                         VARCHAR(2)           NOT NULL,
  CONSTRAINT customer_location_code_key UNIQUE (code),
  CONSTRAINT customer_location_pkey PRIMARY KEY (id)
);

COMMENT ON TABLE customer_location IS 'Table contains records of customer specific Location/address.';
COMMENT ON COLUMN customer_location.change_date IS 'Date when record is modified.';
COMMENT ON COLUMN customer_location.changed_by IS 'User who modified record.';
COMMENT ON COLUMN customer_location.code IS 'Customer location code.';
COMMENT ON COLUMN customer_location.create_date IS 'Date when record is created.';
COMMENT ON COLUMN customer_location.created_by IS 'User who created a record.';
COMMENT ON COLUMN customer_location.description IS 'Description if needed.';
COMMENT ON COLUMN customer_location.display_name IS 'Display name of the customer location.';
COMMENT ON COLUMN customer_location.id IS 'Unique identification ID for the record - created by sequence SEQ_CUSTOMER_LOCATION.';
COMMENT ON COLUMN customer_location.language_id IS 'Language ID. Reference to LANGUAGE table.';
COMMENT ON COLUMN customer_location.name IS 'Name of the customer location.';
