---
sidebar_position: 18
title: "API"
description: "Run the Data Contract CLI as a web server exposing a REST API for testing, linting, and exporting."
---

# API

The Data Contract CLI can run as a web server that exposes a REST API for data contract testing, linting, exporting, and changelogs. This is useful for integrating data contract checks into other services.

You can try a public demo at [api.datacontract.com](https://api.datacontract.com). Note that the demo endpoint cannot connect to your secured data sources.

## Starting the API

The API requires the `api` extra:

```bash
pip install 'datacontract-cli[api]'
```

Start the server:

```bash
datacontract api
```

| Option | Default | Description |
|---|---|---|
| `--port` | `4242` | Bind the socket to this port. |
| `--host` | `127.0.0.1` | Bind to this host. In Docker, use `0.0.0.0`. |
| `--debug` / `--no-debug` | `--no-debug` | Enable debug logging. |

You can pass extra keyword arguments through to `uvicorn.run()`, e.g.:

```bash
datacontract api --port 1234 --root_path /datacontract
```

## OpenAPI / Swagger UI

Once running, open the interactive OpenAPI documentation (Swagger UI) at
[http://localhost:4242](http://localhost:4242). You can execute the commands directly from the UI.

The OpenAPI 3.1 document itself is served at `http://localhost:4242/openapi.json` and can be fed to
a client generator:

```bash
curl -s http://localhost:4242/openapi.json > openapi.json
```

## Test a data contract

POST a data contract as the request body to `/test` and receive the test results as JSON:

```bash
curl -X POST "http://localhost:4242/test?server=production" \
  --data-binary @datacontract.yaml
```

You can also send the YAML inline with `-H 'Content-Type: application/yaml'`.

## Export a data contract

```bash
curl -X POST "http://localhost:4242/export?format=sql" \
  --data-binary @datacontract.yaml
```

## Comparing two contracts

Both comparison endpoints take the same JSON body: `v1` (before) and `v2` (after) as YAML strings.

`POST /changelog` lists what changed. The response is a JSON object with `summary` (one entry per changed field) and `entries` (one per atomic change):

```bash
curl -X POST "http://localhost:4242/changelog" \
  -H "Content-Type: application/json" \
  -d '{
    "v1": "'"$(cat v1.odcs.yaml)"'",
    "v2": "'"$(cat v2.odcs.yaml)"'"
  }'
```

`POST /breaking` grades those same changes for compatibility impact. It adds a `level` (`info`, `warning` or `error`) and a `rule_id` to every entry, plus a top-level `is_breaking` flag that is `true` when any entry is an `error`:

```bash
curl -X POST "http://localhost:4242/breaking" \
  -H "Content-Type: application/json" \
  -d '{
    "v1": "'"$(cat v1.odcs.yaml)"'",
    "v2": "'"$(cat v2.odcs.yaml)"'"
  }'
```

```json
{
  "summary": [...],
  "entries": [
    {
      "path": "schema.orders.properties.order_id.logicalTypeOptions.pattern",
      "change_type": "updated",
      "level": "warning",
      "message": "Changed validation constraint at schema.orders.properties.order_id.logicalTypeOptions.pattern from '^ORD-[0-9]+$' to '^ORD-[0-9]{4}$'",
      "rule_id": "validation-constraint-changed",
      "old_value": "^ORD-[0-9]+$",
      "new_value": "^ORD-[0-9]{4}$"
    }
  ],
  "is_breaking": false
}
```

See [Compare contract versions](./compare-contract-versions.md) for the severity levels and the rules behind them.

## Configure server credentials

To connect to a data source, set the required credentials as environment variables **before starting the API** (see [Configuration](./configuration.md)). For example, for Snowflake:

```bash
export DATACONTRACT_SNOWFLAKE_USERNAME=123
export DATACONTRACT_SNOWFLAKE_PASSWORD=
export DATACONTRACT_SNOWFLAKE_WAREHOUSE=
export DATACONTRACT_SNOWFLAKE_ROLE=
```

Alternatively, `POST /test` accepts credentials per request via `datacontract-*` headers (e.g. `datacontract-snowflake-password`), matched case-insensitively and applied to that request only. This allows one server to test contracts for different tenants without sharing credentials through the process environment. Serve the API over HTTPS when sending credential headers.

## Secure the API

Set `DATACONTRACT_CLI_API_KEY` to a secret value (such as a random UUID) to require authentication. Every endpoint then requires the header `x-api-key` with the correct key, and answers `401` when it is missing and `403` when it is wrong.

```bash
export DATACONTRACT_CLI_API_KEY=<your-secret-key-such-as-a-random-uuid>
```

:::warning
Securing the API is highly recommended. Data contract tests may otherwise be subject to SQL injection or leak sensitive information.
:::

## Posted contracts are untrusted

A data contract carries SQL and names the hosts to connect to, so a contract that arrives over HTTP is treated as untrusted input, whether or not the API key is set:

- a `quality.type: sql` rule must be a **read-only query** — DDL, DML, `COPY`, `ATTACH` and the like are reported as a failed check instead of being executed;
- a credential held in the server's environment is **never sent to a host the contract names** (see [Configuration](./configuration.md));
- a `publish_url` may only point at the **Entropy Data platform or the host set via `ENTROPY_DATA_HOST`** on the server — per-request `entropy-data-host` headers do not widen this, and other hosts are refused;
- `servers[].type: local` is **refused**, so a caller cannot read the files of the machine running the API;
- for a file-based server type (`s3`, `gcs`, `azure`), the DuckDB connection is **confined to the data locations the contract declares**.

If the deployment serves its own files on purpose — the data mounted next to the API in the same container, say — allow it explicitly:

```bash
export DATACONTRACT_CLI_API_ALLOW_LOCAL_FILES=true
```

The contract is then still confined to the paths it declares, but a caller chooses those paths, so only turn this on where callers are trusted.

## Run as a Docker container

The pre-built image can run the API in any container environment (Docker Compose, Kubernetes, Azure Container Apps, Google Cloud Run, …):

```yaml
services:
  datacontract-api:
    image: datacontract/cli:latest
    ports:
      - "4242:4242"
    environment:
      - DATACONTRACT_CLI_API_KEY=a079ce4c-af90-45ab-abe5-a8d7697f60d6
    command: ["api", "--host", "0.0.0.0"]
```

See the [`api` command reference](./commands/api.md).
