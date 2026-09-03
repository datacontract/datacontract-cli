---
sidebar_position: 10
title: "HTTP API Reference"
sidebar_label: "HTTP API"
description: "All HTTP API authentication options and data type handling."
---

# <img className="page-icon" src="/img/icons/api.svg" alt="" /> HTTP API Reference

Authentication options and data type handling for [HTTP API connections](../testing/api.md).

## Server

```yaml
servers:
  - server: production
    type: api
    location: "https://api.example.com/orders"
    format: json
```

## Authentication

| Variable | Example | Description |
|---|---|---|
| `DATACONTRACT_API_HEADER_AUTHORIZATION` | `Bearer <token>` | Value for the `authorization` header (optional) |

The `location` (URL) and `delimiter` (`new_line`, `array`, or `none`) come from the contract's `servers` block. Only GET requests are supported.

## Data types

The response is downloaded and tested like a local JSON file: records are read as the contract's types and validated against a JSON Schema derived from the contract's `logicalType`s. The nine ODCS logical types map to JSON Schema types (`string`, `integer`, `number`, `boolean`, `object`, `array`; `date`/`timestamp`/`time` become `string` with `format: date`/`date-time`/`time`); non-required fields also accept `null`. `physicalType` is not checked. Value constraints come from `logicalTypeOptions` (`pattern`, `minimum`, `enum`, …).
