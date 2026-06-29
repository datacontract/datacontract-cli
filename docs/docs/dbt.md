---
sidebar_position: 8
title: "Sync with dbt"
description: "Generate dbt tests from a data contract and run them with datacontract dbt sync."
---

# Sync with dbt

The Data Contract CLI integrates with [dbt](https://www.getdbt.com/) in two directions:

1. **`datacontract dbt sync` + `datacontract dbt test`** — generate dbt tests from a contract, then run them.
2. **Exporters and importers** — convert between contracts and dbt models/sources.

The flow is two steps:

1. **`datacontract dbt sync`** generates the contract-managed tests into your dbt project.
2. **`datacontract dbt test`** runs them.

## `datacontract dbt sync`

`dbt sync` generates dbt tests from an ODCS data contract directly into your dbt project. The contract becomes the single source of truth for column-level constraints and quality checks. By default it only generates — run the tests with `datacontract dbt test` (or pass `--run-tests` to do both in one step).

```bash
# Auto-discover a contract named *.odcs.yaml in a dbt project, generate tests
datacontract dbt sync

# Explicit contract
datacontract dbt sync orders.odcs.yaml --project-dir ./warehouse

# Generate and run the tests in one step, against a specific dbt target
datacontract dbt sync orders.odcs.yaml --run-tests --target dev

# Generate, run, and publish results to an Entropy Data instance (--publish implies --run-tests)
datacontract dbt sync orders.odcs.yaml --publish https://api.entropy-data.com/api/test-results
```

:::note
The `dbt sync` command is still work in progress and will receive further functionality and documentation over time.
:::

### What it does

On each run, the command:

- **Wipes and regenerates** the `models/datacontract_cli/` and `tests/datacontract_cli/` directories under your dbt project. The paths honor `model-paths` and `test-paths` in `dbt_project.yml`.
- **Emits one YAML model file per ODCS schema** that uses dbt's built-in tests and [`dbt_utils`](https://github.com/dbt-labs/dbt-utils).
- **Emits singular SQL tests** for all ODCS `quality` rules that can't be expressed as native YAML tests.

It does not run the tests by default — pass `--run-tests` to also run them, or run `datacontract dbt test` afterwards.

It is recommended to remove existing dbt tests for the contract's columns to avoid duplication.

### Prerequisites

- `dbt-core` plus an adapter (e.g. `dbt-duckdb`, `dbt-postgres`) on `PATH`.
- [`dbt_utils`](https://github.com/dbt-labs/dbt-utils) installed in your dbt project's `packages.yml`.

### Options

| Option | Default | Description |
|---|---|---|
| `--project-dir` | current dir | Path to the dbt project root (must contain `dbt_project.yml`). |
| `--schema-name` | `all` | Which ODCS schema object to sync, by name. |
| `--model-resolution` | `name` | How to map an ODCS schema to a dbt model name: `name` or `physicalName`. |
| `--target` | — | Forwarded to `dbt test --target`. |
| `--profiles-dir` | — | Forwarded to `dbt test --profiles-dir`. |
| `--run-tests` / `--skip-tests` | `--skip-tests` | Run `dbt test` after syncing. Implied by `--publish`/`--server`. |
| `--publish` | — | URL to publish the results to. |
| `--server` | — | ODCS server name for published test results. |

See the [`dbt` command reference](./commands/dbt.md).

## `datacontract dbt test`

`dbt test` runs the contract-managed tests that `dbt sync` generated, reports the results, and optionally publishes them. It never modifies project files — run `dbt sync` first to (re)generate the tests.

```bash
datacontract dbt test orders.odcs.yaml --project-dir ./warehouse --target dev
```

See the [`dbt` command reference](./commands/dbt.md).

## dbt exporters

Convert a contract into dbt artifacts:

- **[`dbt-models`](./exports/dbt-models.md)** — dbt model schema YAML. If a server is selected via `--server`, the dbt `data_types` match the expected data types of that server; otherwise it defaults to `snowflake`.
- **[`dbt-sources`](./exports/dbt-sources.md)** — dbt sources YAML.
- **[`dbt-staging-sql`](./exports/dbt-staging-sql.md)** — a dbt staging SQL file.

```bash
datacontract export dbt-models datacontract.yaml --server snowflake
```

## dbt importer

Generate a contract from a dbt project's `manifest.json`:

```bash
# Import specific tables from a dbt manifest
datacontract import dbt --source manifest.json --dbt-model orders --dbt-model line_items

# Import all tables
datacontract import dbt --source manifest.json
```

See the [dbt importer](./imports/dbt.md).
