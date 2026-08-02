---
sidebar_position: 11
title: "CI/CD"
description: "Run data contract tests in CI/CD on every change, with CI-friendly annotations, summaries, and exit-code control."
---

# CI/CD

Data contracts deliver the most value when they are checked **continuously**, not just once. Test contracts in CI/CD on every change so a breaking change is caught in the pull request that introduces it. In addition, run them on a recurring schedule to detect data drift in production over time, see [Scheduling](./scheduling/index.md).

The [`ci`](./commands/ci.md) command is purpose-built for pipelines: it wraps [`test`](./commands/test.md) with CI-friendly annotations, a markdown summary, machine-readable output, and exit-code control via `--fail-on`.

## GitHub Actions

The quickest route is the ready-made **[datacontract/datacontract-action](https://github.com/datacontract/datacontract-action/)**. To run the CLI directly:

```yaml
# .github/workflows/datacontract.yml
name: Data Contract CI

on:
  push:
    branches: [main]
  pull_request:

jobs:
  datacontract-ci:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: "3.11"
      - run: pip install datacontract-cli
      # Test one or more data contracts (supports globs, e.g. contracts/*.yaml)
      - run: datacontract ci datacontract.yaml
        env:
          DATACONTRACT_POSTGRES_USERNAME: ${{ secrets.DB_USERNAME }}
          DATACONTRACT_POSTGRES_PASSWORD: ${{ secrets.DB_PASSWORD }}
```

To also run this workflow nightly, add a `schedule` trigger, see [Scheduling](./scheduling/index.md).

## Azure DevOps

```yaml
# azure-pipelines.yml
trigger:
  branches:
    include:
      - main

pool:
  vmImage: "ubuntu-latest"

steps:
  - task: UsePythonVersion@0
    inputs:
      versionSpec: "3.11"
  - script: pip install datacontract-cli
    displayName: "Install datacontract-cli"
  - script: datacontract ci datacontract.yaml
    displayName: "Run data contract tests"
```

## Controlling failure behavior

Use `--fail-on` to decide when a pipeline should be marked as failed:

```bash
# Fail the job on errors only (default)
datacontract ci --fail-on error datacontract.yaml

# Also fail on warnings
datacontract ci --fail-on warning datacontract.yaml

# Never fail (e.g. report-only runs)
datacontract ci --fail-on never datacontract.yaml
```

## Publishing results

Publish each run to track results centrally, over time and across teams:

```bash
datacontract ci datacontract.yaml --publish https://api.entropy-data.com/api/test-results
```

See [Integrate with Entropy Data](./entropy-data.md).

## Next steps

- Catch data drift between changes: **[Scheduling](./scheduling/index.md)**, e.g. with the [Airflow provider](./scheduling/airflow.md).
- Roll this out beyond a single contract: **[Adopting Data Contracts](./best-practices.md)**.
- Share the current state with your team: `datacontract export html` and the [`catalog`](./commands/catalog.md) command.
