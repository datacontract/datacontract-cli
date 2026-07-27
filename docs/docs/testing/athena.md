---
sidebar_position: 1
title: "Amazon Athena"
description: "Create a data contract from your Athena tables and test the actual data against it."
---

# <img className="page-icon" src="/img/icons/athena.svg" alt="" /> Amazon Athena

Test data in AWS Athena stored in S3. Supports formats such as Iceberg, Parquet, JSON, and CSV.

## 1. Install

```bash
uv tool install --python python3.11 --upgrade 'datacontract-cli[athena]'
```

See [Installation](../installation.md) for pip, pipx, and Docker.

## 2. Set credentials

Athena uses the S3 environment variables. Create a `.env` file in your working directory (or export the variables):

```bash
# .env
DATACONTRACT_S3_REGION=eu-central-1
DATACONTRACT_S3_ACCESS_KEY_ID=AKIAXV5Q5QABCDEFGH
DATACONTRACT_S3_SECRET_ACCESS_KEY=93S7LRrJcqLaaaa/XXXXXXXXXXXXX
```

## 3. Create a contract from your tables

Athena tables live in the AWS Glue Data Catalog, so import them from Glue:

```bash
datacontract import glue --database my_database --table orders --output datacontract.yaml
```

The Glue import writes a `servers` entry of `type: glue`, which `datacontract test` cannot connect to directly. Replace it with an Athena server:

```yaml
servers:
  - server: athena
    type: athena
    catalog: awsdatacatalog # default
    schema: my_database     # in Athena, this is called "database"
    regionName: eu-central-1
    stagingDir: s3://my-bucket/athena-results/
```

## 4. Test the actual data

```bash
datacontract test datacontract.yaml
```

```
🟢 data contract is valid. Run 24 checks. Took 7.8 seconds.
```

## 5. Let it catch a violation

The contract becomes valuable when it detects drift. Tighten an expectation — for example, add a quality rule to a schema in `datacontract.yaml`:

```yaml
schema:
  - name: orders
    # ...
    quality:
      - type: sql
        description: No order has a negative total
        query: SELECT COUNT(*) FROM orders WHERE order_total < 0
        mustBe: 0
```

Run `datacontract test datacontract.yaml` again: every violation is listed as an error, and the command exits with code `1` — ready for [CI/CD scheduling](../ci-cd.md) so you catch drift before your consumers do.

## Reference

All authentication options and the data type mappings: **[Athena Reference](../reference/athena.md)**.

## Troubleshooting

- **`Access Denied` on query start** — the credentials need `athena:StartQueryExecution` plus write access to the `stagingDir` bucket.
- **`Table not found`** — `schema` in the `servers` block must be the Athena *database* name (as shown in the Glue Data Catalog), and `regionName` must match where the catalog lives.
- **Query results land in the wrong place** — `stagingDir` is required; Athena writes query results there before the CLI reads them.
