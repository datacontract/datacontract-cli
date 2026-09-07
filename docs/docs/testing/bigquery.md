---
sidebar_position: 10
title: "Google BigQuery"
description: "Create a data contract from your BigQuery tables and test the actual data against it — in about 5 minutes."
---

# <img className="page-icon" src="/img/icons/bigquery.svg" alt="" /> Google BigQuery

Go from an existing BigQuery table to a tested data contract in about five minutes: import the schema straight from BigQuery, then test the actual data against it.

## 1. Install

```bash
uv tool install --python python3.11 --upgrade 'datacontract-cli[bigquery]'
```

See [Installation](../installation.md) for pip, pipx, and Docker.

## 2. Authenticate

The easiest way is Application Default Credentials (ADC) — both `import` and `test` pick them up automatically:

```bash
gcloud auth application-default login
```

Your account (or service account) needs the **BigQuery Job User** and **BigQuery Data Viewer** roles. For service-account key files and CI/CD, see the [BigQuery Reference](../reference/bigquery.md).

## 3. Create a contract from your tables

Import the table metadata directly from the BigQuery API. This also generates a ready-to-test `servers` block:

```bash
datacontract import bigquery \
  --project my-project \
  --dataset my_dataset \
  --table orders \
  --output datacontract.yaml
```

Repeat `--table` for multiple tables, or omit it to import every table in the dataset.

## 4. Test the actual data

```bash
datacontract test datacontract.yaml
```

```
Testing datacontract.yaml
Server: bigquery (type=bigquery, project=my-project, dataset=my_dataset)
╭────────┬─────────────────────────────────────────────────┬─────────────────┬─────────╮
│ Result │ Check                                           │ Field           │ Details │
├────────┼─────────────────────────────────────────────────┼─────────────────┼─────────┤
│ passed │ Check that field 'order_id' is present          │ orders.order_id │         │
│ passed │ Check that field order_id has no missing values │ orders.order_id │         │
│  ...   │                                                 │                 │         │
╰────────┴─────────────────────────────────────────────────┴─────────────────┴─────────╯
🟢 data contract is valid. Run 24 checks. Took 6.1 seconds.
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

All authentication options (service-account keys, WIF, billing project) and the data type mappings: **[BigQuery Reference](../reference/bigquery.md)**.

## Troubleshooting

- **`Your default credentials were not found`** — run `gcloud auth application-default login`, or set `GOOGLE_APPLICATION_CREDENTIALS` / `DATACONTRACT_BIGQUERY_ACCOUNT_INFO_JSON_PATH` to a service-account key file.
- **`403 Access Denied`** — the account is missing **BigQuery Job User** (to run query jobs) or **BigQuery Data Viewer** (to read the tables).
- **Queries billed to the wrong project** — set `DATACONTRACT_BIGQUERY_BILLING_PROJECT`.
