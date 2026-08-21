---
sidebar_position: 18
title: "Snowflake"
description: "Create a data contract from your Snowflake tables and test the actual data against it — in about 5 minutes."
---

# <img className="page-icon" src="/img/icons/snowflake.svg" alt="" /> Snowflake

Go from an existing Snowflake table to a tested data contract in about five minutes: import the schema straight from Snowflake, then test the actual data against it.

## 1. Install

```bash
uv tool install --python python3.11 --upgrade 'datacontract-cli[snowflake]'
```

See [Installation](../installation.md) for pip, pipx, and Docker.

## 2. Authenticate

Create a `.env` file in your working directory (or export the variables):

```bash
# .env
DATACONTRACT_SNOWFLAKE_USERNAME=<your-username>
DATACONTRACT_SNOWFLAKE_PASSWORD=<your-password>
DATACONTRACT_SNOWFLAKE_WAREHOUSE=COMPUTE_WH
DATACONTRACT_SNOWFLAKE_ROLE=<your-role>
```

If `DATACONTRACT_SNOWFLAKE_PASSWORD` is not set, the import falls back to browser-based SSO. For key-pair authentication and other modes, see the [Snowflake Reference](../reference/snowflake.md).

## 3. Create a contract from your tables

Import the table metadata directly from Snowflake. This also generates a ready-to-test `servers` block:

```bash
datacontract import snowflake \
  --source <orgname>-<accountname> \
  --database ORDER_DB \
  --schema PUBLIC \
  --output datacontract.yaml
```

`--source` is your [account identifier](https://docs.snowflake.com/en/user-guide/admin-account-identifier) in the `<orgname>-<accountname>` format.

## 4. Test the actual data

```bash
datacontract test datacontract.yaml
```

```
Testing datacontract.yaml
Server: workspace (type=snowflake, account=..., database=ORDER_DB, schema=PUBLIC)
╭────────┬─────────────────────────────────────────────────┬─────────────────┬─────────╮
│ Result │ Check                                           │ Field           │ Details │
├────────┼─────────────────────────────────────────────────┼─────────────────┼─────────┤
│ passed │ Check that field 'order_id' is present          │ orders.order_id │         │
│ passed │ Check that field order_id has no missing values │ orders.order_id │         │
│  ...   │                                                 │                 │         │
╰────────┴─────────────────────────────────────────────────┴─────────────────┴─────────╯
🟢 data contract is valid. Run 24 checks. Took 5.2 seconds.
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

All authentication options (key-pair, SSO, connections.toml) and the data type mappings: **[Snowflake Reference](../reference/snowflake.md)**.

## Troubleshooting

- **`250001: Could not connect to Snowflake backend`** — the account identifier is wrong. Use the `<orgname>-<accountname>` format, without `.snowflakecomputing.com`.
- **`Object does not exist or not authorized`** — the role in `DATACONTRACT_SNOWFLAKE_ROLE` lacks `USAGE` on the database/schema or `SELECT` on the table.
- **Test hangs waiting for MFA** — interactive MFA pushes don't work well for repeated runs; use key-pair auth or an appropriate `DATACONTRACT_SNOWFLAKE_AUTHENTICATOR`.
