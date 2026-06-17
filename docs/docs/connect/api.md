---
sidebar_position: 17
title: "HTTP API"
description: "Test JSON HTTP APIs (GET only)."
---

# HTTP API

Test APIs that return data in JSON format. Currently, only GET requests are supported.

## Example

```yaml
servers:
  api:
    type: "api"
    location: "https://api.example.com/path"
    delimiter: none # new_line, array, or none (default)
models:
  my_object: # corresponds to the root element of the JSON response
    type: object
    fields:
      field1:
        type: string
      field2:
        type: number
```

## Environment variables

| Variable | Example | Description |
|---|---|---|
| `DATACONTRACT_API_HEADER_AUTHORIZATION` | `Bearer <token>` | Value for the `authorization` header (optional) |
