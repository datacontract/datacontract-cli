---
sidebar_position: 10
title: "catalog"
description: "Create an HTML catalog of data contracts."
---

# `datacontract catalog`

Create an HTML catalog of data contracts.

```bash
datacontract catalog [OPTIONS]
```

| Option | Default | Description |
|---|---|---|
| `--files` | `*.yaml` | Glob pattern for the contract files to include (applies recursively to subfolders). |
| `--output` | `catalog/` | Output directory for the catalog HTML files. |
| `--json-schema` | — | Location (URL or path) of the ODCS JSON Schema. |
| `--debug` / `--no-debug` | off | Enable debug logging. |

```bash
# Create a catalog in the current folder
datacontract catalog --output "."

# Create a catalog based on a filename convention
datacontract catalog --files "*.odcs.yaml"
```
