---
sidebar_position: 10
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

## Changelog between two contracts

POST a JSON body with `v1` (before) and `v2` (after) as YAML strings. The response is a JSON object with `summary` and `entries`:

```bash
curl -X POST "http://localhost:4242/changelog" \
  -H "Content-Type: application/json" \
  -d '{
    "v1": "'"$(cat v1.odcs.yaml)"'",
    "v2": "'"$(cat v2.odcs.yaml)"'"
  }'
```

## Configure server credentials

To connect to a data source, set the required credentials as environment variables **before starting the API** (see [Testing](./testing.md)). For example, for Snowflake:

```bash
export DATACONTRACT_SNOWFLAKE_USERNAME=123
export DATACONTRACT_SNOWFLAKE_PASSWORD=
export DATACONTRACT_SNOWFLAKE_WAREHOUSE=
export DATACONTRACT_SNOWFLAKE_ROLE=
```

## Secure the API

Set `DATACONTRACT_CLI_API_KEY` to a secret value (such as a random UUID) to require authentication. Requests must then include the header `x-api-key` with the correct key.

```bash
export DATACONTRACT_CLI_API_KEY=<your-secret-key-such-as-a-random-uuid>
```

:::warning
Securing the API is highly recommended. Data contract tests may otherwise be subject to SQL injection or leak sensitive information.
:::

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
