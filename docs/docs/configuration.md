---
sidebar_position: 17
title: "Configuration"
description: "All the ways to provide credentials and connection options: environment variables, .env, a YAML config file, the Config class, and per-request API headers."
---

# Configuration

Connecting to a data source needs two kinds of input: **connection details** (host, database, catalog, …), which live in the contract's `servers` block, and **credentials and connection options** (usernames, passwords, tokens, timeouts, …), which are configuration. Every configuration option has a canonical name, its environment variable, such as `DATACONTRACT_SNOWFLAKE_USERNAME`. The [data source pages](./testing/index.md) list the options each source supports.

There are five ways to provide configuration. All of them address options by the same names, and all of them end up in the same place: a `Config` object that is passed through to the connection.

## Environment variables

The default, and the right choice for CI/CD:

```bash
export DATACONTRACT_SNOWFLAKE_USERNAME=svc_test
export DATACONTRACT_SNOWFLAKE_PASSWORD=...
datacontract test datacontract.yaml
```

Environment variables work in every context: CLI, Python library, and API server.

## .env file

The CLI loads a `.env` file from the current working directory, or the nearest parent directory containing one. Values from `.env` fill in missing environment variables; variables that are already set take precedence.

```bash
# .env
DATACONTRACT_POSTGRES_USERNAME=postgres
DATACONTRACT_POSTGRES_PASSWORD=postgres
```

The `.env` values are exported into the process environment, so they also reach tools that read the environment directly, such as boto3 (`AWS_PROFILE`), the Databricks SDK, and Snowflake's `SNOWFLAKE_HOME`.

## Config file (YAML)

A YAML config file groups options in sections per data source. Pass it with the global `--config-file` option, or place it at one of the default locations: `./datacontract-config.yaml` or `~/.datacontract/config.yaml`.

```yaml
# datacontract-config.yaml
snowflake:
  username: svc_test
  password: ${SNOWFLAKE_PASSWORD}
  role: TESTER
  login_timeout: 30
max_errors: 10
```

```bash
datacontract --config-file datacontract-config.yaml test datacontract.yaml
```

Section and key join to form the option name (`snowflake.username` is `DATACONTRACT_SNOWFLAKE_USERNAME`). `${VAR}` references resolve from the environment when the file is loaded, so the file can be committed without holding secrets; add it to `.gitignore` if it contains literal credentials. Unknown option names fail with an error naming the key, so typos surface immediately.

In the Python library, load the same file with `Config.from_yaml("datacontract-config.yaml")`.

## Python library

Pass configuration programmatically via the `config` argument, without touching the process environment:

```python
from datacontract import Config
from datacontract.data_contract import DataContract

run = DataContract(
    data_contract_file="datacontract.yaml",
    server="production",
    config=Config(
        snowflake_username="svc_test",
        snowflake_password=get_secret("snowflake"),
        snowflake_role="TESTER",
    ),
).test()
```

The `Config` class declares every option as a typed field. Field names match the environment variable names (`snowflake_username` for `DATACONTRACT_SNOWFLAKE_USERNAME`), unknown keyword arguments raise immediately, and secrets are held as `SecretStr` so they stay out of logs and reprs. A plain dict keyed by the environment variable names is accepted as well. `DataContract.import_from_source()` takes the same argument. See [Python Library](./python-library.md#credentials) for details.

Because the config object is passed explicitly through the connection layer, concurrent operations with different credentials in one process do not interfere.

## API server

The [API server](./api.md) reads its configuration from environment variables set before startup. In addition, `POST /test` accepts per-request credentials via `datacontract-*` headers, matched case-insensitively and mapped to the option names:

```bash
curl -X POST https://datacontract.example.com/test \
  -H "Content-Type: application/yaml" \
  -H "datacontract-snowflake-username: svc_test" \
  -H "datacontract-snowflake-password: $SNOWFLAKE_PASSWORD" \
  --data-binary @datacontract.yaml
```

Header values apply to that request only, so one server can test contracts for different tenants without sharing credentials through the process environment. Unknown option names are rejected with a 400.

## Precedence

Within one operation, resolution is:

1. **Explicit config** for the options it sets: the `Config` object or dict passed to `DataContract`, the loaded `--config-file`, or the request's `datacontract-*` headers.
2. **Environment variables** for everything the explicit config leaves unset.
3. **`.env`** fills in environment variables that are not already set (it never overrides).

So a committed team config file can hold defaults, CI can override single values via environment variables, and code can override everything.

## Notes for specific sources

- **Snowflake**: only the documented `DATACONTRACT_SNOWFLAKE_*` options are passed to the connector. Unknown names are ignored with a warning; use a [connections.toml](./testing/snowflake.md) for connector parameters the CLI does not support directly.
- **AWS sources (S3, Athena, Redshift IAM, Glue)**: when no `DATACONTRACT_S3_*` options are set, boto3's own credential chain applies (`aws sso login`, `AWS_PROFILE`, instance roles, GitHub OIDC).
