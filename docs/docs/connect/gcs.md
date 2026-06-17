---
sidebar_position: 8
title: "Google Cloud Storage"
description: "Test files on Google Cloud Storage via S3 interoperability."
---

# Google Cloud Storage (GCS)

The [Amazon S3](./s3.md) integration also works with files on Google Cloud Storage through its [interoperability](https://cloud.google.com/storage/docs/interoperability). Use `https://storage.googleapis.com` as the endpoint URL and the `s3://` scheme for the location.

## Server

```yaml
servers:
  - server: production
    type: s3
    endpointUrl: https://storage.googleapis.com
    location: s3://bucket-name/path/*/*.json # use s3:// instead of gs://
    format: json
    delimiter: new_line # new_line, array, or none
```

## Environment variables

| Variable | Example | Description |
|---|---|---|
| `DATACONTRACT_S3_ACCESS_KEY_ID` | `GOOG1EZZZ...` | The GCS [HMAC Key](https://cloud.google.com/storage/docs/authentication/hmackeys) ID |
| `DATACONTRACT_S3_SECRET_ACCESS_KEY` | `PDWWpb...` | The GCS [HMAC Key](https://cloud.google.com/storage/docs/authentication/hmackeys) secret |

Requires the `gcs` / `duckdb` extra.
