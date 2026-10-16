---
sidebar_position: 13
title: "HTTP API Reference"
sidebar_label: "HTTP API"
description: "All HTTP API authentication options and data type handling."
---

# <img className="page-icon" src="/img/icons/api.svg" alt="" /> HTTP API Reference

Authentication options and data type handling for [HTTP API connections](../testing/api.md).

## Server

```yaml
servers:
  - server: api
    type: api
    location: "https://api.example.com/orders"
    delimiter: array # new_line, array, or none (default)
```

## Authentication

| Variable | Example | Description |
|---|---|---|
| `DATACONTRACT_API_HEADER_AUTHORIZATION` | `Bearer <token>` | Value for the `Authorization` header (optional) |
| `DATACONTRACT_API_HEADER_X_API_KEY` | `<api-key>` | Value for the `X-API-Key` header (optional) |

The `location` (URL) and `delimiter` (`new_line`, `array`, or `none`) come from the contract's `servers` block. The `location` may contain [variables](../configuration.md#variables-in-the-data-contract), such as `https://api.example.com/orders/${orderId:-ORD-1001}`.

## Request

Custom properties of the server shape the request:

| Custom property | Example | Description |
|---|---|---|
| `method` | `POST` | `GET` (default) or `POST`. |
| `params` | `{limit: 100, status: [placed, shipped]}` | The query parameters, each a string, number or boolean, or a list of them for a repeated parameter. |
| `body` | `{query: {status: shipped}}` | The request body. A mapping or list is sent as JSON, a string as the JSON text it holds. Requires `method: POST`. |

A `${VAR}` [variable](../configuration.md#variables-in-the-data-contract) may appear in any string of `params` and `body`; it resolves to a string, so write a number the API requires as a literal, or put the reference into a string `body` without quotes: `'{"size": ${SIZE:-100}}'`.

## Data types

The response may be JSON or YAML, as its `Content-Type` states (`application/yaml`, `application/x-yaml`, or `text/yaml` for YAML). A YAML response is read as the JSON it holds; a stream of several YAML documents is one record per document. The response is then downloaded and tested like a local JSON file, so a property that is not required may be absent from every record: records are read as the contract's types and validated against a JSON Schema derived from the contract's `logicalType`s. The ODCS logical types map to JSON Schema types (`string`, `integer`, `number`, `boolean`, `object`, `array`; `date`/`timestamp`/`time` become `string` with `format: date`/`date-time`/`time`, `map` an `object`, and `vector` an `array` of numbers); non-required fields also accept `null`. `physicalType` is not checked. Value constraints come from `logicalTypeOptions` (`pattern`, `minimum`, `enum`, …).
