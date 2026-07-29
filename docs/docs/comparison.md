---
sidebar_position: 21
title: "Comparison with other Tools"
description: "How the Data Contract CLI compares to Great Expectations (GX Core), Soda Core, and dbt contracts — license, governance, contract format, and scope."
---

# Comparison with other Tools

Data quality and data contract tooling changed a lot in 2026: Great Expectations and Soda both changed hands or changed licenses, and dbt Labs merged into Fivetran. This page compares the Data Contract CLI with the three tools it is most often evaluated against — **[Great Expectations (GX Core)](https://greatexpectations.io/)**, **[Soda Core](https://www.soda.io/)**, and **[dbt contracts](https://docs.getdbt.com/docs/collaborate/govern/model-contracts)** — so you can pick the right one, or combine them.

All facts below were verified in July 2026, with sources linked at the bottom of the page.

## At a glance

| | Data Contract CLI | GX Core | Soda Core | dbt contracts |
|---|---|---|---|---|
| **License** | MIT | Apache 2.0 | Elastic License 2.0 (source-available) since v4 | Apache 2.0 (dbt Core) |
| **Maintained by** | Entropy Data and the community | Fivetran (steward since May 2026) | Soda (vendor) | dbt Labs, part of Fivetran since June 2026 |
| **Contract format** | [ODCS](./open-data-contract-standard.md), an open standard governed by [Bitol](https://bitol.io/) under the Linux Foundation AI & Data | Expectation Suites (tool-specific JSON/Python) | Soda contract YAML (tool-specific) | dbt model YAML inside a dbt project |
| **Format is vendor-neutral** | Yes | No | No | No |
| **What the contract covers** | Schema, semantics, quality rules, servers, service levels, ownership | Quality expectations | Schema and quality checks | Column names, data types, constraints |
| **When checks run** | On demand, in CI/CD, or scheduled — against data that already exists | After the data is written | After the data is written | At build time (preflight check plus DDL constraints) |
| **Where it runs** | Standalone CLI, Python library, Docker, GitHub Action, REST API | Python library | CLI and Python library | Only inside a dbt run |
| **Data sources** | [18+](./testing/index.md), including Snowflake, Databricks, BigQuery, Kafka, S3, and local files | SQL databases, Spark, pandas | Postgres, Snowflake, BigQuery, Databricks, Redshift, SQL Server, Fabric, Synapse, Athena, DuckDB | Whatever your dbt adapter supports |
| **Contract is shareable with consumers** | Yes — one portable YAML file | No | Within Soda | No — scoped to one dbt project |

## Data Contract CLI

The CLI is MIT-licensed and built natively on the **Open Data Contract Standard**. The contract is a single YAML file that describes structure, semantics, quality rules, servers, and service levels — an artifact you can put in Git, review in a pull request, hand to a consumer in another team, and [export](./exports/index.md) to 25+ downstream formats.

Because the format is an open standard governed by Bitol under the Linux Foundation AI & Data, it does not belong to any vendor — including us. That is the main structural difference to the other three: with GX, Soda, and dbt, the definition lives in a tool-specific format, so the definition and the tool move together.

**Use it when** you want one portable contract that both documents the data for its consumers and is executable against 18+ platforms, and when license and governance risk matter to you.

## <img className="page-icon" src="/img/icons/great-expectations.svg" alt="" /> Great Expectations (GX Core)

GX Core is an established Python data quality framework, Apache 2.0-licensed, with a large expectation library. Its ownership changed in 2026: **GX Cloud was acquired by FICO** and stopped being publicly available on June 1, 2026, while **Fivetran became the steward** of the GX Core project and the open-source community.

GX describes expectations about data, not contracts. There is no portable, vendor-neutral artifact you can hand to a consuming team, and no notion of servers, service levels, or ownership.

**Use it when** you need its breadth of expectations or already have suites in production. You can keep using it from a data contract: [`datacontract export --format great-expectations`](./exports/great-expectations.md) turns a contract into a GX suite.

## <img className="page-icon" src="/img/icons/soda.svg" alt="" /> Soda Core

Soda Core changed its license with **v4 (January 2026), from Apache 2.0 to the Elastic License 2.0**. It stays source-available and free for internal use, including production, but you may no longer offer it to third parties as a hosted or managed service. Soda Core v4 also replaced the SodaCL checks language with **its own data contract format**, a breaking change with a migration tool.

So Soda now has a data contract format too, but it is Soda's format for Soda's engine, under a source-available license — not an open standard.

**Use it when** you are on the Soda platform and the ELv2 terms fit your use case. The CLI's [SodaCL export](./exports/sodacl.md) targets the checks language of Soda Core v3.

## <img className="page-icon" src="/img/icons/dbt.svg" alt="" /> dbt contracts

dbt model contracts (`contract: enforced: true`) are the strongest option for **build-time** enforcement: dbt verifies before building that the model's SQL returns the declared columns, and it puts data types and constraints into the DDL, so a violating build fails instead of shipping bad data. dbt Core stays Apache 2.0-licensed under Fivetran, which completed its merger with dbt Labs on June 1, 2026.

The limits are scope, not quality. A dbt contract lives in a dbt project and applies to models built by dbt: it does not describe a Kafka topic, an S3 bucket, or a table someone else's pipeline writes, it carries no servers, SLAs, or ownership, and a consumer outside your project cannot use it as an agreement. Contracts also only cover supported materializations, and they check structure — content is still the job of dbt tests.

**Use it when** producers and consumers live in the same dbt project and build-time failure is what you need.

## They are not mutually exclusive

A data contract is the definition; these tools are execution engines. The CLI can drive the others from one ODCS contract:

- [`datacontract dbt sync`](./dbt.md) merges the contract's schema and tests into an existing dbt project, giving you build-time enforcement from the same contract.
- [`datacontract export --format great-expectations`](./exports/great-expectations.md) generates a GX suite.
- [`datacontract export --format sodacl`](./exports/sodacl.md) generates SodaCL checks.
- [`datacontract export --format dbt`](./exports/dbt-models.md) generates a dbt model schema, [sources](./exports/dbt-sources.md), or [staging SQL](./exports/dbt-staging-sql.md).

A common setup is: define the contract in ODCS, enforce structure at build time with dbt, and run [`datacontract test`](./testing/index.md) in CI/CD and on a schedule against the deployed data.

## Sources

- [An Update for the Great Expectations Community](https://greatexpectations.io/blog/an-update-from-great-expectations/) (May 6, 2026) and [Fivetran to Become Steward of the Great Expectations Open Source Community and GX Core Project](https://www.fivetran.com/press/fivetran-to-become-steward-of-the-great-expectations-open-source-community-and-gx-core-project)
- [Soda Core License Update: Moving to Elastic License 2.0](https://soda.io/blog/soda-core-license-update-moving-to-elastic-license) and [Introducing Soda 4.0](https://soda.io/blog/introducing-soda-4.0)
- [dbt model contracts](https://docs.getdbt.com/docs/collaborate/govern/model-contracts) and [Fivetran + dbt Labs Complete Merger](https://www.fivetran.com/press/fivetran-dbt-labs-complete-merger-to-create-the-data-infrastructure-for-trusted-ai-agents) (June 1, 2026)
