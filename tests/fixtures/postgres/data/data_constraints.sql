CREATE TABLE my_schema.customer_location
(
  id                             numeric              NOT NULL,
  created_by                     varchar(30)          NOT NULL,
  create_date                    timestamp            NOT NULL,
  changed_by                     varchar(30)         ,
  change_date                    timestamp           ,
  name                           varchar(120)         NOT NULL,
  short_name                     varchar(60)         ,
  display_name                   varchar(120)         NOT NULL,
  code                           varchar(30)          NOT NULL,
  description                    varchar(4000)       ,
  language_id                    numeric              NOT NULL,
  status                         varchar(2)           NOT NULL,
  CONSTRAINT customer_location_code_key UNIQUE (code),
  CONSTRAINT customer_location_pkey PRIMARY KEY (id)
);


comment on table my_schema.customer_location is 'Table contains records of customer specific Location/address.';
comment on column my_schema.customer_location.change_date is 'Date when record is modified.';
comment on column my_schema.customer_location.changed_by is 'User who modified record.';
comment on column my_schema.customer_location.code is 'Customer location code.';
comment on column my_schema.customer_location.create_date is 'Date when record is created.';
comment on column my_schema.customer_location.created_by is 'User who created a record.';
comment on column my_schema.customer_location.description is 'Description if needed.';
comment on column my_schema.customer_location.display_name is 'Display name of the customer location.';
comment on column my_schema.customer_location.id is 'Unique identification ID for the record - created by sequence SEQ_CUSTOMER_LOCATION.';
comment on column my_schema.customer_location.language_id is 'Language ID. Reference to LANGUAGE table.';
comment on column my_schema.customer_location.name is 'Name of the customer location.';
comment on column my_schema.customer_location.short_name is 'Short name of the customer location.';
comment on column my_schema.customer_location.status is 'Status of the customer location.';
