---
sidebar_position: 11
title: "HTTP API"
description: "Create a data contract from a JSON HTTP API and test the responses against it (GET requests only)."
---

# <img className="page-icon" src="/img/icons/api.svg" alt="" /> HTTP API

Test APIs that return data in JSON format. Currently, only GET requests are supported.

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

## 3. Create a contract from a response

Fetch one response and import its schema, then point the generated `servers` block at the endpoint:

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
    delimiter: none # new_line, array, or none (default)
```

## 4. Test the actual data

```bash
datacontract test datacontract.yaml
```

```
Testing datacontract.yaml
Server: production (type=api, format=json, location=https://api.example.com/orders)
╭────────┬─────────────────────────────────────────────────┬─────────────────┬─────────╮
│ Result │ Check                                           │ Field           │ Details │
├────────┼─────────────────────────────────────────────────┼─────────────────┼─────────┤
│ passed │ Check that field 'order_id' is present          │ orders.order_id │         │
│ passed │ Check that field order_id has no missing values │ orders.order_id │         │
│  ...   │                                                 │                 │         │
╰────────┴─────────────────────────────────────────────────┴─────────────────┴─────────╯
🟢 data contract is valid. Run 24 checks. Took 1.2 seconds.
```

## 5. Let it catch a violation

The contract becomes valuable when it detects drift. Tighten an expectation — for example, mark a field as `required: true`, restrict a status field to its allowed values, or add a quality rule. Run `datacontract test datacontract.yaml` again: every violation is listed as an error, and the command exits with code `1` — ready for [CI/CD and scheduled runs](../scheduling/index.md) so you catch drift before your consumers do.

## Reference

Authentication options and data type handling: **[HTTP API Reference](../reference/api.md)**.

## Troubleshooting

- **`401` / `403`** — set `DATACONTRACT_API_HEADER_AUTHORIZATION` including the scheme (e.g. `Bearer eyJ...`), not just the raw token.
- **Schema checks fail on a wrapped response** — if the API returns `{"data": [...]}` instead of a plain array, model the wrapper object in the schema, or set `delimiter` accordingly (`array` for a JSON array of records, `none` for a single object).
