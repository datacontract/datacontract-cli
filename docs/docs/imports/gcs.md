---
sidebar_position: 13
title: "Import: Google Cloud Storage"
description: "Create a data contract from files in Google Cloud Storage."
---

# <img className="page-icon" src="/img/icons/gcs.svg" alt="" /> Import: Google Cloud Storage

Creates a data contract from files in Google Cloud Storage, in CSV, JSON, Parquet, or Delta format.

```bash
datacontract import gcs \
  --source s3://my-bucket/orders/*.json \
  --output datacontract.yaml
```

The format is taken from the file suffix; pass `--format` for Delta tables, which have none, or to override the guess. `--delimiter` pins how a JSON file is laid out (`new_line`, `array`, or `none`) instead of letting it be detected.

duckdb reads Google Cloud Storage through its S3-compatible endpoint, so the location uses the `s3://` scheme rather than `gs://`.

The objects are read with duckdb through the same connection the test path uses, so the import authenticates identically and infers the column types from exactly the reader that later verifies them.

The generated contract includes a ready-to-test `servers` block, so you can run `datacontract test datacontract.yaml` immediately afterwards — see the **[Google Cloud Storage connection guide](../testing/gcs.md)** for the full 5-minute walkthrough and troubleshooting.

Credentials are the same ones `datacontract test` uses — see the [Google Cloud Storage Reference](../reference/gcs.md).
