---
sidebar_position: 1
title: "Amazon Athena Reference"
sidebar_label: "Amazon Athena"
description: "All Athena authentication options and data type handling."
---

# <img className="page-icon" src="/img/icons/athena.svg" alt="" /> Amazon Athena Reference

Authentication options and data type handling for [Athena connections](../testing/athena.md).

## Server

```yaml
servers:
  - server: athena
    type: athena
    catalog: awsdatacatalog # default
    schema: my_database     # in Athena, this is called "database"
    regionName: eu-central-1
    stagingDir: s3://my-bucket/athena-results/
```

## Authentication

Athena authenticates as an AWS principal, so an existing AWS session is enough — `aws sso login`, `AWS_PROFILE`, EC2/ECS/EKS instance roles, or GitHub OIDC in CI. Unlike Redshift, no database user is involved, so nothing has to be minted or configured.

Set the variables below only to override that with static keys:

| Variable | Example | Description |
|---|---|---|
| `DATACONTRACT_S3_REGION` | `eu-central-1` | Region of the Athena service |
| `DATACONTRACT_S3_ACCESS_KEY_ID` | `AKIAXV5Q5Q...` | AWS Access Key ID |
| `DATACONTRACT_S3_SECRET_ACCESS_KEY` | `93S7LRrJ...` | AWS Secret Access Key |
| `DATACONTRACT_S3_SESSION_TOKEN` | `AQoDYXdzEJr...` | AWS temporary session token (optional) |

`catalog`, `schema` (the Athena database), `regionName`, and `stagingDir` (required, for query results) come from the contract's `servers` block; `DATACONTRACT_S3_REGION` takes precedence over `regionName` when both are set. The credentials need `athena:StartQueryExecution` plus read access to the data and write access to `stagingDir`, and `glue:GetTables` to import.

## Data types

### Importing

`datacontract import athena` reads the table metadata from the AWS Glue Data Catalog, where Athena keeps it. Glue stores the Hive spelling of two types, which the import rewrites to what Athena reports back — `string` → `varchar` and `binary` → `varbinary` — so the physical type checks pass on the first test run. Every other type already compares equal in the Athena dialect (`int`/`integer`, `array<int>`/`array(integer)`, `struct`/`row(...)`, `decimal`/`decimal(10,2)`).

Types map through the shared Glue mapping: `string`/`varchar`/`char` → `string`, `int`/`bigint`/`smallint`/`tinyint` → `integer`, `float`/`double`/`decimal` → `number`, `boolean` → `boolean`, `date` → `date`, `timestamp` → `timestamp`, `array<...>` → `array`, `struct<...>` → `object`, `binary` → `string` (format `binary`), `map<...>` → no logical type.

### Testing

Athena supports **native type introspection**: the declared `physicalType` is checked against the actual column type from the Athena catalog. Timezone variants of timestamps are interchangeable; parameters are only enforced when declared. A `physicalType` that isn't valid Athena SQL falls back to the logical type category comparison.
