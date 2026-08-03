---
sidebar_position: 1
title: "Scheduling"
description: "Run data contract tests continuously: in CI/CD on every change and on a recurring schedule to catch data drift before your consumers do."
---

# Scheduling

Data contracts deliver the most value when they are checked **continuously**, not just once. The recommended practice is to test contracts in CI/CD on every change and, in addition, to run them on a recurring schedule (for example daily) so you detect data drift and quality regressions in production data over time.

The [`ci`](../commands/ci.md) command is purpose-built for automated runs: it wraps [`test`](../commands/test.md) with CI-friendly annotations, a markdown summary, machine-readable output, and exit-code control via `--fail-on`.

Two setups are covered in detail:

- **[GitHub Actions](./github-actions.md)**: test contracts in pull requests and on a cron schedule with the same workflow.
- **[Apache Airflow](./airflow.md)**: run tests as DAG tasks with the Data Contract provider, including credentials via connections, XCom results, and a results view in the Airflow UI.

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

Without a CI system or orchestrator, schedule the Docker image with cron:

```cron
# Run every day at 06:00 — /etc/crontab or `crontab -e`
0 6 * * *  docker run --rm -v "/path/to/contracts:/home/datacontract" \
  -e DATACONTRACT_POSTGRES_USERNAME -e DATACONTRACT_POSTGRES_PASSWORD \
  datacontract/cli:latest ci datacontract.yaml
```

## Other orchestrators (Databricks, Dagster, Prefect, …)

Because the CLI is also a [Python library](../python-library.md), any orchestrator task can call it directly:

```python
from datacontract.data_contract import DataContract

def test_orders_contract():
    run = DataContract(data_contract_file="orders.odcs.yaml").test()
    if not run.has_passed():
        raise RuntimeError("Data contract tests failed")
```

Wrap this in a Databricks job, a Dagster op, or a Prefect task and schedule it with the orchestrator's native scheduler. For Airflow, prefer the [provider](./airflow.md).

## Controlling failure behavior

Use `--fail-on` to decide when a run should be marked as failed:

```bash
# Fail the job on errors only (default)
datacontract ci --fail-on error datacontract.yaml

# Also fail on warnings
datacontract ci --fail-on warning datacontract.yaml

# Never fail (e.g. report-only schedules)
datacontract ci --fail-on never datacontract.yaml
```

## Publishing results

A run tells you whether the data is compliant *today*. Once several contracts run on a schedule, the next question is usually how they behave *over time*, and across teams. Publish each run to track results centrally:

```bash
datacontract ci datacontract.yaml --publish https://api.entropy-data.com/api/test-results
```

The [Airflow provider](./airflow.md) publishes automatically when an Entropy Data connection is configured. See [Integrate with Entropy Data](../entropy-data.md).

## Next steps

- Roll this out beyond a single contract: **[Adopting Data Contracts](../best-practices.md)**.
- Share the current state with your team: `datacontract export html` and the [`catalog`](../commands/catalog.md) command.
