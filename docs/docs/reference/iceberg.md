---
sidebar_position: 4
title: "Apache Iceberg Reference"
sidebar_label: "Apache Iceberg"
description: "Authentication and data type handling for Apache Iceberg REST catalogs."
---

# <img className="page-icon" src="/img/icons/iceberg.svg" alt="" /> Apache Iceberg Reference

Authentication and data type handling for [Apache Iceberg connections](../testing/iceberg.md).

## Server

```yaml
servers:
  - server: production
    type: iceberg
    catalog: main                                       # the catalog's name
    catalogUrl: https://polaris.example.com/api/catalog # the REST catalog endpoint
    namespace: sales                                    # optional; prefixed to every table name
    warehouse: s3://warehouse                           # optional; passed to the catalog
```

## Configuration

| Environment variable | Purpose |
|---|---|
| `DATACONTRACT_ICEBERG_CREDENTIAL` | OAuth2 client credential for the catalog, as `client_id:client_secret` |
| `DATACONTRACT_ICEBERG_TOKEN` | Bearer token for the catalog, instead of a credential |
| `DATACONTRACT_ICEBERG_CATALOG_URL`, `DATACONTRACT_ICEBERG_CATALOG`, `DATACONTRACT_ICEBERG_NAMESPACE`, `DATACONTRACT_ICEBERG_WAREHOUSE` | Override the matching field of the contract's `servers` block |
| `DATACONTRACT_ICEBERG_CATALOG_TYPE` | The pyiceberg catalog implementation: `rest` (default), `sql`, `glue`, `hive`, `dynamodb`. For `sql`, `catalogUrl` is the SQLAlchemy connection URI |
| `DATACONTRACT_S3_ACCESS_KEY_ID`, `DATACONTRACT_S3_SECRET_ACCESS_KEY`, `DATACONTRACT_S3_SESSION_TOKEN`, `DATACONTRACT_S3_REGION` | Credentials for S3 data files and AWS catalog signing; omit to use the AWS credential chain with S3 Tables or Glue |
| `DATACONTRACT_ICEBERG_S3_ENDPOINT` | Endpoint of an S3-compatible store (MinIO, Ceph) holding the data files |
| `DATACONTRACT_ICEBERG_SIGNING_NAME` | Sign catalog requests with SigV4 for this AWS service (`s3tables`, `glue`); detected from `catalogUrl` for the AWS endpoints, so only needed behind a proxy |
| `DATACONTRACT_ICEBERG_PROPERTIES` | Extra pyiceberg catalog properties, as a JSON object or `key=value,key=value` |

## Amazon S3 Tables

S3 Tables exposes each table bucket as an Iceberg REST catalog. `catalogUrl` is the regional endpoint, `warehouse` the **table bucket ARN** (not an `s3://` location), and `namespace` the S3 Tables namespace. The CLI detects the signing service and region from the endpoint. AWS uses SigV4, not OAuth, for this endpoint; see the [AWS endpoint documentation](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-tables-integrating-open-source.html).

For installation, AWS SSO sign-in, import/test commands, and a quality-check example, follow the dedicated [Amazon S3 Tables testing guide](../testing/s3-tables.md).

Use your own region, account, bucket, namespace, and an existing populated table. No Glue integration, Athena workgroup, or OAuth token is required for this direct endpoint. For import and testing, the identity needs `s3tables:GetTableBucket` on the bucket and `s3tables:GetTableMetadataLocation` and `s3tables:GetTableData` on the table. Listing, creating, or modifying tables requires additional permissions; AWS documents the [operation-to-permission mapping](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-tables-integrating-open-source.html#endpoint-supported-api).

The CLI resolves the AWS credential chain, including `AWS_PROFILE`, and forwards credentials to the Arrow data-file reader as well as signing catalog requests. Explicit `DATACONTRACT_S3_*` credentials take precedence; temporary credentials require `DATACONTRACT_S3_SESSION_TOKEN`. Credentials are not written into the imported contract. Data-file credentials are captured when the catalog is opened, so they must remain valid for the scan; reauthenticate and rerun if they expire. Do not rely on this direct endpoint vending data-file credentials.

The generated server looks like this (the local catalog label defaults to `default`; use `--catalog s3tables` to name it):

```yaml
servers:
  - server: production
    type: iceberg
    catalog: s3tables
    catalogUrl: https://s3tables.eu-central-1.amazonaws.com/iceberg
    warehouse: arn:aws:s3tables:eu-central-1:123456789012:bucket/my-table-bucket
    namespace: sales
```

You can also pass `--table sales.orders` without `--namespace`. The importer preserves that qualified name in the schema object's `physicalName`. S3 Tables supports one namespace level.

The AWS Glue Data Catalog's Iceberg REST endpoint (`https://glue.<region>.amazonaws.com/iceberg`) also uses SigV4, but has different warehouse identifiers and authorization requirements. For S3 Tables through Glue, follow the [AWS Glue endpoint setup](https://docs.aws.amazon.com/AmazonS3/latest/userguide/s3-tables-integrating-glue-endpoint.html); it is a separate path from the direct S3 Tables endpoint above.

### Run the AWS integration test

The testing guide documents [running the opt-in AWS integration suite](../testing/s3-tables.md#run-the-clis-aws-integration-suite), including its resource creation, cleanup, and permission requirements.

The full list is on the [Configuration](../configuration.md) page.

## Data types

### Importing

`datacontract import iceberg` reads the table schema from the catalog (or from a schema JSON file with `--source`):

| Iceberg type | `logicalType` |
|---|---|
| `string`, `uuid` | `string` |
| `int`, `long` | `integer` |
| `float`, `double`, `decimal(p,s)` | `number` |
| `boolean` | `boolean` |
| `date` | `date` |
| `timestamp`, `timestamptz` | `timestamp` |
| `time` | `time` |
| `struct<...>` | `object` with `properties` |
| `list<...>` | `array` with `items` |
| `map<k,v>` | `map` with `key` and `value` |
| `binary`, `fixed` | No `logicalType`; retained as `physicalType` because ODCS has no binary logical type |

The Iceberg type is kept as `physicalType`, and the field id as the `icebergFieldId` custom property.

### Testing

The table is scanned to Arrow and registered in DuckDB, so the type checks compare the declared `logicalType` against the DuckDB type of the Arrow column: structs become `STRUCT`, lists `LIST`, and maps `MAP`, which the nested type checks walk. `physicalType` checks against the catalog's declared type are not run for Iceberg; the logical type check runs instead. Binary fields still get presence and applicable quality checks, but no logical type check.

SQL quality queries address the schema object's logical `name`, even when `physicalName` points to a different or qualified catalog table. The CLI reads the full selected tables into memory before checking them; use tables that fit in available memory. SQL rules and `--filters` do not reduce the Iceberg scan.

### Exporting

`datacontract export iceberg` writes an Iceberg schema JSON from the contract. See the [Iceberg export guide](../exports/iceberg.md) for the mapping; import/export is not a lossless round-trip of every physical type.
