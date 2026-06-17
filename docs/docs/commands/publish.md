---
sidebar_position: 11
title: "publish"
description: "Publish a data contract to Entropy Data."
---

# `datacontract publish`

Publish the data contract to [Entropy Data](https://www.entropy-data.com/).

```bash
datacontract publish [LOCATION]
```

| Argument | Default | Description |
|---|---|---|
| `LOCATION` | `datacontract.yaml` | Location (URL or path) of the data contract YAML. |

| Option | Default | Description |
|---|---|---|
| `--json-schema` | — | Location (URL or path) of the ODCS JSON Schema. |
| `--ssl-verification` / `--no-...` | on | SSL verification when publishing. |
| `--debug` / `--no-debug` | off | Enable debug logging. |

```bash
datacontract publish datacontract.yaml
```
