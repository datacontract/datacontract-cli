Setup:

# Create an S3 bucket for Iceberg data


```
s3://datacontract-iceberg-demo
```

# Create an S3 bucket for Athena Results

```
s3://entropy-data-demo-athena-results-dfhsiuya
```

# Create a Glue database

In Athena run:
```
CREATE DATABASE icebergdemodb
```

# Create an Iceberg table
In Athena run:
```
CREATE TABLE athena_iceberg_table_partitioned (
    color string,
    date string,
    name string,
    price bigint,
    product string,
    ts timestamp)
PARTITIONED BY (day(ts))
LOCATION 's3://datacontract-iceberg-demo/ice_warehouse/iceberg_db/athena_iceberg_table/'
TBLPROPERTIES (
    'table_type' ='ICEBERG'
)
```

# Add some data to the Iceberg table

In Athena run:
```
INSERT INTO "icebergdemodb"."athena_iceberg_table_partitioned" VALUES (
    'red', '222022-07-19T03:47:29', 'PersonNew', 178, 'Tuna', now()
)
```

# Add a new IAM user 
No permissions needed

E.g. `datacontract-cli-unittests`

# Create an Access Key for this IAM user

Use type `other`
Save them in .env file
```
DATACONTRACT_S3_ACCESS_KEY_ID=AKIA...
DATACONTRACT_S3_SECRET_ACCESS_KEY=...
```

# Give permissions to the IAM user

In Glue ->
https://eu-central-1.console.aws.amazon.com/glue/home?region=eu-central-1#/v2/iam-permissions/select-users

Select the S3 bucket

Create the standard role `AWSGlueServiceRole`
