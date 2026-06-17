---
sidebar_position: 4
title: "changelog"
description: "Show a changelog between two data contracts."
---

# `datacontract changelog`

Show a changelog between two data contracts.

```bash
datacontract changelog V1 V2
```

| Argument | Description |
|---|---|
| `V1` *(required)* | Location (URL or path) of the source (before) contract. |
| `V2` *(required)* | Location (URL or path) of the target (after) contract. |

| Option | Default | Description |
|---|---|---|
| `--inline-references` / `--no-inline-references` | `--inline-references` | Resolve and inline external references. |
| `--debug` / `--no-debug` | `--no-debug` | Enable debug logging. |

```bash
datacontract changelog v1.odcs.yaml v2.odcs.yaml
```
