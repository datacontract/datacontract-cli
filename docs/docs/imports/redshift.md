---
sidebar_position: 16
title: "Import: Amazon Redshift"
description: "Create a data contract from an Amazon Redshift schema."
---

# <img className="page-icon" src="/img/icons/redshift.svg" alt="" /> Import: Amazon Redshift

Creates a data contract from an Amazon Redshift schema by reading table metadata from the `SVV_TABLES` and `SVV_COLUMNS` catalog views — including column types with length and precision, nullability, primary keys, and comments. Works with provisioned clusters and Redshift Serverless, and covers local tables, views, and external (Spectrum) tables.

```bash
datacontract import redshift \
  --source my-workgroup.123456789012.us-east-1.redshift-serverless.amazonaws.com \
  --database dev \
  --schema analytics \
  --output datacontract.yaml
```

`--source` is the endpoint host of your cluster or serverless workgroup. Add `--port` if it doesn't listen on the default `5439`, and repeat `--table` to import only specific tables (by default every table in the schema is imported).

The generated contract includes a ready-to-test `servers` block, so you can run `datacontract test datacontract.yaml` immediately afterwards — see the **[Redshift connection guide](../testing/redshift.md)** for credentials, the full 5-minute walkthrough, and troubleshooting.

Credentials are provided as environment variables and are the same ones `datacontract test` uses: either IAM (`DATACONTRACT_REDSHIFT_AUTHENTICATION=iam`, which requests temporary credentials from your AWS session) or a database user (`DATACONTRACT_REDSHIFT_USERNAME`, `DATACONTRACT_REDSHIFT_PASSWORD`) — see the [Redshift Reference](../reference/redshift.md).
