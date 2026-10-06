---
sidebar_position: 15
title: "HTTP API"
description: "Test the JSON or YAML responses of a REST API's GET endpoint against a data contract, created from its OpenAPI document or a sample response."
---

# <img className="page-icon" src="/img/icons/api.svg" alt="" /> HTTP API

Test the response of a REST API's GET endpoint. `datacontract test` calls the endpoint and checks the response, JSON or YAML, against the contract. Only GET requests are supported.

## 1. Install

The response is tested with duckdb, so the `duckdb` extra is required:

```bash
uv tool install --python python3.11 --upgrade 'datacontract-cli[duckdb]'
```

See [Installation](../installation.md) for pip, pipx, and Docker.

## 2. Authenticate

If the API requires authentication, set the value for the `authorization` header:

```bash
# .env
DATACONTRACT_API_HEADER_AUTHORIZATION="Bearer <token>"
```

For public endpoints, skip this step.

## 3. Create a contract

### From the OpenAPI document

If the API has an OpenAPI 3.x document, import the GET operation you want to test, by its `operationId` or its path:

```bash
datacontract import openapi --source openapi.yaml --operation listOrders --output datacontract.yaml
```

The contract gets one schema for the operation's response, and an `api` server for each server in the document, located at the endpoint:

```yaml
servers:
  - server: production
    type: api
    description: Production
    location: https://api.example.com/v1/orders?limit=${limit:-100}
  - server: staging
    type: api
    description: Staging
    location: https://staging.api.example.com/v1/orders?limit=${limit:-100}
schema:
  - name: listOrders
    # ...
```

Path parameters and required query parameters become [variables](../configuration.md#variables-in-the-data-contract) in the `location`, defaulting to the parameter's `example` or `default`. Set them in the environment to call the endpoint with other values, for example `limit=10 datacontract test datacontract.yaml`. See [Import: OpenAPI](../imports/openapi.md) for what is imported.

### From a response

Without an OpenAPI document, fetch one response and import its schema:

```bash
curl -o response.json https://api.example.com/orders
datacontract import json --source response.json --output datacontract.yaml
```

The import generates a `servers` entry of `type: local`. Replace it with the API endpoint:

```yaml
servers:
  - server: api
    type: api
    location: "https://api.example.com/orders"
```

## 4. Test the actual data

```bash
datacontract test datacontract.yaml
```

The first server is tested unless you select one with `--server`, e.g. `--server staging`.

```
Testing datacontract.yaml
Server: production (type=api, location=https://api.example.com/v1/orders?limit=${limit:-100})
╭────────┬───────────────────────────────────────────┬──────────┬─────────────────────────────╮
│ Result │ Check                                     │ Field    │ Details                     │
├────────┼───────────────────────────────────────────┼──────────┼─────────────────────────────┤
│ passed │ Check that JSON has valid schema          │          │ All JSON entries are valid. │
│ passed │ Check that field 'order_id' is present    │ order_id │                             │
│  ...   │                                           │          │                             │
╰────────┴───────────────────────────────────────────┴──────────┴─────────────────────────────╯
🟢 Data contract is valid. Ran 10 checks. Took 1.2 seconds.
```

The request asks for JSON or YAML (`Accept: application/json, application/yaml`). How the response is read depends on its `Content-Type`:

- **JSON**: a single object, an array of records, or one record per line (JSON Lines) is detected automatically.
- **YAML** (`application/yaml`, `application/x-yaml`, `text/yaml`): the YAML is read as the JSON it holds and then tested the same way. A stream of several YAML documents (separated by `---`) counts as one record per document.

## 5. Let it catch a violation

The contract becomes valuable when it detects drift. Tighten an expectation — for example, mark a field as `required: true`, restrict a status field to its allowed values, or add a quality rule. Run `datacontract test datacontract.yaml` again: every violation is listed as an error, and the command exits with code `1` — ready for [CI/CD and scheduled runs](../scheduling/index.md) so you catch drift before your consumers do.

## Reference

Authentication options and data type handling: **[HTTP API Reference](../reference/api.md)**.

## Troubleshooting

- **`401` / `403`**: set `DATACONTRACT_API_HEADER_AUTHORIZATION` including the scheme (e.g. `Bearer eyJ...`), not just the raw token.
- **`Variable orderId referenced in ... is not set`**: the endpoint has a path or query parameter without an example or default. Set it in the environment or a `.env` file, or write a default into the `location` (`${orderId:-ORD-1001}`).
- **Schema checks fail on a wrapped response**: if the API returns `{"data": [...]}` instead of a plain array, model the wrapper object in the schema, or set `delimiter` accordingly (`array` for a JSON array of records, `none` for a single object).
