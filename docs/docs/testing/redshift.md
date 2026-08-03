---
sidebar_position: 2
title: "Amazon Redshift"
description: "Create a data contract from your Redshift tables and test the actual data against it — in about 5 minutes."
---

# <img className="page-icon" src="/img/icons/redshift.svg" alt="" /> Amazon Redshift

Go from an existing Redshift table to a tested data contract in about five minutes: import the schema straight from Redshift, then test the actual data against it. Works with provisioned clusters and Redshift Serverless — both are reached over the PostgreSQL wire protocol.

## 1. Install

```bash
uv tool install --python python3.11 --upgrade 'datacontract-cli[redshift]'
```

See [Installation](../installation.md) for pip, pipx, and Docker.

## 2. Authenticate

The easiest way is IAM — sign in to AWS once and the CLI requests temporary database credentials itself, so no database password is stored anywhere and nothing else has to be configured:

```bash
aws sso login   # or any other way of getting an AWS session
```

Your AWS identity needs `redshift-serverless:GetCredentials` (Serverless) or `redshift:GetClusterCredentialsWithIAM` (provisioned cluster), and the resulting database user needs `USAGE` on the schema plus `SELECT` on the tables.

Prefer a database user? Set the credentials directly and they are used instead:

```bash
# .env
DATACONTRACT_REDSHIFT_USERNAME=awsuser
DATACONTRACT_REDSHIFT_PASSWORD=mysecretpassword
```

The CLI picks the method from what you configured: a password means a database login, otherwise it uses your AWS session. Either way, `import` and `test` use the same setup. For custom domains, VPC endpoints, and the full list of options, see the [Redshift Reference](../reference/redshift.md).

## 3. Create a contract from your tables

Import the table metadata directly from the Redshift catalog. This also generates a ready-to-test `servers` block:

```bash
datacontract import redshift \
  --source my-workgroup.123456789012.us-east-1.redshift-serverless.amazonaws.com \
  --database dev \
  --schema analytics \
  --table orders \
  --output datacontract.yaml
```

`--source` is the endpoint host of your cluster or serverless workgroup (without the trailing `:5439/dev` that the console shows). Repeat `--table` for multiple tables, or omit it to import every table in the schema.

## 4. Test the actual data

```bash
datacontract test datacontract.yaml
```

```
Testing datacontract.yaml
Server: redshift (type=redshift, host=my-workgroup..., database=dev, schema=analytics)
╭────────┬─────────────────────────────────────────────────┬─────────────────┬─────────╮
│ Result │ Check                                           │ Field           │ Details │
├────────┼─────────────────────────────────────────────────┼─────────────────┼─────────┤
│ passed │ Check that field 'order_id' is present          │ orders.order_id │         │
│ passed │ Check that field order_id has no missing values │ orders.order_id │         │
│  ...   │                                                 │                 │         │
╰────────┴─────────────────────────────────────────────────┴─────────────────┴─────────╯
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

Run `datacontract test datacontract.yaml` again: every violation is listed as an error, and the command exits with code `1` — ready for [CI/CD and scheduled runs](../scheduling/index.md) so you catch drift before your consumers do.

## Reference

All authentication options and the data type mappings: **[Redshift Reference](../reference/redshift.md)**.

## Troubleshooting

- **Connection timeout** — the cluster/workgroup must be reachable from your machine: check **Publicly accessible**, the VPC security group's inbound rule for port `5439`, and VPN routing.
- **`password authentication failed`** — Redshift Serverless expects the namespace's admin credentials or a database user; an IAM user name is not a database user. Unset `DATACONTRACT_REDSHIFT_PASSWORD` to sign in with your AWS identity instead.
- **`Could not obtain temporary Redshift credentials`** — the AWS identity may call the wrong region (set `DATACONTRACT_REDSHIFT_REGION`) or lack `GetCredentials` / `GetClusterCredentialsWithIAM` permission.
- **`Using the login credential provider requires an additional dependency`** — your AWS profile uses the `aws login` flow, which needs `pip install "botocore[crt]"` in the same environment as the CLI.
- **`relation does not exist`** — check the `schema` in the `servers` block and the user's `USAGE` grant on it.
- **The import finds no tables** — `--schema` is case-sensitive and must match the schema as stored in the catalog; external schemas need the `SVV_EXTERNAL_*` permissions granted to your user.
