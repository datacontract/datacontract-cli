---
sidebar_position: 6
title: "dbt"
description: "Generate dbt tests from a contract and run them."
---

# `datacontract dbt`

Work with data contracts in your dbt project. Two subcommands:

- `datacontract dbt sync` — generate dbt tests and model metadata from an ODCS contract.
- `datacontract dbt test` — run the generated, contract-managed tests.

See the [dbt Integration](../dbt.md) guide.

## `datacontract dbt sync`

Generate dbt tests and model metadata from an ODCS contract. Modifies the existing dbt model YAML in place (preserving comments and formatting), and creates new model YAML files or singular SQL tests under `<test-paths>/datacontract_cli/` if needed. Generate-only by default — pass `--run-tests` (or `--publish`/`--server`, which imply it) to also run `dbt test --select config.meta.datacontract_cli.include_in_tests:true`.

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
| `--prune` / `--no-prune` | off | Remove model columns and tags that are not declared in the contract. |
| `--target` | — | Forwarded to `dbt test --target`. |
| `--profiles-dir` | — | Forwarded to `dbt test --profiles-dir`. |
| `--run-tests` / `--skip-tests` | `--skip-tests` | Run `dbt test` after syncing. Implied by `--publish`/`--server`. |
| `--publish` | — | URL to publish the results to. |
| `--server` | — | ODCS server name for published test results. |
| `--ssl-verification` / `--no-...` | on | SSL verification when publishing. |
| `--debug` / `--no-debug` | off | Enable debug logging. |

```bash
datacontract dbt sync orders.odcs.yaml --project-dir ./warehouse
```

## `datacontract dbt test`

Run the contract-managed dbt tests that `datacontract dbt sync` generated. Runs `dbt test --select config.meta.datacontract_cli.include_in_tests:true`, reports the results, and optionally publishes them. Never modifies project files — run `datacontract dbt sync` first to (re)generate the tests.

```bash
datacontract dbt test [CONTRACT]
```

| Argument | Description |
|---|---|
| `CONTRACT` | Path to the ODCS contract. If omitted, searches for a single `*.odcs.yaml` in the current directory and subdirectories. |

| Option | Default | Description |
|---|---|---|
| `--project-dir` | current dir | Path to the dbt project root (must contain `dbt_project.yml`). |
| `--target` | — | Forwarded to `dbt test --target`. |
| `--profiles-dir` | — | Forwarded to `dbt test --profiles-dir`. |
| `--publish` | — | URL to publish the results to. |
| `--server` | — | ODCS server name for published test results. |
| `--ssl-verification` / `--no-...` | on | SSL verification when publishing. |
| `--debug` / `--no-debug` | off | Enable debug logging. |

```bash
datacontract dbt test orders.odcs.yaml --project-dir ./warehouse
```
