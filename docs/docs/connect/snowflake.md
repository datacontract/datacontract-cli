---
sidebar_position: 16
title: "Snowflake"
description: "Test data in Snowflake."
---

<img className="page-icon" src="/img/icons/snowflake.svg" alt="" />

# Snowflake

Test data in Snowflake.

## Server

```yaml
servers:
  - server: snowflake
    type: snowflake
    account: abcdefg-xn12345
    database: ORDER_DB
    schema: ORDERS_PII_V2
```

`account`, `database`, and `schema` come from the `servers` section above.

## Environment variables

Any `DATACONTRACT_SNOWFLAKE_`-prefixed variable is passed (lowercased, prefix stripped) as a connection parameter to the [snowflake-connector-python](https://docs.snowflake.com/en/developer-guide/python-connector/python-connector-api#connect) driver. Set the variables required by your workspace's `authenticator` mode.

| Connection parameter | Environment variable |
|---|---|
| `username` | `DATACONTRACT_SNOWFLAKE_USERNAME` |
| `password` | `DATACONTRACT_SNOWFLAKE_PASSWORD` |
| `warehouse` | `DATACONTRACT_SNOWFLAKE_WAREHOUSE` |
| `role` | `DATACONTRACT_SNOWFLAKE_ROLE` |
| `connection_timeout` | `DATACONTRACT_SNOWFLAKE_CONNECTION_TIMEOUT` |
| `authenticator` | `DATACONTRACT_SNOWFLAKE_AUTHENTICATOR` |
| `private_key` | `DATACONTRACT_SNOWFLAKE_PRIVATE_KEY` |
| `private_key_passphrase` | `DATACONTRACT_SNOWFLAKE_PRIVATE_KEY_PASSPHRASE` |
| `private_key_path` | `DATACONTRACT_SNOWFLAKE_PRIVATE_KEY_PATH` |

Requires the `snowflake` extra.
