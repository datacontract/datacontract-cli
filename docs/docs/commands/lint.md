---
sidebar_position: 3
title: "lint"
description: "Validate that the data contract is correctly formatted."
---

# `datacontract lint`

Validate that the `datacontract.yaml` is correctly formatted against the ODCS JSON Schema.

```bash
datacontract lint [LOCATION]
```

| Argument | Default | Description |
|---|---|---|
| `LOCATION` | `datacontract.yaml` | Location (URL or path) of the data contract YAML. |

| Option | Default | Description |
|---|---|---|
| `--json-schema` | — | Location (URL or path) of the ODCS JSON Schema. |
| `--output` | stdout | File path to write the results to. |
| `--output-format` | — | `json` or `junit`. |
| `--all-errors` | — | Report all JSON Schema validation errors instead of stopping after the first. |
| `--inline-references` / `--no-inline-references` | `--inline-references` | Resolve and inline external references. |
| `--debug` / `--no-debug` | `--no-debug` | Enable debug logging. |

```bash
datacontract lint datacontract.yaml
```
