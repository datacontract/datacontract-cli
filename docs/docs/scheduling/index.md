---
sidebar_position: 1
title: "Scheduling"
description: "Run data contract tests on a recurring schedule to detect data drift and quality regressions in production data."
---

# Scheduling

A test in [CI/CD](../ci-cd.md) tells you a change is safe at the moment it ships. Data can still drift afterwards: an upstream system changes a format, a pipeline stops loading, quality degrades slowly. Running contract tests on a recurring schedule (for example daily) catches these regressions in production data before your consumers do.

## Apache Airflow

If you run Airflow, use the **[Data Contract Provider for Apache Airflow](./airflow.md)**. It ships a `DataContractTestOperator` that runs the tests as a task, fails the task when the contract is violated, resolves credentials through Airflow connections, pushes the full run report to XCom, and adds a results view to the Airflow UI.

```python
from datetime import datetime
from airflow.sdk import dag
from datacontract_provider.operators.datacontract import DataContractTestOperator


@dag(schedule="0 2 * * *", start_date=datetime(2026, 1, 1), catchup=False)
def nightly_datacontract_test():
    DataContractTestOperator(
        task_id="test_orders_contract",
        data_contract_file="https://demo.datacontract.com/orders-latest/datacontract.yaml",
        server="production",
    )


nightly_datacontract_test()
```

See the full guide: **[Apache Airflow](./airflow.md)**.

## Scheduled CI pipelines

CI systems can run pipelines on a cron schedule, so the same pipeline that tests contracts on every change can also run nightly. In GitHub Actions, add a `schedule` trigger to the workflow from the [CI/CD guide](../ci-cd.md):

```yaml
on:
  push:
    branches: [main]
  schedule:
    # Run every day at 06:00 UTC to catch data drift in production
    - cron: "0 6 * * *"
```

Azure DevOps has the same concept with the `schedules` keyword. The [`ci`](../commands/ci.md) command's `--fail-on` option controls when a scheduled run is marked as failed, e.g. `--fail-on never` for report-only schedules.

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

Wrap this in a Databricks job, a Dagster op, or a Prefect task and schedule it with the orchestrator's native scheduler.

## Publishing scheduled results

A scheduled run tells you whether the data is compliant *today*. Once several contracts run on a schedule, the next question is usually how they behave *over time*, and across teams. Publish each run to track results centrally:

```bash
datacontract ci datacontract.yaml --publish https://api.entropy-data.com/api/test-results
```

The Airflow provider publishes automatically when an Entropy Data connection is configured. See [Integrate with Entropy Data](../entropy-data.md).

## Next steps

- Set up the Airflow provider: **[Apache Airflow](./airflow.md)**.
- Test on every change, too: **[CI/CD](../ci-cd.md)**.
- Roll this out beyond a single contract: **[Adopting Data Contracts](../best-practices.md)**.
