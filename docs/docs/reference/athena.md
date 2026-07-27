---
sidebar_position: 7
title: "Amazon Athena Reference"
sidebar_label: "Amazon Athena"
description: "All Athena authentication options and data type handling."
---

# <img className="page-icon" src="/img/icons/athena.svg" alt="" /> Amazon Athena Reference

Authentication options and data type handling for [Athena connections](../connect/athena.md).

## Authentication

Athena uses the S3 environment variables:

| Variable | Example | Description |
|---|---|---|
| `DATACONTRACT_S3_REGION` | `eu-central-1` | Region of the Athena service |
| `DATACONTRACT_S3_ACCESS_KEY_ID` | `AKIAXV5Q5Q...` | AWS Access Key ID |
| `DATACONTRACT_S3_SECRET_ACCESS_KEY` | `93S7LRrJ...` | AWS Secret Access Key |
| `DATACONTRACT_S3_SESSION_TOKEN` | `AQoDYXdzEJr...` | AWS temporary session token (optional) |

`catalog`, `schema` (the Athena database), `regionName`, and `stagingDir` (required, for query results) come from the contract's `servers` block. The credentials need `athena:StartQueryExecution` plus read access to the data and write access to `stagingDir`.

## Data types

### Importing

There is no direct Athena importer. Since Athena tables live in the AWS Glue Data Catalog, use `datacontract import glue --database my_database` — Glue/Hive types map through the shared SQL mapping: `string`/`varchar`/`char` → `string`, `int`/`bigint`/`smallint`/`tinyint` → `integer`, `float`/`double`/`decimal` → `number`, `boolean` → `boolean`, `date` → `date`, `timestamp` → `timestamp`, `array<...>` → `array`, `struct<...>` → `object`, `binary` → `string` (format `binary`), `map<...>` → no logical type.

### Testing

Athena supports **native type introspection**: the declared `physicalType` is checked against the actual column type from the Athena catalog. Timezone variants of timestamps are interchangeable; parameters are only enforced when declared. A `physicalType` that isn't valid Athena SQL falls back to the logical type category comparison.
