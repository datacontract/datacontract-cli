---
sidebar_position: 1
title: "Import: Amazon Athena"
description: "Create a data contract from an Amazon Athena database."
---

# <img className="page-icon" src="/img/icons/athena.svg" alt="" /> Import: Amazon Athena

Creates a data contract from an Amazon Athena database, including column types, partition keys, and comments.

```bash
datacontract import athena \
  --schema my_database \
  --staging-dir s3://my-bucket/athena-results/ \
  --region eu-central-1 \
  --output datacontract.yaml
```

`--schema` is the Athena database. Repeat `--table` to import only specific tables (by default every table in the database is imported), and set `--catalog` if you don't use `awsdatacatalog`.

`--staging-dir` is the S3 location Athena writes query results to. `datacontract test` needs it, so the import writes it into the `servers` block.

Athena keeps its table metadata in the AWS Glue Data Catalog, so the import reads the catalog rather than querying Athena — it needs only `glue:GetTables`, costs nothing to run, and requires no query results to be staged. Glue stores the Hive spelling of two types, which the import rewrites to what Athena reports back (`string` → `varchar`, `binary` → `varbinary`) so the physical type checks pass on the first test run.

The generated contract includes a ready-to-test `servers` block, so you can run `datacontract test datacontract.yaml` immediately afterwards — see the **[Athena connection guide](../testing/athena.md)** for the full 5-minute walkthrough and troubleshooting.

Credentials are provided as environment variables and are the same ones `datacontract test` uses: `DATACONTRACT_S3_REGION`, `DATACONTRACT_S3_ACCESS_KEY_ID`, and `DATACONTRACT_S3_SECRET_ACCESS_KEY` — see the [Athena Reference](../reference/athena.md).

Want the Glue Data Catalog itself rather than Athena? Use [`datacontract import glue`](./glue.md).
