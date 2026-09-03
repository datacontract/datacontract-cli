---
sidebar_position: 16
title: "Snowflake Reference"
sidebar_label: "Snowflake"
description: "All Snowflake authentication options and data type mappings."
---

# <img className="page-icon" src="/img/icons/snowflake.svg" alt="" /> Snowflake Reference

Authentication options and data type handling for [Snowflake connections](../testing/snowflake.md).

## Server

```yaml
servers:
  - server: snowflake
    type: snowflake
    account: abcdefg-xn12345
    database: ORDER_DB
    schema: ORDERS_PII_V2
```

## Authentication

Any `DATACONTRACT_SNOWFLAKE_`-prefixed variable is passed (lowercased, prefix stripped) as a connection parameter to the [snowflake-connector-python](https://docs.snowflake.com/en/developer-guide/python-connector/python-connector-api#connect) driver. Set the variables required by your workspace's `authenticator` mode.

| Connection parameter | Environment variable |
|---|---|
| `user` | `DATACONTRACT_SNOWFLAKE_USERNAME` (also `..._USER`) |
| `password` | `DATACONTRACT_SNOWFLAKE_PASSWORD` |
| `warehouse` | `DATACONTRACT_SNOWFLAKE_WAREHOUSE` |
| `role` | `DATACONTRACT_SNOWFLAKE_ROLE` |
| `authenticator` | `DATACONTRACT_SNOWFLAKE_AUTHENTICATOR` |
| `private_key_file` | `DATACONTRACT_SNOWFLAKE_PRIVATE_KEY_FILE` |
| `private_key_file_pwd` | `DATACONTRACT_SNOWFLAKE_PRIVATE_KEY_FILE_PWD` |
| `private_key` | `DATACONTRACT_SNOWFLAKE_PRIVATE_KEY` |
| `login_timeout` | `DATACONTRACT_SNOWFLAKE_LOGIN_TIMEOUT` |
| `network_timeout` | `DATACONTRACT_SNOWFLAKE_NETWORK_TIMEOUT` |
| `socket_timeout` | `DATACONTRACT_SNOWFLAKE_SOCKET_TIMEOUT` |

`account`, `database`, and `schema` come from the contract's `servers` block, and can be overridden with `DATACONTRACT_SNOWFLAKE_ACCOUNT`, `DATACONTRACT_SNOWFLAKE_DATABASE`, and `DATACONTRACT_SNOWFLAKE_SCHEMA`.

For key-pair auth, set `DATACONTRACT_SNOWFLAKE_PRIVATE_KEY_FILE` to the path of the key file and `..._PRIVATE_KEY_FILE_PWD` to its passphrase, if it has one. `..._PRIVATE_KEY` takes the key itself rather than a path.

:::warning
The variable name after the prefix must match the driver's parameter name exactly. The driver ignores parameters it does not recognise without raising, so a misspelled variable is silently dropped and the connection then fails for an unrelated-looking reason — a mistyped key-pair variable surfaces as an authentication error, not as a bad-parameter error.
:::

### Deprecated variables

Earlier versions documented three names the driver has never accepted, so setting them had no effect. They now work as synonyms and log a deprecation warning; set the replacement instead. If both are set, the replacement wins.

| Deprecated | Use instead |
|---|---|
| `DATACONTRACT_SNOWFLAKE_PRIVATE_KEY_PATH` | `DATACONTRACT_SNOWFLAKE_PRIVATE_KEY_FILE` |
| `DATACONTRACT_SNOWFLAKE_PRIVATE_KEY_PASSPHRASE` | `DATACONTRACT_SNOWFLAKE_PRIVATE_KEY_FILE_PWD` |
| `DATACONTRACT_SNOWFLAKE_CONNECTION_TIMEOUT` | `DATACONTRACT_SNOWFLAKE_LOGIN_TIMEOUT` |

### Import-specific options

`datacontract import snowflake` additionally supports:

| Variable | Description |
|---|---|
| `DATACONTRACT_SNOWFLAKE_HOME` | Directory containing a [connections.toml](https://docs.snowflake.com/en/developer-guide/python-connector/python-connector-connect#connecting-using-the-connections-toml-file) |
| `DATACONTRACT_SNOWFLAKE_CONNECTIONS_FILE` | Path to a connections.toml file |
| `DATACONTRACT_SNOWFLAKE_DEFAULT_CONNECTION_NAME` | Connection name within connections.toml |

The `SNOWFLAKE_`-prefixed equivalents work as fallbacks. If no password is set, the import falls back to browser-based SSO (`externalbrowser`).

## Data types

### Importing

`datacontract import snowflake` reads `INFORMATION_SCHEMA.COLUMNS` and maps types as follows. The `physicalType` keeps the full native type including length/precision (e.g. `NUMBER(38, 0)`, `TEXT(16777216)`).

| Snowflake type | `logicalType` | Notes |
|---|---|---|
| `TEXT`, `VARCHAR` | `string` | `maxLength` from `CHARACTER_MAXIMUM_LENGTH` |
| `NUMBER` (incl. `INT`/`BIGINT` aliases) | `number` | precision/scale as custom properties |
| `FLOAT`, `DOUBLE` | `number` | |
| `BOOLEAN` | `boolean` | |
| `DATE` | `date` | |
| `TIMESTAMP_NTZ` / `_LTZ` / `_TZ` | `timestamp` | |
| `TIME` | `time` | |
| `BINARY` | `string` (format `binary`) | |
| `ARRAY` | `array` | |
| `VARIANT`, `OBJECT`, `GEOGRAPHY`, `GEOMETRY` | *(unset)* | `physicalType` is still written |

Columns also get `required` (from `IS_NULLABLE`), `unique` (from `IS_IDENTITY`), and custom properties for `ordinalPosition`, `default`, `precision`, `scale`, `characterSet`, and `collation`.

### Testing

Snowflake supports **native type introspection**: the declared `physicalType` is checked against the actual catalog type. Snowflake-specific leniency: `VARCHAR`/`TEXT`/`NVARCHAR` are treated as the same family, as are `DECIMAL`/`INT`/`BIGINT`/`SMALLINT`/`TINYINT` (Snowflake stores all of them as `NUMBER`), and `DOUBLE`/`FLOAT`. Structured `OBJECT(...)`/`ARRAY(...)`/`MAP(...)` columns are introspected via `SHOW COLUMNS` and compared including their nesting.

{/* AUTOGENERATED TYPE MAPPING: do not edit by hand; regenerate with update_reference_types.py */}

### Logical type mapping

When no `physicalType` is declared, the CLI derives the native type from the `logicalType` — for example in `datacontract export sql` and the dbt exports. This table is generated from the converter in the CLI's code:

| `logicalType` | Snowflake type |
|---|---|
| `string` | `STRING` |
| `integer` | `NUMBER` |
| `number` | `NUMBER` |
| `boolean` | `BOOLEAN` |
| `date` | `DATE` |
| `timestamp` | `TIMESTAMP_TZ` |
| `time` | `TIME` |
| `object` | `OBJECT` |
| `array` | `ARRAY` |
| `map` | `MAP(VARCHAR, VARCHAR)` |
| `vector` | `VECTOR(FLOAT, 1536)` |

{/* END AUTOGENERATED TYPE MAPPING */}
