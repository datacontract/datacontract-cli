---
sidebar_position: 25
title: "Import: Snowflake"
description: "Create a data contract from a Snowflake workspace."
---

# <img className="page-icon" src="/img/icons/snowflake.svg" alt="" /> Import: Snowflake

Creates a data contract from a Snowflake workspace by reading table metadata from `INFORMATION_SCHEMA` — including schemas, column types, primary keys, and comments.

```bash
datacontract import snowflake \
  --source <orgname>-<accountname> \
  --database ORDER_DB \
  --schema PUBLIC \
  --output datacontract.yaml
```

`--source` is your [account identifier](https://docs.snowflake.com/en/user-guide/admin-account-identifier).

The generated contract includes a ready-to-test `servers` block, so you can run `datacontract test datacontract.yaml` immediately afterwards — see the **[Snowflake connection guide](../testing/snowflake.md)** for credentials, the full 5-minute walkthrough, and troubleshooting.

Credentials are provided as environment variables (`DATACONTRACT_SNOWFLAKE_USERNAME`, `DATACONTRACT_SNOWFLAKE_PASSWORD`, `DATACONTRACT_SNOWFLAKE_ROLE`, `DATACONTRACT_SNOWFLAKE_WAREHOUSE`). If no password is set, the import falls back to browser-based SSO. Key-pair auth and `connections.toml` are also supported — see the [Snowflake Reference](../reference/snowflake.md).

All options: **[`datacontract import snowflake`](../commands/import/snowflake.md)**.
