---
sidebar_position: 4
title: "Amazon S3 Tables"
description: "Import a data contract from Amazon S3 Tables and test schema and data quality through its Iceberg REST endpoint."
---

# <img className="page-icon" src="/img/icons/s3.svg" alt="" /> Amazon S3 Tables

Test an Amazon S3 Table directly through its Iceberg REST catalog. The CLI imports the table's schema, reads its data with PyIceberg, and runs schema and quality checks in DuckDB.

:::note
S3 Tables uses **`type: iceberg`**, not `type: s3`, and requires the **`iceberg` extra**. For CSV, JSON, Delta, or Parquet files in a regular S3 bucket, use the [Amazon S3 guide](./s3.md).
:::

## Before you start

Have an existing table bucket, namespace, and populated Iceberg table. The examples use `sales.orders`; replace the region, account ID, bucket, namespace, and table with your values.

This guide uses the [direct S3 Tables REST endpoint](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-tables-integrating-open-source.html), which needs no Glue integration or Athena workgroup. Your AWS identity needs `s3tables:GetTableBucket` on the bucket and `s3tables:GetTableMetadataLocation` and `s3tables:GetTableData` on the table. Listing or creating resources requires additional permissions.

## 1. Install

```bash
uv tool install --python python3.11 --upgrade 'datacontract-cli[iceberg]'
```

See [Installation](../installation.md) for other installation methods.

## 2. Sign in to AWS

For an IAM Identity Center (SSO) profile configured in the AWS CLI:

```bash
export AWS_PROFILE=my-playground-profile
aws sso login --profile "$AWS_PROFILE"
aws sts get-caller-identity
```

Check that the last command reports the intended account. The CLI uses the AWS credential chain for both the catalog and its data files. It detects the SigV4 signing service and region from the endpoint; no OAuth token or Iceberg client secret is needed.

Explicit `DATACONTRACT_S3_*` credentials override the default chain. Temporary credentials also need `DATACONTRACT_S3_SESSION_TOKEN`; see the [authentication reference](../reference/iceberg.md#amazon-s3-tables). Credentials are not stored in the imported contract.

## 3. Import the table's contract

```bash
datacontract import iceberg \
  --catalog-url https://s3tables.eu-central-1.amazonaws.com/iceberg \
  --warehouse arn:aws:s3tables:eu-central-1:123456789012:bucket/my-table-bucket \
  --catalog s3tables --namespace sales --table orders \
  --output datacontract.yaml
```

`--warehouse` takes the **table bucket ARN**, not a table ARN or an `s3://` path. The generated ODCS v3.2.0 contract contains the imported properties and this server:

```yaml
servers:
  - server: production
    type: iceberg
    catalog: s3tables
    catalogUrl: https://s3tables.eu-central-1.amazonaws.com/iceberg
    warehouse: arn:aws:s3tables:eu-central-1:123456789012:bucket/my-table-bucket
    namespace: sales
```

`--catalog` is a local catalog label, not an AWS resource name; it defaults to `default`. Alternatively, pass `--table sales.orders` without `--namespace`. The importer preserves the qualified name in `physicalName`.

All import options: [`datacontract import iceberg`](../commands/import/iceberg.md).

## 4. Test the live data

```bash
datacontract lint datacontract.yaml
datacontract test datacontract.yaml --server production
```

Lint validates the contract document; test connects to S3 Tables and checks the actual columns, logical types, required values, and other declared constraints. Imported lists, maps, and structs include nested type definitions. A passing test exits with code `0`; failed checks exit with code `1`.

For a machine-readable report:

```bash
datacontract test datacontract.yaml --server production \
  --output test-results.json --output-format json
```

## 5. Add a quality rule and prove it catches a violation

Add this `quality` block to the `orders` schema object, alongside its existing `name` and `properties`:

```yaml
quality:
  - type: sql
    description: Orders must not be empty
    query: SELECT count(*) FROM orders
    mustBeGreaterThan: 0
```

Run `datacontract test datacontract.yaml` again. For a populated table, the rule passes. To verify the failure path without changing any data, temporarily replace `mustBeGreaterThan: 0` with `mustBe: 0`. The rule now fails and the command exits with code `1`. Restore the original rule afterward.

SQL uses DuckDB's dialect and the schema object's logical `name`. If `name` is `purchases` and `physicalName` is `sales.orders`, write `FROM purchases` in the query.

## Limits and troubleshooting

- **Full-table scan:** selected tables are read into memory before checks run. Use tables that fit in available memory. SQL quality rules and row filters do not reduce the Iceberg scan.
- **Expired session:** sign in again and rerun. Data-file credentials are captured when the catalog opens and must stay valid for the scan.
- **Access denied:** confirm the account, bucket ARN, and table permissions. Catalog access alone does not prove permission to read data files.
- **Table not found:** check `namespace` and the table's `physicalName`. S3 Tables supports a single namespace level.
- **Binary columns:** ODCS has no binary logical type. Imports retain `physicalType`; presence and applicable quality checks still run, but there is no logical type check for these columns.

This is the direct S3 Tables path. The [Glue Iceberg REST endpoint](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-tables-integrating-glue-endpoint.html) has a separate setup and authorization model.

## Run the CLI's AWS integration suite

For contributors, a development checkout with the `dev` and `iceberg` extras includes an opt-in live test:

```bash
AWS_PROFILE=my-playground-profile \
DATACONTRACT_TEST_S3_TABLES_WAREHOUSE=arn:aws:s3tables:eu-central-1:123456789012:bucket/my-table-bucket \
pytest -q tests/test_test_iceberg_s3tables.py
```

This **creates and writes** a three-row table in a unique namespace, exercises import/lint/test with passing and deliberately failing contracts, then deletes its table and namespace. Use a playground bucket in the signed-in account with create, read, write, and delete permissions. AWS request and storage charges apply. Interrupted runs can leave `datacontract_e2e_*` namespaces; inspect them before cleaning them up. The normal test suite skips these AWS tests.

## Reference

- [Iceberg configuration and type handling](../reference/iceberg.md)
- [`datacontract test` command](../commands/test.md)
- [Run tests in CI/CD](../scheduling/github-actions.md)
