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

## Variables in the data contract

Since ODCS v3.2.0, any string value in a data contract may contain a `${VAR_NAME}` reference, optionally with an inline default: `${VAR_NAME:-default}`. This keeps hostnames, bucket paths, and other environment-specific values out of the contract, so the same file works in every environment.

```yaml
servers:
  - server: production
    type: postgresql
    host: ${DB_HOST}
    port: ${DB_PORT:-5432}
    database: ${DB_NAME:-orders}
schema:
  - name: orders
    quality:
      - type: sql
        query: SELECT COUNT(*) FROM orders WHERE created_at > '${CUTOFF_DATE}'
        mustBe: 0
```

The CLI resolves a reference at the moment it uses the value: when `datacontract test` opens the connection, and when it prepares a SQL quality query for execution. In queries, the CLI's own placeholders such as `${model}` and `${schema}` are substituted first. Values come from the environment, including a loaded `.env` file. A reference to an unset or empty variable without a default fails the run with the variable's name; an empty string is never substituted silently. The contract itself is never changed: `lint` accepts unresolved references, and `export` and `publish` write them back exactly as written.

The [per-source override options](#all-options) such as `DATACONTRACT_POSTGRES_HOST` take precedence over the contract, so an override replaces a reference in the same field without resolving it.

## Config file (YAML)

A YAML config file groups options in sections per data source. String values may contain `${VAR}` and `${VAR:-default}` references, resolved when the file is loaded. Pass it with the global `--config-file` option, or place it at one of the default locations: `./datacontract-config.yaml` or `~/.datacontract/config.yaml`.

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

## All options

Every option, by its environment variable name and the matching `Config` field. The [data source pages](./testing/index.md) explain how each source uses them. `${VAR}`-style config file keys drop the `DATACONTRACT_` prefix and the section name (`snowflake.username` for `DATACONTRACT_SNOWFLAKE_USERNAME`); API headers are the environment variable name in lowercase with dashes (`datacontract-snowflake-username`).

{/* AUTOGENERATED CONFIG OPTIONS: do not edit by hand; regenerate with update_config_options.py */}

### Entropy Data (publishing, remote contracts)

| Environment variable | `Config` field | Type | Notes |
|---|---|---|---|
| `ENTROPY_DATA_API_KEY` | `entropy_data_api_key` | string (secret) |  |
| `ENTROPY_DATA_HOST` | `entropy_data_host` | string |  |
| `DATAMESH_MANAGER_API_KEY` | `datamesh_manager_api_key` | string (secret) | Deprecated, use `ENTROPY_DATA_API_KEY` |
| `DATAMESH_MANAGER_HOST` | `datamesh_manager_host` | string | Deprecated, use `ENTROPY_DATA_HOST` |
| `DATACONTRACT_MANAGER_API_KEY` | `datacontract_manager_api_key` | string (secret) | Deprecated, use `ENTROPY_DATA_API_KEY` |
| `DATACONTRACT_MANAGER_HOST` | `datacontract_manager_host` | string | Deprecated, use `ENTROPY_DATA_HOST` |

### General

| Environment variable | `Config` field | Type | Notes |
|---|---|---|---|
| `DATACONTRACT_API_HEADER_AUTHORIZATION` | `api_header_authorization` | string (secret) |  |
| `DATACONTRACT_MAX_ERRORS` | `max_errors` | integer |  |

### Athena

| Environment variable | `Config` field | Type | Notes |
|---|---|---|---|
| `DATACONTRACT_ATHENA_CATALOG` | `athena_catalog` | string | Overrides `catalog` from the contract's `servers` block |
| `DATACONTRACT_ATHENA_SCHEMA` | `athena_schema` | string | Overrides `schema` from the contract's `servers` block |
| `DATACONTRACT_ATHENA_STAGING_DIR` | `athena_staging_dir` | string | Overrides `stagingDir` from the contract's `servers` block |
| `DATACONTRACT_ATHENA_WORKGROUP` | `athena_workgroup` | string | Overrides `workgroup` from the contract's `servers` block |

### Azure

| Environment variable | `Config` field | Type | Notes |
|---|---|---|---|
| `DATACONTRACT_AZURE_CONNECTION_STRING` | `azure_connection_string` | string (secret) |  |
| `DATACONTRACT_AZURE_STORAGE_ACCOUNT_KEY` | `azure_storage_account_key` | string (secret) |  |
| `DATACONTRACT_AZURE_TENANT_ID` | `azure_tenant_id` | string |  |
| `DATACONTRACT_AZURE_CLIENT_ID` | `azure_client_id` | string |  |
| `DATACONTRACT_AZURE_CLIENT_SECRET` | `azure_client_secret` | string (secret) |  |

### BigQuery

| Environment variable | `Config` field | Type | Notes |
|---|---|---|---|
| `DATACONTRACT_BIGQUERY_ACCOUNT_INFO_JSON_PATH` | `bigquery_account_info_json_path` | string |  |
| `DATACONTRACT_BIGQUERY_BILLING_PROJECT` | `bigquery_billing_project` | string |  |
| `DATACONTRACT_BIGQUERY_IMPERSONATION_ACCOUNT` | `bigquery_impersonation_account` | string |  |
| `DATACONTRACT_BIGQUERY_PROJECT` | `bigquery_project` | string | Overrides `project` from the contract's `servers` block |
| `DATACONTRACT_BIGQUERY_DATASET` | `bigquery_dataset` | string | Overrides `dataset` from the contract's `servers` block |

### Databricks

| Environment variable | `Config` field | Type | Notes |
|---|---|---|---|
| `DATACONTRACT_DATABRICKS_SERVER_HOSTNAME` | `databricks_server_hostname` | string | Overrides `host` from the contract's `servers` block |
| `DATACONTRACT_DATABRICKS_HTTP_PATH` | `databricks_http_path` | string |  |
| `DATACONTRACT_DATABRICKS_TOKEN` | `databricks_token` | string (secret) |  |
| `DATACONTRACT_DATABRICKS_CLIENT_ID` | `databricks_client_id` | string |  |
| `DATACONTRACT_DATABRICKS_CLIENT_SECRET` | `databricks_client_secret` | string (secret) |  |
| `DATACONTRACT_DATABRICKS_PROFILE` | `databricks_profile` | string |  |
| `DATACONTRACT_DATABRICKS_AUTH_TYPE` | `databricks_auth_type` | string |  |
| `DATACONTRACT_DATABRICKS_CATALOG` | `databricks_catalog` | string | Overrides `catalog` from the contract's `servers` block |
| `DATACONTRACT_DATABRICKS_SCHEMA` | `databricks_schema` | string | Overrides `schema` from the contract's `servers` block |

### DuckDB

| Environment variable | `Config` field | Type | Notes |
|---|---|---|---|
| `DATACONTRACT_DUCKDB_DATABASE` | `duckdb_database` | string | Overrides `database` from the contract's `servers` block |
| `DATACONTRACT_DUCKDB_SCHEMA` | `duckdb_schema` | string | Overrides `schema` from the contract's `servers` block |

### GCS

| Environment variable | `Config` field | Type | Notes |
|---|---|---|---|
| `DATACONTRACT_GCS_KEY_ID` | `gcs_key_id` | string |  |
| `DATACONTRACT_GCS_SECRET` | `gcs_secret` | string (secret) |  |

### Impala

| Environment variable | `Config` field | Type | Notes |
|---|---|---|---|
| `DATACONTRACT_IMPALA_USERNAME` | `impala_username` | string |  |
| `DATACONTRACT_IMPALA_PASSWORD` | `impala_password` | string (secret) |  |
| `DATACONTRACT_IMPALA_AUTH_MECHANISM` | `impala_auth_mechanism` | string |  |
| `DATACONTRACT_IMPALA_HTTP_PATH` | `impala_http_path` | string |  |
| `DATACONTRACT_IMPALA_USE_SSL` | `impala_use_ssl` | boolean |  |
| `DATACONTRACT_IMPALA_USE_HTTP_TRANSPORT` | `impala_use_http_transport` | boolean |  |
| `DATACONTRACT_IMPALA_HOST` | `impala_host` | string | Overrides `host` from the contract's `servers` block |
| `DATACONTRACT_IMPALA_PORT` | `impala_port` | integer | Overrides `port` from the contract's `servers` block |
| `DATACONTRACT_IMPALA_DATABASE` | `impala_database` | string | Overrides `database` from the contract's `servers` block |

### Kafka

| Environment variable | `Config` field | Type | Notes |
|---|---|---|---|
| `DATACONTRACT_KAFKA_SASL_USERNAME` | `kafka_sasl_username` | string |  |
| `DATACONTRACT_KAFKA_SASL_PASSWORD` | `kafka_sasl_password` | string (secret) |  |
| `DATACONTRACT_KAFKA_SASL_MECHANISM` | `kafka_sasl_mechanism` | string |  |
| `DATACONTRACT_KAFKA_SCHEMA_REGISTRY_URL` | `kafka_schema_registry_url` | string |  |
| `DATACONTRACT_KAFKA_SCHEMA_REGISTRY_USERNAME` | `kafka_schema_registry_username` | string |  |
| `DATACONTRACT_KAFKA_SCHEMA_REGISTRY_PASSWORD` | `kafka_schema_registry_password` | string (secret) |  |
| `DATACONTRACT_KAFKA_MAX_MESSAGES` | `kafka_max_messages` | integer |  |
| `DATACONTRACT_KAFKA_TIMEOUT` | `kafka_timeout` | integer |  |
| `DATACONTRACT_KAFKA_GROUP_PREFIX` | `kafka_group_prefix` | string |  |

### MySQL

| Environment variable | `Config` field | Type | Notes |
|---|---|---|---|
| `DATACONTRACT_MYSQL_USERNAME` | `mysql_username` | string |  |
| `DATACONTRACT_MYSQL_PASSWORD` | `mysql_password` | string (secret) |  |
| `DATACONTRACT_MYSQL_HOST` | `mysql_host` | string | Overrides `host` from the contract's `servers` block |
| `DATACONTRACT_MYSQL_PORT` | `mysql_port` | integer | Overrides `port` from the contract's `servers` block |
| `DATACONTRACT_MYSQL_DATABASE` | `mysql_database` | string | Overrides `database` from the contract's `servers` block |

### Oracle

| Environment variable | `Config` field | Type | Notes |
|---|---|---|---|
| `DATACONTRACT_ORACLE_USERNAME` | `oracle_username` | string |  |
| `DATACONTRACT_ORACLE_PASSWORD` | `oracle_password` | string (secret) |  |
| `DATACONTRACT_ORACLE_CLIENT_DIR` | `oracle_client_dir` | string |  |
| `DATACONTRACT_ORACLE_HOST` | `oracle_host` | string | Overrides `host` from the contract's `servers` block |
| `DATACONTRACT_ORACLE_PORT` | `oracle_port` | integer | Overrides `port` from the contract's `servers` block |
| `DATACONTRACT_ORACLE_SERVICE_NAME` | `oracle_service_name` | string | Overrides `serviceName` from the contract's `servers` block |

### Postgres

| Environment variable | `Config` field | Type | Notes |
|---|---|---|---|
| `DATACONTRACT_POSTGRES_USERNAME` | `postgres_username` | string |  |
| `DATACONTRACT_POSTGRES_PASSWORD` | `postgres_password` | string (secret) |  |
| `DATACONTRACT_POSTGRES_HOST` | `postgres_host` | string | Overrides `host` from the contract's `servers` block |
| `DATACONTRACT_POSTGRES_PORT` | `postgres_port` | integer | Overrides `port` from the contract's `servers` block |
| `DATACONTRACT_POSTGRES_DATABASE` | `postgres_database` | string | Overrides `database` from the contract's `servers` block |
| `DATACONTRACT_POSTGRES_SCHEMA` | `postgres_schema` | string | Overrides `schema` from the contract's `servers` block |

### Redshift

| Environment variable | `Config` field | Type | Notes |
|---|---|---|---|
| `DATACONTRACT_REDSHIFT_AUTHENTICATION` | `redshift_authentication` | string |  |
| `DATACONTRACT_REDSHIFT_USERNAME` | `redshift_username` | string |  |
| `DATACONTRACT_REDSHIFT_PASSWORD` | `redshift_password` | string (secret) |  |
| `DATACONTRACT_REDSHIFT_SSLMODE` | `redshift_sslmode` | string |  |
| `DATACONTRACT_REDSHIFT_DB_USER` | `redshift_db_user` | string |  |
| `DATACONTRACT_REDSHIFT_DB_GROUPS` | `redshift_db_groups` | string |  |
| `DATACONTRACT_REDSHIFT_AUTO_CREATE` | `redshift_auto_create` | boolean |  |
| `DATACONTRACT_REDSHIFT_WORKGROUP` | `redshift_workgroup` | string |  |
| `DATACONTRACT_REDSHIFT_CLUSTER_IDENTIFIER` | `redshift_cluster_identifier` | string |  |
| `DATACONTRACT_REDSHIFT_REGION` | `redshift_region` | string |  |
| `DATACONTRACT_REDSHIFT_DURATION_SECONDS` | `redshift_duration_seconds` | integer |  |
| `DATACONTRACT_REDSHIFT_HOST` | `redshift_host` | string | Overrides `host` from the contract's `servers` block |
| `DATACONTRACT_REDSHIFT_PORT` | `redshift_port` | integer | Overrides `port` from the contract's `servers` block |
| `DATACONTRACT_REDSHIFT_DATABASE` | `redshift_database` | string | Overrides `database` from the contract's `servers` block |
| `DATACONTRACT_REDSHIFT_SCHEMA` | `redshift_schema` | string | Overrides `schema` from the contract's `servers` block |

### S3 / AWS (also Athena, Redshift IAM, Glue)

| Environment variable | `Config` field | Type | Notes |
|---|---|---|---|
| `DATACONTRACT_S3_ACCESS_KEY_ID` | `s3_access_key_id` | string |  |
| `DATACONTRACT_S3_SECRET_ACCESS_KEY` | `s3_secret_access_key` | string (secret) |  |
| `DATACONTRACT_S3_SESSION_TOKEN` | `s3_session_token` | string (secret) |  |
| `DATACONTRACT_S3_REGION` | `s3_region` | string |  |

### Snowflake

| Environment variable | `Config` field | Type | Notes |
|---|---|---|---|
| `DATACONTRACT_SNOWFLAKE_USERNAME` | `snowflake_username` | string |  |
| `DATACONTRACT_SNOWFLAKE_PASSWORD` | `snowflake_password` | string (secret) |  |
| `DATACONTRACT_SNOWFLAKE_AUTHENTICATOR` | `snowflake_authenticator` | string |  |
| `DATACONTRACT_SNOWFLAKE_ROLE` | `snowflake_role` | string |  |
| `DATACONTRACT_SNOWFLAKE_TOKEN` | `snowflake_token` | string (secret) |  |
| `DATACONTRACT_SNOWFLAKE_PASSCODE` | `snowflake_passcode` | string (secret) |  |
| `DATACONTRACT_SNOWFLAKE_PRIVATE_KEY` | `snowflake_private_key` | string (secret) |  |
| `DATACONTRACT_SNOWFLAKE_PRIVATE_KEY_FILE` | `snowflake_private_key_file` | string |  |
| `DATACONTRACT_SNOWFLAKE_PRIVATE_KEY_FILE_PWD` | `snowflake_private_key_file_pwd` | string (secret) |  |
| `DATACONTRACT_SNOWFLAKE_WAREHOUSE` | `snowflake_warehouse` | string |  |
| `DATACONTRACT_SNOWFLAKE_CREATE_OBJECT_UDFS` | `snowflake_create_object_udfs` | boolean |  |
| `DATACONTRACT_SNOWFLAKE_LOGIN_TIMEOUT` | `snowflake_login_timeout` | integer |  |
| `DATACONTRACT_SNOWFLAKE_NETWORK_TIMEOUT` | `snowflake_network_timeout` | integer |  |
| `DATACONTRACT_SNOWFLAKE_SOCKET_TIMEOUT` | `snowflake_socket_timeout` | integer |  |
| `DATACONTRACT_SNOWFLAKE_HOST` | `snowflake_host` | string |  |
| `DATACONTRACT_SNOWFLAKE_PORT` | `snowflake_port` | integer |  |
| `DATACONTRACT_SNOWFLAKE_HOME` | `snowflake_home` | string |  |
| `DATACONTRACT_SNOWFLAKE_CONNECTIONS_FILE` | `snowflake_connections_file` | string |  |
| `DATACONTRACT_SNOWFLAKE_DEFAULT_CONNECTION_NAME` | `snowflake_default_connection_name` | string |  |
| `DATACONTRACT_SNOWFLAKE_PRIVATE_KEY_PATH` | `snowflake_private_key_path` | string | Deprecated, use `DATACONTRACT_SNOWFLAKE_PRIVATE_KEY_FILE` |
| `DATACONTRACT_SNOWFLAKE_PRIVATE_KEY_PASSPHRASE` | `snowflake_private_key_passphrase` | string (secret) | Deprecated, use `DATACONTRACT_SNOWFLAKE_PRIVATE_KEY_FILE_PWD` |
| `DATACONTRACT_SNOWFLAKE_CONNECTION_TIMEOUT` | `snowflake_connection_timeout` | integer | Deprecated, use `DATACONTRACT_SNOWFLAKE_LOGIN_TIMEOUT` |
| `DATACONTRACT_SNOWFLAKE_ACCOUNT` | `snowflake_account` | string | Overrides `account` from the contract's `servers` block |
| `DATACONTRACT_SNOWFLAKE_DATABASE` | `snowflake_database` | string | Overrides `database` from the contract's `servers` block |
| `DATACONTRACT_SNOWFLAKE_SCHEMA` | `snowflake_schema` | string | Overrides `schema` from the contract's `servers` block |

### SQL Server

| Environment variable | `Config` field | Type | Notes |
|---|---|---|---|
| `DATACONTRACT_SQLSERVER_AUTHENTICATION` | `sqlserver_authentication` | string |  |
| `DATACONTRACT_SQLSERVER_USERNAME` | `sqlserver_username` | string |  |
| `DATACONTRACT_SQLSERVER_PASSWORD` | `sqlserver_password` | string (secret) |  |
| `DATACONTRACT_SQLSERVER_CLIENT_ID` | `sqlserver_client_id` | string |  |
| `DATACONTRACT_SQLSERVER_CLIENT_SECRET` | `sqlserver_client_secret` | string (secret) |  |
| `DATACONTRACT_SQLSERVER_DRIVER` | `sqlserver_driver` | string |  |
| `DATACONTRACT_SQLSERVER_ENCRYPTED_CONNECTION` | `sqlserver_encrypted_connection` | boolean |  |
| `DATACONTRACT_SQLSERVER_TRUST_SERVER_CERTIFICATE` | `sqlserver_trust_server_certificate` | boolean |  |
| `DATACONTRACT_SQLSERVER_TRUSTED_CONNECTION` | `sqlserver_trusted_connection` | boolean |  |
| `DATACONTRACT_SQLSERVER_HOST` | `sqlserver_host` | string | Overrides `host` from the contract's `servers` block |
| `DATACONTRACT_SQLSERVER_PORT` | `sqlserver_port` | integer | Overrides `port` from the contract's `servers` block |
| `DATACONTRACT_SQLSERVER_DATABASE` | `sqlserver_database` | string | Overrides `database` from the contract's `servers` block |

### Trino

| Environment variable | `Config` field | Type | Notes |
|---|---|---|---|
| `DATACONTRACT_TRINO_AUTHENTICATION` | `trino_authentication` | string |  |
| `DATACONTRACT_TRINO_USERNAME` | `trino_username` | string |  |
| `DATACONTRACT_TRINO_PASSWORD` | `trino_password` | string (secret) |  |
| `DATACONTRACT_TRINO_JWT_TOKEN` | `trino_jwt_token` | string (secret) |  |
| `DATACONTRACT_TRINO_HOST` | `trino_host` | string | Overrides `host` from the contract's `servers` block |
| `DATACONTRACT_TRINO_PORT` | `trino_port` | integer | Overrides `port` from the contract's `servers` block |
| `DATACONTRACT_TRINO_CATALOG` | `trino_catalog` | string | Overrides `catalog` from the contract's `servers` block |
| `DATACONTRACT_TRINO_SCHEMA` | `trino_schema` | string | Overrides `schema` from the contract's `servers` block |

{/* END AUTOGENERATED CONFIG OPTIONS */}

Process-level variables are not `Config` options and stay environment-only: `DATACONTRACT_CLI_DEBUG` (debug logging), `DATACONTRACT_CLI_API_KEY` (see [API](./api.md)), and `DATACONTRACT_SYSTEM_TRUSTSTORE` (see the [command reference](./commands/index.md)).

## Precedence

Within one operation, resolution is:

1. **Explicit config** for the options it sets: the `Config` object or dict passed to `DataContract`, the loaded `--config-file`, or the request's `datacontract-*` headers.
2. **Environment variables** for everything the explicit config leaves unset.
3. **`.env`** fills in environment variables that are not already set (it never overrides).

So a committed team config file can hold defaults, CI can override single values via environment variables, and code can override everything.

## Notes for specific sources

- **Snowflake**: only the documented `DATACONTRACT_SNOWFLAKE_*` options are passed to the connector. Unknown names are ignored with a warning; use a [connections.toml](./testing/snowflake.md) for connector parameters the CLI does not support directly.
- **AWS sources (S3, Athena, Redshift IAM, Glue)**: when no `DATACONTRACT_S3_*` options are set, boto3's own credential chain applies (`aws sso login`, `AWS_PROFILE`, instance roles, GitHub OIDC). The same credential set is used to read data contracts from `s3://` locations.
