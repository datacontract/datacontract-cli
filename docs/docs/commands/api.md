---
sidebar_position: 12
title: "api"
description: "Start the CLI as a web server with a REST API."
---

# `datacontract api`

Start the CLI as a web server application with a REST API. The OpenAPI documentation (Swagger UI) is available at `http://localhost:4242`. Requires the `api` extra. See the [API](../api.md) guide.

```bash
datacontract api [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `--port` | `4242` | Bind the socket to this port. |
| `--host` | `127.0.0.1` | Bind to this host (use `0.0.0.0` for Docker). |
| `--debug` / `--no-debug` | off | Enable debug logging. |

Protect the API by setting `DATACONTRACT_CLI_API_KEY`; requests must then include an `x-api-key` header.

```bash
datacontract api --port 4242 --host 0.0.0.0
```
