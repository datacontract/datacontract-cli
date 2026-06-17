---
sidebar_position: 5
title: "test"
description: "Run schema and quality tests on configured servers."
---

# `datacontract test`

Run schema and quality tests on the servers configured in the contract. See the [Data Contract Testing](../testing.md) guide for connection details and supported data sources.

```bash
datacontract test [LOCATION]
```

| Argument | Default | Description |
|---|---|---|
| `LOCATION` | `datacontract.yaml` | Location (URL or path) of the data contract YAML. |

| Option | Default | Description |
|---|---|---|
| `--server` | `all` | Which server to test (the key in the `servers` block), or `all`. |
| `--schema-name` | `all` | Which schema to test, or `all`. |
| `--checks` | all | Comma-separated categories: `schema`, `quality`, `servicelevel`, `custom`. |
| `--publish` | — | URL to publish the results to after the test. |
| `--output` | — | File path to write results to. |
| `--output-format` | — | `json` or `junit`. |
| `--include-failed-samples` / `--no-...` | off | Collect a small sample of failed rows. |
| `--logs` / `--no-logs` | `--no-logs` | Print logs. |
| `--ssl-verification` / `--no-...` | on | SSL verification when publishing. |
| `--inline-references` / `--no-...` | on | Resolve and inline external references. |
| `--debug` / `--no-debug` | off | Enable debug logging. |

```bash
datacontract test datacontract.yaml --server production
```
