---
sidebar_position: 4
title: "Apache Iceberg"
description: "Test Apache Iceberg tables through a REST catalog (Polaris, Nessie, Unity Catalog, Glue, S3 Tables) in 5 minutes."
---

# <img className="page-icon" src="/img/icons/iceberg.svg" alt="" /> Apache Iceberg

Test Apache Iceberg tables through a REST catalog such as Polaris, Nessie, Unity Catalog, AWS Glue, or Amazon S3 Tables. The CLI loads each table with [pyiceberg](https://py.iceberg.apache.org/), scans it to Arrow, and runs the checks in DuckDB. For S3 Tables and Glue the requests are signed with your AWS credentials; see the [reference](../reference/iceberg.md#amazon-s3-tables).

## 1. Install

```bash
uv tool install --python python3.11 --upgrade 'datacontract-cli[iceberg]'
```

See [Installation](../installation.md) for pip, pipx, and Docker.

## 2. Authenticate

For **Amazon S3 Tables or AWS Glue**, use AWS credentials, not OAuth. The [S3 Tables walkthrough](../reference/iceberg.md#amazon-s3-tables) covers `AWS_PROFILE`, SSO login, the table bucket ARN, and import/test commands.

For **OAuth-based REST catalogs**, the catalog and data-file authentication are separate. Supply a client credential or bearer token as required by your catalog; data files on S3 use the same `DATACONTRACT_S3_*` options as the [S3](./s3.md) source, unless the catalog vends credentials.

```bash
# catalog: one of
export DATACONTRACT_ICEBERG_CREDENTIAL=client_id:client_secret
export DATACONTRACT_ICEBERG_TOKEN=eyJ...

# data files (skip when the catalog vends credentials)
export DATACONTRACT_S3_ACCESS_KEY_ID=...
export DATACONTRACT_S3_SECRET_ACCESS_KEY=...
export DATACONTRACT_S3_REGION=eu-central-1
```

## 3. Create a contract from a table

```bash
datacontract import iceberg --catalog-url https://polaris.example.com/api/catalog \
  --catalog main --namespace sales --table orders --output datacontract.yaml
```

The contract gets the table's schema, with `map`, `list`, and `struct` columns expanded, and a ready-to-test `servers` block:

```yaml
servers:
  - server: production
    type: iceberg
    catalog: main
    catalogUrl: https://polaris.example.com/api/catalog
    namespace: sales
```

`datacontract import iceberg --source schema.json` still imports from a schema file, without a server.

## 4. Test the actual data

```bash
datacontract test datacontract.yaml
```

Each schema object is one table in the namespace. A `physicalName` on the schema object names the table when it differs from the schema name; a name with a dot is used as the full identifier.

## 5. Let it catch a violation

Add a `quality` rule to the contract and run the test again:

```yaml
    quality:
      - type: sql
        description: No order without lines
        query: SELECT count(*) FROM orders WHERE cardinality(lines) = 0
        mustBe: 0
```

The query runs in DuckDB against the scanned table, so DuckDB's SQL dialect applies. Use the schema object's logical `name` in SQL, not its `physicalName`. The full selected tables are read into memory before the checks run.

## Reference

All options and the data type handling: **[Apache Iceberg Reference](../reference/iceberg.md)**.

## Troubleshooting

- **`catalogUrl is required`** — the server needs the REST endpoint in `catalogUrl`, or `DATACONTRACT_ICEBERG_CATALOG_URL`.
- **`Table 'sales.orders' was not found`** — check `namespace`; the identifier the CLI asked for is in the message.
- **Expired AWS SSO session** — run `aws sso login --profile "$AWS_PROFILE"` again and retry. Check the selected account with `aws sts get-caller-identity`.
- **`403` while reading S3 Tables data files** — verify `s3tables:GetTableData` on the table and that temporary credentials include their session token. A successful catalog connection does not prove data-file access.
- **`403` with other catalogs** — check the data-file credentials (`DATACONTRACT_S3_*`) or the catalog's credential-vending configuration.
