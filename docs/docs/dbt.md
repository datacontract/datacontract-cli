---
sidebar_position: 8
title: "Sync with dbt"
description: "Sync a data contract's schema and tests into your dbt project with datacontract dbt sync, then run them with datacontract dbt test."
---

# Sync with dbt

The Data Contract CLI integrates with [dbt](https://www.getdbt.com/) in multiple ways:

- **Import** : Create a data contract from a dbt manifest file (`datacontract import dbt`)
- **Sync**: Merge the schema and tests of one or multiple data contracts into an existing dbt project (`datacontract dbt sync`)
- **Test**: Run the CLI-generated dbt tests, optionally scoped to a contract (`datacontract dbt test`)
- **Export**: Do a one-time export from a data contract into a dbt model schema, a sources YAML, or a staging SQL file (`datacontract export`)


## `datacontract dbt sync`

`dbt sync` merges an ODCS data contract's schema — column data types, descriptions, tags, and model metadata — and its tests directly into your dbt project. The contract becomes the single source of truth for column-level metadata, constraints, and quality checks. By default it only writes the YAML and SQL — run the generated tests with `datacontract dbt test` (or pass `--run-tests` to do both in one step).

You can sync more than one contract at once: pass several paths, a glob, or no argument to sync every `*.odcs.yaml` in the project. Each contract is synced independently. If two *different* contracts resolve to the same dbt model the command aborts before writing anything — select a single contract so each model has one owner. Two contracts that are **versions of the same contract** may share a model when it is a [versioned dbt model](#versioned-models).

```bash
# Auto-discover and sync every *.odcs.yaml in a dbt project, generate tests
datacontract dbt sync

# Explicit contract
datacontract dbt sync orders.odcs.yaml --project-dir ./warehouse

# Several contracts, or a glob
datacontract dbt sync orders.odcs.yaml customers.odcs.yaml
datacontract dbt sync "contracts/*.odcs.yaml"

# Generate and run the tests in one step, against a specific dbt target
datacontract dbt sync orders.odcs.yaml --run-tests --target dev

# Generate, run, and publish results to an Entropy Data instance (--publish requires --run-tests)
datacontract dbt sync orders.odcs.yaml --run-tests --publish https://api.entropy-data.com/api/test-results
```

:::note
The `dbt sync` command is still work in progress and will receive further functionality and documentation over time.
:::

### What it does

On each run, for every schema in the contract, the command:

- **Edits your existing dbt model YAML in place**, preserving comments and formatting. It merges the contract's column metadata and tests into the matching model (matched case-insensitively by model name, or by `physicalName` with `--model-resolution physicalName`), marking everything it manages with a `config.meta.datacontract_cli` block. Model YAML and singular SQL paths honor `model-paths` and `test-paths` in `dbt_project.yml`.
- **Writes each column's `data_type`.** The type comes from the contract's `physicalType` or `logicalType`, mapped to the selected warehouse dialect — the ODCS server's `type` (from `--server`, or the type the declared servers share) — the same mapping `export dbt-models` uses (so `BIGINT` may become `NUMBER` on Snowflake, `text` on Postgres, etc.). With no resolvable dialect a `physicalType` is written as-is, and a column that declares only a `logicalType` is skipped with a warning (pass `--server` or add a `physicalType`). The contract owns the type: it overwrites an existing `data_type`, and a column the contract leaves untyped keeps its current type unless `--prune` is set. (Under dbt model contracts, `contract: {enforced: true}`, a type that genuinely disagrees with the model's output will fail `dbt parse` — as intended.)
- **Creates a model YAML file** only when a model has a `.sql` file but no schema YAML yet — a sidecar next to the `.sql`.
- **Emits singular SQL tests** — under `<test-paths>/datacontract_cli/<contract-id>/` — for ODCS `quality` rules and field bounds (length, regex, numeric range, row count, composite-key uniqueness) that can't be expressed as native YAML tests. These are self-contained SQL, so your project needs no `dbt_utils` or `dbt_expectations`. Each contract owns its own singular SQL files, so syncing one contract never removes another's.

Your own columns, tags, and tests are left untouched; pass `--prune` to also remove model columns and tags the contract doesn't declare. It does not run the tests by default — pass `--run-tests` to also run them, or run `datacontract dbt test` afterwards.

### Prerequisites

- `dbt-core` plus an adapter (e.g. `dbt-duckdb`, `dbt-postgres`) on `PATH` — needed only to *run* the tests. Generating them (`dbt sync` without `--run-tests`) doesn't require dbt.

### Options

| Option | Default | Description |
|---|---|---|
| `--project-dir` | current dir | Path to the dbt project root (must contain `dbt_project.yml`). |
| `--schema-name` | `all` | Which ODCS schema object to sync, by name. |
| `--model-resolution` | `name` | How to map an ODCS schema to a dbt model name: `name` or `physicalName`. |
| `--prune` / `--no-prune` | off | Remove model columns and tags that are not declared in the contract. |
| `--target` | — | Forwarded to `dbt test --target`. |
| `--profiles-dir` | — | Forwarded to `dbt test --profiles-dir`. |
| `--run-tests` / `--skip-tests` | `--skip-tests` | Run `dbt test` after syncing. Required by `--publish`/`--server`. |
| `--publish` | — | URL to publish the results to. |
| `--server` | — | ODCS server whose `type` is the dialect for mapping the contract's types to column `data_type`s, and the server name for published test results. |

See the [`dbt` command reference](./commands/dbt.md).

### Versioned models

If your project uses [dbt model versions](https://docs.getdbt.com/docs/mesh/govern/model-versions) — a `versions:` block backed by `orders_v1.sql`, `orders_v2.sql`, … — you can keep one ODCS contract per model version and sync them into a single versioned model. Which dbt version a contract targets is taken from a `v<N>` token in its **filename**: `orders-v2.odcs.yaml` → dbt version `2` (zero-padded `v02` is accepted). The `.sql` files must already exist; `dbt sync` never creates or renames them.

The `v<N>` token only takes effect when a matching versioned model exists on disk — a `<model>_v<N>.sql`, or a model whose YAML already declares a `versions:` block. Otherwise the token is ignored and the contract syncs into a plain, unversioned model named `<model>` (so `orders-v2.odcs.yaml` against a lone `orders.sql` updates `orders` in place). Conversely, syncing an *unversioned* contract onto a model that already has a `versions:` block is refused — name the file with the target version instead.

```bash
# Two versions of the same contract → one versioned `orders` model
datacontract dbt sync orders-v1.odcs.yaml orders-v2.odcs.yaml
```

This merges both contracts into one model entry: columns and tests shared by all versions live in the top-level `columns:` (each test's `config.meta.datacontract_cli.contract_versions` lists the versions that declare it); columns absent from a version are `exclude`d from its `versions:` bullet; and a column whose tests differ between versions becomes a per-version override. A column's `data_type` is version-specific too — the top-level carries the latest version's type, and any version whose type differs gets a per-version override with its own `data_type`. Singular SQL tests reference the right version via `ref('orders', version=N)`.

Syncing is **additive and order-independent**: syncing `orders-v2.odcs.yaml` alone updates v2 and leaves v1 exactly as it was, so syncing versions one at a time and all at once produce the same result. Versions you don't pass are never touched, and retiring a version (removing its `versions:` bullet, `.sql`, and generated tests) is your call.

`datacontract dbt test orders-v2.odcs.yaml` scopes the run to that model version's node (`orders.v2`), so only v2's tests run.

## `datacontract dbt test`

`dbt test` runs the contract-managed tests that `dbt sync` generated, reports the results, and optionally publishes them. It never modifies project files — run `dbt sync` first to (re)generate the tests. Like `dbt sync`, it accepts multiple contracts (paths, a glob, or every `*.odcs.yaml` in the project); the run is scoped to the requested contracts' models, and each contract's results are reported and published separately.

```bash
# A single contract
datacontract dbt test orders.odcs.yaml --project-dir ./warehouse --target dev

# Every contract in the project
datacontract dbt test --project-dir ./warehouse
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
datacontract import dbt --source manifest.json --model orders --model line_items

# Import all tables
datacontract import dbt --source manifest.json
```

See the [dbt importer](./imports/dbt.md).
