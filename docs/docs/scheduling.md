---
sidebar_position: 10
title: "Scheduling"
description: "Run data contract tests continuously and on a schedule in CI/CD, cron, and orchestrators."
---

# Scheduling

Data contracts deliver the most value when they are checked **continuously**, not just once. The recommended practice is to test contracts in CI/CD on every change and, in addition, to run them on a recurring schedule (for example daily) so you detect data drift and quality regressions in production data over time.

The [`ci`](./commands/ci.md) command is purpose-built for this: it wraps [`test`](./commands/test.md) with CI-friendly annotations, a markdown summary, machine-readable output, and exit-code control via `--fail-on`.

## GitHub Actions (on change and scheduled)

```yaml
# .github/workflows/datacontract.yml
name: Data Contract CI

on:
  push:
    branches: [main]
  pull_request:
  schedule:
    # Run every day at 06:00 UTC to catch data drift in production
    - cron: "0 6 * * *"

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

There is also a ready-made GitHub Action — see [datacontract/datacontract-action](https://github.com/datacontract/datacontract-action/).

## Azure DevOps

```yaml
# azure-pipelines.yml
trigger:
  branches:
    include:
      - main

schedules:
  - cron: "0 6 * * *"
    displayName: Daily data contract tests
    branches:
      include: [main]
    always: true

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

## Plain cron with Docker

If you don't have a CI system, schedule the Docker image with cron:

```cron
# Run every day at 06:00 — /etc/crontab or `crontab -e`
0 6 * * *  docker run --rm -v "/path/to/contracts:/home/datacontract" \
  -e DATACONTRACT_POSTGRES_USERNAME -e DATACONTRACT_POSTGRES_PASSWORD \
  datacontract/cli:latest ci datacontract.yaml
```

## Orchestrators (Airflow, Databricks, …)

Because the CLI is also a Python library, you can call it from any orchestrator task:

```python
from datacontract.data_contract import DataContract

def test_orders_contract():
    run = DataContract(data_contract_file="orders.odcs.yaml").test()
    if not run.has_passed():
        raise RuntimeError("Data contract tests failed")
```

Wrap this in an Airflow `PythonOperator`, a Databricks job, a Dagster op, or a Prefect task and schedule it with your orchestrator's native scheduler.

## Publishing scheduled results

To track results over time, publish each run to an Entropy Data instance:

```bash
datacontract ci datacontract.yaml --publish https://api.entropy-data.com/api/test-results
```

## Controlling failure behavior

Use `--fail-on` to decide when a scheduled run should be marked as failed:

```bash
# Fail the job on errors only (default)
datacontract ci --fail-on error datacontract.yaml

# Also fail on warnings
datacontract ci --fail-on warning datacontract.yaml

# Never fail (e.g. report-only schedules)
datacontract ci --fail-on never datacontract.yaml
```
