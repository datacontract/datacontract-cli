---
sidebar_position: 9
title: "HTTP API"
description: "Test data from a JSON HTTP API endpoint with the Data Contract CLI (GET requests only)."
---

<img className="page-icon" src="/img/icons/api.svg" alt="" />

# HTTP API

:::info Required extra
This connection needs **no additional extra**. See [Installation](../installation.md).
:::

Test APIs that return data in JSON format. Currently, only GET requests are supported.

## Server

```yaml
servers:
  - server: api
    type: api
    location: "https://api.example.com/path"
    delimiter: none # new_line, array, or none (default)
```

## Environment variables

| Variable | Example | Description |
|---|---|---|
| `DATACONTRACT_API_HEADER_AUTHORIZATION` | `Bearer <token>` | Value for the `authorization` header (optional) |

