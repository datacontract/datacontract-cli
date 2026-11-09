---
sidebar_position: 24.5
title: "Recognition"
description: "Industry recognition of the Data Contract CLI, and blog posts and public repositories from organizations that use it."
---

# Recognition

This page lists public sources where organizations say they use the Data Contract CLI, plus the reviews it has received. All sources were checked in October 2026.

Do you use the CLI and write about it? [Open a pull request](https://github.com/datacontract/datacontract-cli/edit/main/docs/docs/recognition.md) to add your blog post or repository.

## Industry recognition

- **[Thoughtworks Technology Radar](https://www.thoughtworks.com/radar/tools/data-contract-cli)** (November 2025), ring **Trial**: Thoughtworks recommends the CLI for creating and validating data contracts, detecting breaking changes, and enforcing contract governance between data products in CI/CD pipelines.
- **[Astrafy](https://astrafy.io/the-hub/blog/technical/data-contract-cli-the-future-of-data-contract-definition)** (April 2024), *Data Contract CLI — The future of Data Contract definition?*: an evaluation by the data consultancy, which found that the CLI meets most of its requirements.

## Blog posts

| Organization | Post | How they use the CLI |
|---|---|---|
| **10X, Inc.** (Japan) | [しなやかなデータ連携に向けたdatacontract-cliへの貢献について紹介します](https://product.10x.co.jp/entry/2025/01/27/200416) (January 2025) | Adopted the CLI for its data contracts and contributed BigQuery and dbt features needed for production use. |
| **CADDi** (Japan) | [15,000カラムの機密性を守る - CTOと実践したデータガバナンスの実現](https://caddi.tech/2025/12/23/112420) (December 2025) | A [custom importer](./extending.md) generates contracts from a spreadsheet of column confidentiality levels; the output drives BigQuery policy tags and masking through Terraform. |
| **Finatext** (Japan) | [Data Contract CLIでデータテストを行い、dbtのschemaを生成する CI/CD](https://zenn.dev/finatext/articles/data-contract-dbt-cicd) (December 2024) | A GitHub Actions pipeline that lints contracts, tests them against real data, checks for breaking changes, generates an HTML catalog, and exports dbt schemas. |

## Public repositories and issues

| Organization | Source | How they use the CLI |
|---|---|---|
| **Kartverket** (Norwegian Mapping Authority) | [kartverket/dask-modules](https://github.com/kartverket/dask-modules/blob/main/scripts/validate_data_contract/validate_data_contract.py) and [issue #1280](https://github.com/datacontract/datacontract-cli/issues/1280) | Imports contracts from Databricks Unity Catalog and validates tables with `datacontract test` on its data platform. |
| **Association Infoclimat** (France) | [AssociationInfoclimat/data-platform](https://github.com/AssociationInfoclimat/data-platform) | Manages the association's data governance with ODCS contracts and the CLI. |
| **UN Task Team for Scanner Data** | [price-stats-data-catalogue](https://github.com/UN-Task-Team-for-Scanner-Data/price-stats-data-catalogue/blob/main/.github/workflows/deploy.yml) | A proof-of-concept data catalog for price statistics researchers, built with `datacontract catalog` and published on [GitHub Pages](https://un-task-team-for-scanner-data.github.io/price-stats-data-catalogue/). |
| **Voloridge Investment Management** | [Issue #196](https://github.com/datacontract/datacontract-cli/issues/196) | Adopting the CLI to enforce stricter guarantees on data shared between teams; requested the SQL Server support that the CLI now has. |
