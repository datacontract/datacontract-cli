---
sidebar_position: 1
title: "Amazon Athena"
description: "Test data in AWS Athena stored in S3."
---

# Amazon Athena

Test data in AWS Athena stored in S3. Supports formats such as Iceberg, Parquet, JSON, and CSV.

## Example

```yaml
servers:
  athena:
    type: athena
    catalog: awsdatacatalog # default
    schema: icebergdemodb   # in Athena, this is called "database"
    regionName: eu-central-1
    stagingDir: s3://my-bucket/athena-results/
models:
  my_table: # corresponds to a table or view
    type: table
    fields:
      my_column_1:
        type: string
        config:
          physicalType: varchar
```

## Environment variables

| Variable | Example | Description |
|---|---|---|
| `DATACONTRACT_S3_REGION` | `eu-central-1` | Region of the Athena service |
| `DATACONTRACT_S3_ACCESS_KEY_ID` | `AKIAXV5Q5Q...` | AWS Access Key ID |
| `DATACONTRACT_S3_SECRET_ACCESS_KEY` | `93S7LRrJ...` | AWS Secret Access Key |
| `DATACONTRACT_S3_SESSION_TOKEN` | `AQoDYXdzEJr...` | AWS temporary session token (optional) |

Requires the `athena` extra.
