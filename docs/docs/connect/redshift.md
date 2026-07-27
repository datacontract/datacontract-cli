---
sidebar_position: 8
title: "Amazon Redshift"
description: "Create a data contract from your Redshift tables and test the actual data against it."
---

# <img className="page-icon" src="/img/icons/redshift.svg" alt="" /> Amazon Redshift

Test data in Amazon Redshift (both provisioned clusters and Redshift Serverless). Redshift is reached over the PostgreSQL wire protocol via the ibis Postgres backend, using username/password authentication.

## 1. Install

```bash
uv tool install --python python3.11 --upgrade 'datacontract-cli[redshift]'
```

See [Installation](../installation.md) for pip, pipx, and Docker.

## 2. Set credentials

Create a `.env` file in your working directory (or export the variables):

```bash
# .env
DATACONTRACT_REDSHIFT_USERNAME=awsuser
DATACONTRACT_REDSHIFT_PASSWORD=mysecretpassword
```

:::note
IAM-based authentication (region / access key / role ARN) is not currently supported for Redshift, because ibis connects through the generic Postgres backend rather than a Redshift-specific driver.
:::

## 3. Create a contract from your tables

Get the DDL of a table (e.g. with `SHOW TABLE my_schema.orders;` in the Redshift query editor), save it to a file, and import it:

```bash
datacontract import sql --source orders.sql --dialect redshift --output datacontract.yaml
```

The SQL import can't know your connection details, so it writes a `servers` block with placeholder values. Open `datacontract.yaml` and fill in your endpoint:

```yaml
servers:
  - server: redshift
    type: redshift
    host: my-workgroup.123456789012.us-east-1.redshift-serverless.amazonaws.com
    port: 5439
    database: dev
    schema: analytics
```

## 4. Test the actual data

```bash
datacontract test datacontract.yaml
```

```
🟢 data contract is valid. Run 24 checks. Took 4.9 seconds.
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

Run `datacontract test datacontract.yaml` again: every violation is listed as an error, and the command exits with code `1` — ready for [CI/CD scheduling](../ci-cd.md) so you catch drift before your consumers do.

## Reference

All authentication options and the data type mappings: **[Redshift Reference](../reference/redshift.md)**.

## Troubleshooting

- **Connection timeout** — the cluster/workgroup must be reachable from your machine: check **Publicly accessible**, the VPC security group's inbound rule for port `5439`, and VPN routing.
- **`password authentication failed`** — Redshift Serverless uses the namespace's admin credentials or database users; IAM users don't work over the Postgres wire protocol.
- **`relation does not exist`** — check the `schema` in the `servers` block and the user's `USAGE` grant on it.
