---
sidebar_position: 1
title: "init"
description: "Create a new data contract file from a built-in template or an existing contract to start from."
---

# `datacontract init`

Create an empty data contract from a template.

```bash
datacontract init [LOCATION]
```

| Argument | Default | Description |
|---|---|---|
| `LOCATION` | `datacontract.yaml` | Path of the data contract file to create. |

| Option | Default | Description |
|---|---|---|
| `--template` | — | URL of a template or data contract to start from. |
| `--overwrite` / `--no-overwrite` | `--no-overwrite` | Replace an existing file. |
| `--debug` / `--no-debug` | `--no-debug` | Enable debug logging. |

```bash
datacontract init datacontract.yaml
```
