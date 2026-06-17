---
sidebar_position: 1
slug: /
title: "What is Data Contract CLI?"
description: "An open-source command-line tool for working with data contracts based on the Open Data Contract Standard (ODCS)."
---

# What is Data Contract CLI?

The `datacontract` CLI is an open-source command-line tool for working with [data contracts](https://datacontract.com).

It natively supports the [Open Data Contract Standard (ODCS)](https://bitol-io.github.io/open-data-contract-standard/latest/) to:

- **Lint** data contracts and validate them against the ODCS JSON Schema.
- **Connect** to data sources such as Snowflake, BigQuery, Databricks, Postgres, Kafka, S3, and many more.
- **Test** that the actual data complies with the schema and quality expectations defined in the contract.
- **Export** a contract to 25+ formats (SQL DDL, dbt, Avro, JSON Schema, HTML, Protobuf, …).
- **Import** an existing schema (SQL, dbt, BigQuery, Glue, Excel, …) into a data contract.

The tool is written in Python. It can be used as a standalone CLI tool, in a CI/CD pipeline, or directly as a Python library.

![Main features of the Data Contract CLI](/img/datacontractcli.png)

## Why data contracts?

A data contract is a machine-readable, versioned agreement that describes the **structure**, **semantics**, **quality**, and **service levels** of a data set. Because the contract is a single file, it can be:

- stored in Git next to your code,
- reviewed in pull requests,
- linted and tested automatically in CI/CD, and
- used to generate downstream artifacts (DDL, dbt models, schemas, documentation).

A typical contract has a `servers` section with endpoint details, a `schema` describing the structure and semantics of the data, plus `service levels` and `quality` attributes that describe expectations such as freshness and number of rows. This is enough information to connect to the data source and check that the actual data product is compliant.

## How it works

When you run `datacontract test`, the CLI connects to a data source and runs schema and quality tests to verify that the data contract is valid. Internally it uses different engines based on the server `type` — it connects with DuckDB, Spark, or a native connection, executes most checks with [_ibis_](https://ibis-project.org/) (compiling dialect-specific SQL per backend), and validates JSON with [_fastjsonschema_](https://pypi.org/project/fastjsonschema/).

## Next steps

- New here? Start with the **[Quickstart](./quickstart.md)**.
- Learn the underlying format in **[Open Data Contract Standard](./open-data-contract-standard.md)**.
- Author contracts visually with the **[Data Contract Editor](./editor.md)**.
- Run checks against real data with **[Data Contract Testing](./testing.md)**.
- See every command in the **[Commands reference](./commands/index.md)**.

## Related links

- Website: [datacontract.com](https://datacontract.com)
- Source code: [github.com/datacontract/datacontract-cli](https://github.com/datacontract/datacontract-cli)
- Community Slack: [datacontract.com/slack](https://datacontract.com/slack)
- GitHub Action: [datacontract/datacontract-action](https://github.com/datacontract/datacontract-action/)
