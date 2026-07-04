---
sidebar_position: 6
title: "dbt"
description: "Generate dbt tests from a contract and run them."
---

# `datacontract dbt`

Work with data contracts in your dbt project. Two subcommands:

- `datacontract dbt sync` — merge an ODCS contract's schema (columns, descriptions, tags) and tests into your dbt project.
- `datacontract dbt test` — run the generated, contract-managed tests.

See the [dbt Integration](../dbt.md) guide.

## `datacontract dbt sync`

Merge one or more ODCS contracts' schema (column data types, descriptions, tags, model metadata) and tests into your dbt project. Modifies the existing dbt model YAML in place (preserving comments and formatting) and, if needed, creates a new model YAML sidecar (next to a model's `.sql`) or singular SQL tests (under `<test-paths>/datacontract_cli/`). Generate-only by default — pass `--run-tests` to also run the contract-managed tests (required alongside `--publish`/`--server`).

```bash
datacontract dbt sync [CONTRACT]...
```

| Argument | Description |
|---|---|
| `CONTRACT` | One or more paths or globs of ODCS contracts to sync. If omitted, every `*.odcs.yaml` under `--project-dir` (and its subdirectories) is synced. Each contract is synced independently; if two *different* contracts resolve to the same dbt model the command aborts before writing anything. Versions of the *same* contract (distinct versions, each with a `v<N>` filename) may share a [versioned dbt model](../dbt.md#versioned-models). |

| Option | Default | Description |
|---|---|---|
| `--project-dir` | current dir | Path to the dbt project root (must contain `dbt_project.yml`). |
| `--schema-name` | `all` | Which ODCS schema to sync, by name. |
| `--model-resolution` | `name` | Map an ODCS schema to a dbt model name: `name` or `physicalName`. |
| `--prune` / `--no-prune` | off | Remove model columns and tags that are not declared in the contract. |
| `--target` | — | Forwarded to `dbt test --target`. |
| `--profiles-dir` | — | Forwarded to `dbt test --profiles-dir`. |
| `--run-tests` / `--skip-tests` | `--skip-tests` | Run `dbt test` after syncing. Required by `--publish`/`--server`. |
| `--publish` | — | URL to publish the results to. |
| `--server` | — | ODCS server whose `type` is the dialect for mapping the contract's types to column `data_type`s, and the server name for published results. |
| `--ssl-verification` / `--no-...` | on | SSL verification when publishing. |
| `--debug` / `--no-debug` | off | Enable debug logging. |

```bash
datacontract dbt sync orders.odcs.yaml --project-dir ./warehouse
```

## `datacontract dbt test`

Run the contract-managed dbt tests that `datacontract dbt sync` generated, scoped to the requested contracts' models, report the results, and optionally publish them. Never modifies project files — run `datacontract dbt sync` first to (re)generate the tests. With multiple contracts, each contract's results are reported (and published) separately, followed by a summary.

```bash
datacontract dbt test [CONTRACT]...
```

| Argument | Description |
|---|---|
| `CONTRACT` | One or more paths or globs of ODCS contracts to test. If omitted, every `*.odcs.yaml` under `--project-dir` (and its subdirectories) is tested. |

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
