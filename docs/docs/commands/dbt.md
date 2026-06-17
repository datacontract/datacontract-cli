---
sidebar_position: 6
title: "dbt sync"
description: "Generate dbt tests from a contract and run them."
---

# `datacontract dbt sync`

Generate dbt tests from an ODCS contract and run them. Within the dbt project, this wipes and regenerates `<model-paths>/datacontract_cli/` and `<test-paths>/datacontract_cli/`, then runs `dbt test`. See the [dbt Integration](../dbt.md) guide.

```bash
datacontract dbt sync [CONTRACT]
```

| Argument | Description |
|---|---|
| `CONTRACT` | Path to the ODCS contract. If omitted, searches for a single `*.odcs.yaml` in the current directory and subdirectories. |

| Option | Default | Description |
|---|---|---|
| `--project-dir` | current dir | Path to the dbt project root (must contain `dbt_project.yml`). |
| `--schema-name` | `all` | Which ODCS schema to sync, by name. |
| `--model-resolution` | `name` | Map an ODCS schema to a dbt model name: `name` or `physicalName`. |
| `--target` | — | Forwarded to `dbt test --target`. |
| `--profiles-dir` | — | Forwarded to `dbt test --profiles-dir`. |
| `--skip-tests` / `--run-tests` | `--run-tests` | Generate tests but skip running `dbt test`. |
| `--publish` | — | URL to publish the results to. |
| `--server` | — | ODCS server name for published test results. |
| `--ssl-verification` / `--no-...` | on | SSL verification when publishing. |
| `--debug` / `--no-debug` | off | Enable debug logging. |

```bash
datacontract dbt sync orders.odcs.yaml --project-dir ./warehouse
```
