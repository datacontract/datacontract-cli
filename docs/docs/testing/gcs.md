---
sidebar_position: 10
title: "Google Cloud Storage"
description: "Create a data contract from files on Google Cloud Storage and test them against it."
---

# <img className="page-icon" src="/img/icons/gcs.svg" alt="" /> Google Cloud Storage (GCS)

The [Amazon S3](./s3.md) integration also works with files on Google Cloud Storage through its [interoperability](https://cloud.google.com/storage/docs/interoperability). ODCS defines no `gcs` server type, so a GCS contract uses `type: s3` with `https://storage.googleapis.com` as the endpoint URL and the `s3://` scheme for the location — `datacontract import gcs` writes exactly that.

## 1. Install

```bash
uv tool install --python python3.11 --upgrade 'datacontract-cli[gcs]'
```

See [Installation](../installation.md) for pip, pipx, and Docker.

## 2. Authenticate

Create an [HMAC key](https://cloud.google.com/storage/docs/authentication/hmackeys) for your user or service account, then create a `.env` file in your working directory (or export the variables):

```bash
# .env
DATACONTRACT_S3_ACCESS_KEY_ID=GOOG1EZZZXXXXXXXXXXXXX
DATACONTRACT_S3_SECRET_ACCESS_KEY=PDWWpbXXXXXXXXXXXXX
```

## 3. Create a contract from your files

Import the schema straight from the bucket. This also generates a ready-to-test `servers` block:

```bash
datacontract import gcs \
  --source s3://my-bucket/orders/*.json \
  --output datacontract.yaml
```

duckdb reads Google Cloud Storage through its S3-compatible endpoint, so the location uses the `s3://` scheme rather than `gs://`; a `gs://` source is rewritten for you. The format is taken from the file suffix; pass `--format` for Delta tables, which have none.

## 4. Test the actual data

```bash
datacontract test datacontract.yaml
```

```
Testing datacontract.yaml
Server: production (type=s3, format=json, location=s3://my-bucket/orders/*.json)
╭────────┬─────────────────────────────────────────────────┬─────────────────┬─────────╮
│ Result │ Check                                           │ Field           │ Details │
├────────┼─────────────────────────────────────────────────┼─────────────────┼─────────┤
│ passed │ Check that field 'order_id' is present          │ orders.order_id │         │
│ passed │ Check that field order_id has no missing values │ orders.order_id │         │
│  ...   │                                                 │                 │         │
╰────────┴─────────────────────────────────────────────────┴─────────────────┴─────────╯
🟢 data contract is valid. Run 24 checks. Took 3.1 seconds.
```

## 5. Let it catch a violation

The contract becomes valuable when it detects drift. Tighten an expectation — for example, mark a field as `required: true` that occasionally arrives empty, or add a quality rule:

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

All authentication options and the data type handling per file format: **[GCS Reference](../reference/gcs.md)**.

## Troubleshooting

- **`403 Forbidden`** — the HMAC key's principal lacks `storage.objects.get`/`storage.objects.list` on the bucket, or the key was deactivated.
- **`No files found that match the pattern`** — the `location` must use the `s3://` scheme (not `gs://`), and `endpointUrl` must be `https://storage.googleapis.com`.
