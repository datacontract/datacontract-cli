---
sidebar_position: 1
title: "Amazon Athena"
description: "Create a data contract from your Athena tables and test the actual data against it — in about 5 minutes."
---

# <img className="page-icon" src="/img/icons/athena.svg" alt="" /> Amazon Athena

Go from an existing Athena table to a tested data contract in about five minutes: import the schema straight from the catalog, then test the actual data against it. Athena reads data in S3, so this covers formats such as Iceberg, Parquet, JSON, and CSV.

## 1. Install

```bash
uv tool install --python python3.11 --upgrade 'datacontract-cli[athena]'
```

See [Installation](../installation.md) for pip, pipx, and Docker.

## 2. Authenticate

The easiest way is to sign in to AWS once — the CLI picks the session up, so no key is stored anywhere and nothing else has to be configured:

```bash
aws sso login   # or any other way of getting an AWS session
```

Prefer static keys? Set them directly and they are used instead:

```bash
# .env
DATACONTRACT_S3_REGION=eu-central-1
DATACONTRACT_S3_ACCESS_KEY_ID=AKIAXV5Q5QABCDEFGH
DATACONTRACT_S3_SECRET_ACCESS_KEY=93S7LRrJcqLaaaa/XXXXXXXXXXXXX
```

Either way, your AWS identity needs `glue:GetTables` to import, and `athena:StartQueryExecution` plus read access to the data and write access to the staging directory to test. `import` and `test` use the same setup.

## 3. Create a contract from your tables

Import the table metadata directly from the catalog. This also generates a ready-to-test `servers` block:

```bash
datacontract import athena \
  --schema my_database \
  --staging-dir s3://my-bucket/athena-results/ \
  --region eu-central-1 \
  --table orders \
  --output datacontract.yaml
```

`--schema` is the Athena database. Repeat `--table` for multiple tables, or omit it to import every table in the database. `--catalog` defaults to `awsdatacatalog`.

`--staging-dir` is where Athena writes query results; `datacontract test` needs it, so the import asks for it up front and writes it into the contract.

## 4. Test the actual data

```bash
datacontract test datacontract.yaml
```

```
Testing datacontract.yaml
Server: athena (type=athena, catalog=awsdatacatalog, schema=my_database, regionName=eu-central-1)
╭────────┬─────────────────────────────────────────────────┬─────────────────┬─────────╮
│ Result │ Check                                           │ Field           │ Details │
├────────┼─────────────────────────────────────────────────┼─────────────────┼─────────┤
│ passed │ Check that field 'order_id' is present          │ orders.order_id │         │
│ passed │ Check that field order_id has no missing values │ orders.order_id │         │
│  ...   │                                                 │                 │         │
╰────────┴─────────────────────────────────────────────────┴─────────────────┴─────────╯
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

Run `datacontract test datacontract.yaml` again: every violation is listed as an error, and the command exits with code `1` — ready for [CI/CD and scheduled runs](../scheduling/index.md) so you catch drift before your consumers do.

## Reference

All authentication options and the data type mappings: **[Athena Reference](../reference/athena.md)**.

Since ODCS v3.2.0 the server may name a `workgroup` (override: `DATACONTRACT_ATHENA_WORKGROUP`). A workgroup can enforce the query result location, so `stagingDir` is optional when one is set.

## Troubleshooting

- **`Access Denied` on query start** — the credentials need `athena:StartQueryExecution` plus write access to the `stagingDir` bucket.
- **`Table not found`** — `schema` in the `servers` block must be the Athena *database* name (as shown in the Glue Data Catalog), and `regionName` must match where the catalog lives.
- **`Your session has expired`** — the AWS session has lapsed; run `aws sso login` again. No `DATACONTRACT_S3_*` variable is needed when a session is present.
