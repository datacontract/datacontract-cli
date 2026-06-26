# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [1.0.9] - 2026-06-26

### Fixed
- `datacontract test` against Kafka no longer reports every field as null for plain (non-Confluent Schema Registry) Avro messages (#1344)
- Honor the `pattern` argument in `invalidValues` quality checks (#1346)

## [1.0.8] - 2026-06-25

### Fixed
- `datacontract test` against Redshift no longer fails with `relation "pg_catalog.pg_enum" does not exist`. Redshift rides the Postgres ibis backend, whose schema introspection joins `pg_catalog.pg_enum` to detect enum columns — a relation Redshift does not expose. Introspection now omits that join (Redshift has no enum types).

## [1.0.7] - 2026-06-25

### Added
- New global option `--system-truststore` (env `DATACONTRACT_SYSTEM_TRUSTSTORE`) to verify TLS using the operating system's certificate trust store, for use behind corporate proxies or with internal CAs.

## [1.0.6] - 2026-06-24

### Fixed
- `datacontract test` against Redshift no longer fails with `column "current_schema" does not exist`. Redshift rides the Postgres ibis backend, whose introspection resolved the active schema with `SELECT current_schema` (no parentheses) — valid on PostgreSQL but rejected by Redshift, which only supports `current_schema()`. The configured server `schema` is now passed explicitly during introspection, skipping that query.

## [1.0.5] - 2026-06-24

### Fixed
- `datacontract test` now only supports logicalTypes. Previously physicalType was preferrerd and used even if logicalType did not exist. 
- `datacontract test` field type check now compares the full structured type tree for `object` and `array` logical types.
- Unknown and unsupported types are silently ignored rather than failing the check. Specifically the `map` type is not supported until ODCS version v3.2.0 and is also ignored. 
- `datacontract --help` no longer fails with `ModuleNotFoundError: No module named 'ibis'` when the optional `ibis` extra is not installed.
- `datacontract test` against Oracle now qualifies tables with the configured server `schema` (owner), fixing `Could not read model '<table>': <table>` when the login user differs from the table owner.



## [1.0.4] - 2026-06-22

### Added
- `datacontract test` validates Azure Blob Storage / ADLS Gen2 file metadata against a data contract used as a storage policy (#1227)
- `datacontract test` against Trino now supports `DATACONTRACT_TRINO_AUTHENTICATION=jwt` with `DATACONTRACT_TRINO_JWT_TOKEN`, and `DATACONTRACT_TRINO_AUTHENTICATION=oauth2` for the interactive browser flow.
- `datacontract export sql --dialect clickhouse`: export data contracts to ClickHouse SQL DDL. (#1293)
- Example data contracts and import sources under `examples/`, used as the worked examples on the docs export and import pages.

### Fixed
- `datacontract import unity` now imports struct and array columns as structured ODCS types instead of only a flat type string: structs get nested `properties`, arrays get `items` (parsed recursively from Unity's `type_json`, including descriptions on nested fields). Arrays also get the correct `logicalType: array` (previously `object`); this logical type fix applies to the `sql` and `snowflake` importers as well. Map columns and other unmappable SQL types now leave `logicalType` unset (instead of the invalid `object`) until ODCS v3.2 adds `logicalType: map` (RFC 0030). (#1280)
- `datacontract export dcs` no longer crashes on data contracts with a structured description or a standard server.
- `datacontract test` against Oracle releases before 23ai no longer fails every check with `ORA-00923: FROM keyword not found where expected` during schema introspection.
- `datacontract test` now recognizes Oracle `VARCHAR2`/`NVARCHAR2` (with or without a length, e.g. `VARCHAR2(4000)`) as string types in the field type check.

## [1.0.3] - 2026-06-15

### Added
- `datacontract import powerbi` imports a data contract from a Power BI semantic model (.pbit, .bim, or .json) (#1232,#1233 @dmaresma)

### Changed
- `datacontract edit` shows the edited filename in the editor header, no longer offers New/Load Example/Open, and Cancel reverts to the file on disk

### Fixed
- `datacontract test` no longer aborts remaining quality checks after a SQL quality check falls back to native execution on DuckDB-backed sources (#1302)
- Athena: pass `DATACONTRACT_S3_SESSION_TOKEN` to the connection again, fixing `UnrecognizedClientException` with temporary AWS credentials (#1309)

## [1.0.2] - 2026-06-11

### Added
- `datacontract edit` now accepts a URL: it asks to download a local copy and opens that in the editor, using the configured API key (e.g., `ENTROPY_DATA_API_KEY`) to fetch the file.
- BigQuery: added support for a separate billing/compute project via the `DATACONTRACT_BIGQUERY_BILLING_PROJECT` environment variable. When set, query jobs are submitted to (and billed against) the billing project while data is read from the `project` specified in the server config. This enables cross-project and cross-organisation validation without requiring `bigquery.jobUser` on the data project.
### Fixed
- `datacontract test` no longer fails on Spark/Databricks tables containing columns of types ibis cannot represent, such as VariantType (#1296)
- The `postgres` and `redshift` extras now install `psycopg[binary]`, whose wheels bundle the libpq client library. Previously, `datacontract test` against PostgreSQL/Redshift failed on machines without PostgreSQL client libraries installed (`couldn't import psycopg: no pq wrapper available`).

## [1.0.1] - 2026-06-10

### Added
- Environment variables (e.g., credentials for `datacontract test`) are now also loaded from a `.env` file in the current working directory, walking up parent directories until one is found. Already-set environment variables take precedence over `.env` values, so exported variables and CI secrets keep working unchanged. (#1295)
- `datacontract edit <file>` opens a local data contract file in the [Data Contract Editor](https://github.com/datacontract/datacontract-editor) (web UI). Starts a local web server (default port 4243, requires the `api` extra) that serves the editor, writes saves directly back to the file, and doubles as the editor's test runner: "Run test" in the editor executes the data contract tests locally via the server's own `/test` endpoint. The editor is bundled with the CLI and works offline; `--editor-version` loads a specific editor version from the CDN instead, `--editor-assets-url` a self-hosted build. If the file does not exist, the command offers to initialize a new data contract (same template as `datacontract init`). Saving gives feedback in the editor and on the console.

### Fixed
- `datacontract test` no longer fails with `Compilation rule for RegexSearch operation is not defined` when a contract uses `logicalTypeOptions.pattern` (or `pattern`) against SQL Server. SQL Server has no native regex operator, so the ibis mssql backend cannot compile `re_search`; pattern checks now fall back to a `PATINDEX(...) > 0` LIKE match, restoring the behaviour of the former soda-core engine. Patterns that use real regex syntax (anchors, quantifiers, groups, `.`) cannot be expressed as a T-SQL LIKE pattern and now raise a clear error instead of failing cryptically. (#1284)

## [1.0.0] - 2026-06-04

### Breaking Changes
- Replaced the Soda Core quality/test engine with [ibis](https://ibis-project.org/). `datacontract test` now compiles schema and quality checks into ibis expressions (dialect-correct SQL per backend via sqlglot, local/remote files via DuckDB) instead of generating SodaCL. Install extras now pull `ibis-framework[<backend>]` instead of `soda-core-*`. Check semantics and pass/fail results are preserved for the supported sources (postgres, redshift, mysql, snowflake, bigquery, databricks, sqlserver, oracle, trino, athena, impala, kafka/dataframe via the ibis Spark backend, and local/S3/GCS/Azure files).
- Raw SodaCL custom quality checks (`quality.type: custom` with `engine: soda`) are no longer executed and now report a warning. Migrate them to `quality.type: sql` or a library metric (e.g. `metric: rowCount`).

### Added
- Python 3.13 and 3.14 support (`requires-python` now allows 3.10–3.14). On 3.13/3.14 the Spark-backed extras resolve to PySpark 4.0 (Spark 3.5 has no 3.13+ build); the Kafka/Avro connector jars already adapt to the runtime Spark/Scala version. `create_spark_session` now pins `PYSPARK_PYTHON`/`PYSPARK_DRIVER_PYTHON` to the running interpreter so Spark's Python workers match the driver.
- `datacontract test` against Databricks now supports more authentication methods beyond the personal access token (`DATACONTRACT_DATABRICKS_TOKEN`): an OAuth service principal for machine-to-machine auth (`DATACONTRACT_DATABRICKS_CLIENT_ID` + `DATACONTRACT_DATABRICKS_CLIENT_SECRET`), a local config profile via the Databricks SDK unified auth (`DATACONTRACT_DATABRICKS_PROFILE`, also covers Azure CLI/MSI), and an explicit connector auth type (`DATACONTRACT_DATABRICKS_AUTH_TYPE`, e.g. `databricks-oauth` for the interactive browser flow).
- `datacontract test` now records structured `diagnostics` on each check explaining why it passed or failed: the metric, measured value, threshold, and (for "bad row" metrics) the total row count and failed fraction. `invalid_count` checks also report the validity rule they enforced (e.g. `{"max_length": 20}`, `{"pattern": "^.+@.+$"}`). The diagnostics surface in the JSON output and the JUnit failure text. This replaces the Soda-specific `diagnostics` payload that the ibis migration had left unpopulated.
- `datacontract test` now honors ODCS `quality.unit: percent` on the count-of-bad-rows library metrics (`nullValues`, `missingValues`, `invalidValues`). The threshold is then compared against the failed fraction (0–100) of the model row count instead of an absolute count, so e.g. `metric: nullValues`, `unit: percent`, `mustBeLessThan: 5` passes when fewer than 5% of rows are null. Percent on metrics where a row fraction has no meaning (`rowCount`, `duplicateValues`) logs a warning and falls back to the absolute count. The measured `percent` is added to the check diagnostics.
- `datacontract test` now honors ODCS `quality.severity`: a non-blocking severity (`info`, `warning`, `low`, `minor`, `trivial`) downgrades a failing quality check to a `warning` instead of a `failed`, so it no longer fails the run. Any other severity (or none) still fails. The severity is recorded in the check diagnostics.
- `datacontract test --include-failed-samples` collects a small sample of the rows that failed each `missing`/`invalid`/`duplicate` check (off by default). Each sample is restricted to the contract's identifier columns (`unique` / `primaryKey` fields) plus the offending column; duplicate checks report the duplicated key values and their counts. Columns whose ODCS `classification` marks them sensitive (`pii`, `personal`, `confidential`, `restricted`, `sensitive`, `secret`) are omitted. Samples are capped at 5 rows per check and surface on `Check.failed_samples` in the JSON output and in the JUnit failure text. This is local-only and needs no Soda Cloud (soda-core itself collects failed-row samples only via Soda Cloud).

### Changed
- MySQL is tested through DuckDB's `mysql` extension instead of ibis's native MySQL backend, so the `mysql` extra stays pure-pip (no `mysqlclient` C build / system MySQL client libraries required).
- Bumped DuckDB to the 1.5.x line (from 1.0.x) with the bundled `duckdb-extension-*` wheels (httpfs/aws/azure) pinned in lockstep. The 1.5.x extension wheels publish arm64 Linux builds, so air-gapped installs on arm64 Linux are now supported (the previous platform skip markers were removed).
- The Kafka/Avro Spark connector jars are now derived from the installed PySpark at runtime (Spark version + Scala binary version), so both PySpark 3.5.x (Scala 2.12) and 4.x (Scala 2.13) work. The `kafka` and `databricks` extras allow `pyspark<5.0`.
- `import protobuf` now uses the pure-Python `proto-schema-parser` instead of the `protoc` system binary. The `protobuf` extra no longer requires `protoc` (or the `protobuf` runtime), so `.proto` import works out of the box, including transitive imports across subdirectories.
- Container image is now based on [Docker Hardened Images](https://hub.docker.com/hardened-images/catalog/dhi/python): signed, ships SBOM/VEX, and has tighter CVE patch SLAs than upstream Debian. Runs as nonroot (uid 65532) instead of root. `pip` / `uv` installs at build time are routed through Socket Firewall Free, which blocks malicious dependencies. (#1275, #1277)
- Container image now ships Eclipse Temurin JRE 17, so PySpark-backed engines (Kafka, Spark) actually run inside the image — previously they failed at `SparkSession` startup because the base image had no JVM. End users pulling `datacontract/cli` are unaffected by the build-side changes. (#1277)

### Fixed
- DuckDB S3 secret creation no longer fails (`Secret Validation Failure`) on DuckDB ≥1.5: explicit `KEY_ID`/`SECRET` now use the default `config` provider instead of `CREDENTIAL_CHAIN`.
- `import csv` no longer fails with a DuckDB binder error on DuckDB ≥1.5 (the uniqueness probe now uses `count(DISTINCT ...)` via SQL).

### Removed
- The `soda-core` runtime dependency and all `soda-core-*` install extras, plus the `setuptools` runtime shim they required. The `sodacl` export format (`datacontract export sodacl`) is unchanged and is now generated independently of any Soda runtime.
- The unused `details` field on test-result checks (`Run.checks[].details`). It was a Soda-era placeholder that was never populated; the new structured `diagnostics` field replaces it. The JUnit failure text no longer prints a `Details:` line.

## [0.12.5] - 2026-05-30

### Added
- Resolve `authoritativeDefinitions[type=definition]` on schema properties, filling fields the contract author left unset (#1261)
  - **Breaking:** Per default, any resolution failure of `authoritativeDefinitions[type in {definition, semantics}]` now rejects the contract on `lint`, `test`, `ci`, `export`, and `changelog`. (#1261)
  - Resolve `authoritativeDefinitions[type=semantics]` (and the legacy `type=semantic`) the same way. A `url:` that points at the configured entropy-data host is fetched directly; a `url:` that's an IRI (host doesn't match) is routed through `GET /api/semantics?iri=...` on the configured host, which uses the API key's organization to resolve. (#1262)
  - `--no-inline-references` flag to skip the HTTP fetch (#1261)
- When `--json-schema` points at a custom JSON Schema, the ODCS Pydantic step now accepts extra top-level fields the schema allows (#1266)

### Changed
- JSON Schema validation errors now identify the offending schema and property by name instead of array indices (#1255 @dmaresma)
- `test`, `lint`, and `ci` now infer `--output-format` from the `--output` file extension when not given (`.json` → json, `.xml` → junit) (#1156 @dallylee)

### Fixed
- Schema type check no longer fails for `varchar(n)` columns on Databricks with PySpark 4.0+, and for `map` and `varchar` types nested inside `struct` columns; affected columns emit a warning and skip the type check instead (#1219,#1245 @IchEssBlumen)
- `WARNING`/`ERROR` log messages are no longer hidden by default for `import`, `export`, `changelog`, `catalog`, `dbt`, and `publish` (#1264)
- `datacontract test` against S3, GCS, and Azure no longer fails with `Failed to download extension` in air-gapped containers. The required DuckDB extensions are now bundled via the `s3`/`gcs`/`azure` install extras (#1191 @ParenParikh)
- JSON/CSV/Parquet with DuckDB: `field_is_present` check now correctly detects missing columns (#1065,#1163 @hieusats)
- `import dbt --model <name>.vN` now correctly imports the specified version of a versioned dbt model. Previously the filter compared the full `name.vN` string against `node["name"]` (which is always the bare base name), producing a silent empty contract (#1249 @willbowditch)

## [0.12.4] - 2026-05-21

### Added
- `datacontract test` now logs the Data Contract CLI version and whether it ran as a local CLI or through the FastAPI server (including the request URL) as part of the test result logs

### Fixed
- Schema checks now resolve each property by its `physicalName` when set (falling back to `name`), matching the existing table-level resolution and the SQL/BigQuery exporters. Previously a property whose logical `name` differed from its physical column (e.g. `name: brand` with `physicalName: BRAND`) failed the presence and type checks even though the physical column existed (#1246)

## [0.12.3] - 2026-05-18

### Added
- new `datacontract dbt sync` command: generate dbt tests from an ODCS contract, then run `dbt test` for them, and optionally publish the results to Entropy Data (#1222, #1235)
- `redshift` server type for `datacontract test` (requires `pip install datacontract-cli[redshift]`). (#1236)

### Fixed
- SQL type converter: emit canonical `decimal`/`numeric` per dialect (Postgres → `numeric`, MySQL → `decimal`) so `test`'s column-type check matches `information_schema` (#1237)

## [0.12.2] - 2026-05-05

### Added
- `impala` extra (`pip install datacontract-cli[impala]`) — pulls in `soda-core-impala`. Impala engine support landed in #965 but the install extra was never added; users had to install `soda-core-impala` manually. Also included in `[all]`.

### Changed
- **breaking:** drop the `dbt` extra and the `dbt-core` dependency. `import dbt` now reads `manifest.json` directly with no third-party dependency, and works without installing any extra. Minimum supported manifest schema version is v9 (dbt 1.5+). Users who installed `datacontract-cli[dbt]` should switch to plain `datacontract-cli`.
- **breaking:** the `protobuf` extra now requires the `protoc` compiler installed on the system. Replaces the bundled `grpcio-tools` (~50 MB of platform-specific protoc binaries) with the lighter `protobuf` runtime (`>=3.20,<7.0`). `import protobuf` raises a clear error with platform-specific install hints if `protoc` is not on `PATH`. Install with `brew install protobuf` (macOS), `sudo apt install protobuf-compiler` (Debian/Ubuntu), etc. — see README.

### Fixed
- README install table: add missing `csv`, `excel`, and `oracle` extras. The matching `[project.optional-dependencies]` entries already existed but were undocumented.
- quality: support `{object}` and `${object}` placeholder in SQL quality queries as the ODCS-spec name for the current schema object (alias for `{model}`/`{table}`) (#676)
- `changelog` command help text now advertises `(url or path)` for V1/V2 arguments, clarifying that HTTP/HTTPS URLs are accepted (#1162)
- **breaking:** `test` command now exits non-zero when a server is specified, but soda-core fails to connect or authenticate (#1181)
- correct swapped `check_type` labels  `model_qualty_sql` and `field_quality_sql` (#1187)
- `import spark` now emits a native Spark SQL physicalType (e.g. `string`) instead of Python repr (e.g. `StringType()`). Contracts imported using Spark in v0.11.0–v0.12.1 did not perform type checks and must be re-imported. (#1048)
- Re-add `setuptools` as a base dependency. soda-core's `env_helper.py` imports `from distutils.util import strtobool`; `distutils` was removed from stdlib in Python 3.12 and stripped from python-build-standalone 3.11 builds. `setuptools` provides the `distutils` shim. Previously pulled in transitively via `grpcio-tools`; now required explicitly. Reverts #1199 — see soda-core#2091.
- SLA freshness checks now quote column identifiers with special characters (#1202)
- update field / model quotation for Impala, dataframe, and Kafka (#1202)

## [0.12.1] - 2026-04-21

### Fixed
- make `--schema` a deprecated alias for `--json-schema` to (will be removed in v0.13.0)

## [0.12.0] - 2026-04-20

This release introduces several changes to improve the usability of `datacontract-cli` for AI Agents.

- **Breaking**: Several changes in the CLI syntax (#1157):
> Fix in v0.12.1: re-added `--schema` as alias for the new `--json-schema` (will be removed in v0.13.0)

| Command                                    | Old option                                    | New option                             |
  |--------------------------------------------|-----------------------------------------------|----------------------------------------|
  | `lint`, `test`, `ci`, `publish`, `catalog` | `--schema <PATH>` (will work until v0.13.0)   | `--json-schema <PATH>`                 |
  | `export`, `import`                         | `--format <FORMAT> <OPTIONS>`                 | `<FORMAT> <OPTIONS>` (drop `--format`) |
  | **Export options:**                        |                                               |                                        |
  | `export --format dbt`                      | `--format dbt`                                | `dbt-models` (format renamed)          |
  | `export --format great-expectations`       | `--sql-server-type <TYPE>`                    | `--dialect <TYPE>`                     |
  | `export --format rdf`                      | `--rdf-base <URI>`                            | `--base <URI>`                         |
  | `export --format sql`                      | `--sql-server-type <TYPE>`                    | `--dialect <TYPE>`                     |
  | `export --format sql-query`                | `--sql-server-type <TYPE>`                    | `--dialect <TYPE>`                     |
  | **Import options:**                        |                                               |                                        |
  | `import --format bigquery`                 | `--bigquery-[project\|dataset\|table] <NAME>` | `--[project\|dataset\|table] <NAME>`   |
  | `import --format dbt`                      | `--dbt-model <NAME>`                          | `--model <NAME>`                       |
  | `import --format glue`                     | `--source <NAME>`, `--glue-table <NAME>`      | `--database <NAME>`, `--table <NAME>`  |
  | `import --format iceberg`                  | `--iceberg-table <NAME>`                      | `--table <NAME>`                       |
  | `import --format unity`                    | `--unity-table-full-name <NAME>`              | `--table <NAME>`                       |
  | `import --format spark`                    | `--source <NAMES>`                            | `--tables <NAMES>`                     |
  | `import`                                   | `--template`                                  | dropped (was a no-op)                  |

The `--schema` option (referring to the ODCS JSON schema) was renamed to `--json-schema` to avoid confusion with `--schema-name`, which refers to the schema within the data contract to test for.

- Error messages for uncaught exceptions are shortened now. Pass `--debug` (or set `DATACONTRACT_CLI_DEBUG=1`) to see the full traceback. (#1175)
- Add example calls to `--help` outputs (#1176)
- Add explicit errors when required env vars for soda connections are missing (#1177)
- Validate some of the CLI options against their allowed values instead of accepting any string (#1178)


## [0.11.9] - 2026-04-20

### Added
- Added `--checks` option to `test` command to selectively run check categories: `schema`, `quality`, `servicelevel` (#678)
- Added `--schema-name` option to `test` command to test a specific schema instead of all schemas (#1079,#1085 @kelsoufi-sanofi)

### Fixed
- Move `precision`/`scale` for `number` types from `logicalTypeOptions` to `customProperties` (#1145,#1160 @davidb-tada)
- Emit placeholder server values in SQL importer so generated contracts pass lint (#1146,#1152 @Ai-chan-0411)
- Fix Protobuf export for arrays of objects and improve message/enum naming to UpperCamelCase (#1012 @Schokuroff)
- Exit with code 1 when `--server` name is not found (#1153,#1161 @Ai-chan-0411)

Thanks to @kelsoufi-sanofi for the new `--schema-name` option on `test`, and to @Schokuroff, @Ai-chan-0411, and @davidb-tada for their contributions.

## [0.11.8] - 2026-04-10

### Added
- Added `ci` command for CI/CD-optimized test runs: multi-file support, GitHub Actions annotations and step summary, Azure DevOps annotations, `--fail-on` flag, `--json` output (#1114)
- Added `changelog` command and API endpoint (#1118 @davidb-tada)
- Added opt-in `--all-errors` mode for `datacontract lint` to report all JSON Schema validation errors, with matching `all_errors` support in the Python library and API (#1125 @jmbenedetto)
- Added `--schema-name` option to custom model export (#978 @AntoineGiraud)

### Fixed
- Avro importer now raises an error for union fields with multiple non-null types, which are not supported by ODCS (#1124)
- Fix SQL export generating multiple PRIMARY KEY constraints for composite keys (#1026,#1092 @barry0451 @dwestheide)
- Preserve parametrized physicalTypes for SQL export (#1086,#1093 @barry0451 @alexander-griesbeck)
- Fix incorrect SQL type mappings: SQL Server `double`/`jsonb`, MySQL bare `varchar`, missing Trino types (#1110)
- Fix markdown export breaking table structure when extra field values contain pipe characters (#832,#1117 @barry0451 @grepwood)
- Fix dbt import using incorrect physicalType instead of actual materialization type (#1136)
- Remove unnecessary numpy dependency from databricks and kafka extras (#1135 @kayhendriksen)

Special thanks to @davidb-tada for the outstanding contribution of the new `changelog` command and API endpoint! Also thanks to @barry0451 for multiple quality fixes across the SQL exporter and markdown export, and to @AntoineGiraud and @jmbenedetto for their feature contributions.

## [0.11.7] - 2026-03-24

### Fixed
- Escape single quotes in string values for SodaCL checks (#1090)
- Escape BigQuery field and model names with backticks for SodaCL checks (#736)
- Escape Databricks model names with backticks for SodaCL checks
- Fixed catalog export SpecView not having a tags property for the index.html template (#1059)
- Fix SQL importer type mappings: binary types, datetime/time, uuid now map to correct ODCS logicalType and format (#790)

### Added
- Added support for MySQL for data contract tests (#1101)
- Support additional PyArrow types in Parquet importer (#1091)
- Populate `logicalTypeOptions.format` for SQL import from binary and uuid types (#790)
- Snowflake DDL import with tags, descriptions, and template variable handling (#790)

## [0.11.6] - 2026-03-17

### Fixed
- Fix parser error for CSV / Parquet table names containing special characters (#1066)
- Fix BigQuery export failing with "Unsupported type" for parameterized physicalType like `NUMERIC(18, 4)` (#1083)

### Added
- Added JSON output format for test results (`--output-format json`)
- Added Azure AD / Entra ID authentication support for SQL Server and Microsoft Fabric

## [0.11.5] - 2026-02-19

### Fixed

- Fix BigQuery import for repeated fields (#1017)
- Make Markdown export compatible with XHTML by replacing `<br>` with `<br />` (#1030)
- Add ADC/WIF and impersonation support for BigQuery (#1064)
- Fix Snowflake quoted identifiers by enabling double-quote quoting (#1053)
- Fix retention duration crash for numeric ODCS values (#1051)
- Fix physicalType bypass for precision and scale conversion (#1043)
- Fix mkdir TOCTOU race causing silent JUnit write failure (#1050)
- Fix validation failure for field names with special chars on Databricks (#1049)
- Add Azure support for field name quoting in schema checks (#1025)

## [0.11.4] - 2026-01-19

### Changed

- Made `duckdb` an optional dependency. Install with `pip install datacontract-cli[duckdb]` for local/S3/GCS/Azure file testing.
- Removed unused `fastparquet` and `numpy` core dependencies.

### Added

- Include searchable tags in catalog index.html

### Fixed

- Fixed example(s) field mapping for Data Contract Specification importer (#992).
- Spark exporter now supports decimal precision/scale via `customProperties` or parsing from `physicalType` (e.g., `decimal(10,2)`) (#996)
- Fix catalog/HTML export failing on ODCS contracts with no schema or no properties (#971)

## [0.11.3] - 2026-01-10

### Fixed

- Fix `datacontract init` to generate ODCS format instead of deprecated Data Contract Specification (#984)
- Fix ODCS lint failing on optional relationship `type` field by updating open-data-contract-standard to v3.1.2 (#971)
- Restrict DuckDB dependency to < 1.4.0 (#972)
- Fixed schema evolution support for optional fields in CSV and Parquet formats. Optional fields marked with `required: false` are no longer incorrectly treated as required during validation, enabling proper schema evolution where optional fields can be added to contracts without breaking validation of historical data files (#977)
- Fixed decimals in pydantic model export. Fields marked with `type: decimal` will be mapped to `decimal.Decimal` instead of `float`.
- Fix BigQuery test failure for fields with FLOAT or BOOLEAN types by mapping them to equivalent types (BOOL and FLOAT64)

## [0.11.2] - 2025-12-15

### Added
- Add Impala engine support for Soda scans via ODCS `impala` server type.
### Fixed
- Restrict DuckDB dependency to < 1.4.0 (#972)

## [0.11.1] - 2025-12-14

This is a major release with breaking changes:
We switched the internal data model from [Data Contract Specification](https://datacontract-specification.com) to [Open Data Contract Standard](https://datacontract.com/#odcs) (ODCS).

Not all features that were available are supported in this version, as some features are not supported by the Open Data Contract Standard, such as:

- Internal definitions using `$ref` (you can refer to external definitions via `authoritativeDefinition`)
- Lineage (no real workaround, use customProperties or transformation object if needed)
- Support for different physical types (no real workaround, use customProperties if needed)
- Support for enums (use quality metric `invalidValues`)
- Support for properties with type map and defining `keys` and `values` (use logical type map)
- Support for `scale` and `precision` (define them in `physicalType`)

The reason for this change is that the Data Contract Specification is deprecated, we focus on best possible support for the Open Data Contract Standard.
We try to make this transition as seamless as possible. 
If you face issues, please open an issue on GitHub.

We continue support reading [Data Contract Specification](https://datacontract-specification.com) data contracts during v0.11.x releases until end of 2026.
To migrate existing data contracts to Open Data Contract Standard use this instruction: https://datacontract-specification.com/#migration

### Changed

- ODCS v3.1.0 is now the default format for all imports.
- Renamed `--model` option to `--schema-name` in the `export` command to align with ODCS terminology.
- Renamed exporter files from `*_converter.py` to `*_exporter.py` for consistency (internal change).

### Added

- If an ODCS slaProperty "freshness" is defined with a reference to the element (column), the CLI will now test freshness of the data.
- If an ODCS slaProperty "retention" is defined with a reference to the element (column), the CLI will now test retention of the data.
- Support for custom Soda quality checks in ODCS using `type: custom` and `engine: soda` with raw SodaCL implementation.

### Fixed

- Oracle: Fix `service_name` attribute access to use ODCS field name `serviceName`

### Removed

- The `breaking`, `changelog`, and `diff` commands are now deleted (#925).
- The `terraform` export format has been removed.


## [0.10.41] - 2025-12-02

### Changed

- Great Expectations export: Update to Great Expectations 1.x format (#919)
  - Changed `expectation_suite_name` to `name` in suite output
  - Changed `expectation_type` to `type` in expectations
  - Removed `data_asset_type` field from suite output
  - **Breaking**: Users with custom quality definitions using `expectation_type` must update to use `type`

### Added

- test: Log server name and type in output (#963)
- api: CORS is now enabled for all origins
- quality: Support `{schema}` and `${schema}` placeholder in SQL quality checks to reference the server's database schema (#957)
- SQL Server: Support `DATACONTRACT_SQLSERVER_DRIVER` environment variable to specify the ODBC driver (#959)
- Excel: Add Oracle server type support for Excel export/import (#960)
- Excel: Add local/CSV server type support for Excel export/import (#961)
- Excel Export: Complete server types (glue, kafka, postgres, s3, snowflake, sqlserver, custom)

### Fixed

- Protobuf import: Fix transitive imports across subdirectories (#943)
- Protobuf export now works without error (#951)
- lint: YAML date values (e.g., `2022-01-15`) are now kept as strings instead of being converted to datetime objects, fixing ODCS schema validation
- export: field annotation now matches to number/numeric/decimal types
- Excel: Server port is now correctly parsed as integer instead of string for all server types
- Excel: Remove invalid `table` and `view` fields from custom server import
- Fixed DuckDB DDL generation to use `JSON` type instead of invalid empty `STRUCT()` for objects without defined properties ([#940](https://github.com/datacontract/datacontract-cli/issues/940))

### Deprecated

- The `breaking`, `changelog`, and `diff` commands are now deprecated and will be removed in a future version (#925)

## [0.10.40] - 2025-11-25

### Added

- Support for ODCS v3.1.0

## [0.10.39] - 2025-11-20

### Added

- Oracle DB: Client Directory for Connection Mode 'Thick' can now be specified in the `DATACONTRACT_ORACLE_CLIENT_DIR` environment variable (#949)

### Fixed

- Import composite primary keys from open data contract spec

## [0.10.38] - 2025-11-11

### Added

- Support for Oracle Database (>= 19C)

### Fixed

- Athena: Now correctly uses the (optional) AWS session token specified in the `DATACONTRACT_S3_SESSION_TOKEN' environment variable when testing contracts (#934)

## [0.10.37] - 2025-11-03

### Added

- import: Support for nested arrays in odcs v3 importer
- lint: ODCS schema is now checked before converting
- --debug flag for all commands

### Fixed

- export: Excel exporter now exports critical data element


## [0.10.36] - 2025-10-17

### Added

- Support for Data Contract Specification v1.2.1 (Data Quality Metrics)
- Support for decimal testing in spark and databricks (#902)
- Support for BigQuery Flexible Schema in Data Contract Checks (#909)

### Changed

- `DataContract().import_from_source()` as an instance method is now deprecated. Use `DataContract.import_from_source()` as a class method instead.

### Fixed

- Export to DQX: Correct DQX format for global-level quality check of data contract export. (#877)
- Import the table tags from a open data contract spec v3 (#895)
- dbt export: Enhanced model-level primaryKey support with automatic test generation for single and multiple column primary keys (#898)
- ODCS: field discarded when no logicalType defined  (#891)
 
### Removed

- Removed specific linters, as the linters did not support ODCS (#913)

## [0.10.35] - 2025-08-25

### Added

- Export to DQX : datacontract export --format dqx (#846)
- API `/test` endpoint now supports `publish_url` parameter to publish test results to a URL. (#853)
- The Spark importer and exporter now also exports the description of columns via the additional metadata of StructFields (#868)

### Fixed

- Improved regex for extracting Azure storage account names from URLs with containerName@storageAccountName format (#848)
- JSON Schema Check: Add globbing support for local JSON files
- Fixed server section rendering for markdown exporter

## [0.10.34] - 2025-08-06

### Added

- `datacontract test` now supports HTTP APIs.
- `datacontract test` now supports Athena.

### Fixed

- Avro Importer: Optional and required enum types are now supported (#804)


## [0.10.33] - 2025-07-29

### Added
- Export to Excel: Convert ODCS YAML to Excel https://github.com/datacontract/open-data-contract-standard-excel-template (#742)
- Extra properties in Markdown export. (#842)


## [0.10.32] - 2025-07-28

### Added
- Import from Excel: Support the new quality sheet

### Fixed
- JUnit Test Report: Fixed incorrect syntax on handling warning test report. (#833)

## [0.10.31] - 2025-07-18

### Added
- Added support for Variant with Spark exporter, data_contract.test(), and import as source unity catalog (#792)


## [0.10.30] - 2025-07-15

### Fixed
- Excel Import should return ODCS YAML (#829)
- Excel Import: Missing server section when the server included a schema property (#823)

### Changed
- Use `&#x2007;` instead of `&numsp;` for tab in Markdown export.

## [0.10.29] - 2025-07-06

### Added
- Support for Data Contract Specification v1.2.0
- `datacontract import --format json`: Import from JSON files

### Changed
- `datacontract api [OPTIONS]`: Added option to pass extra arguments for `uvicorn.run()`

### Fixed
- `pytest tests\test_api.py`: Fixed an issue where special characters were not read correctly from file.
- `datacontract export --format mermaid`: Fixed an issue where the `mermaid` export did not handle references correctly

## [0.10.28] - 2025-06-05

### Added
- Much better ODCS support
    - Import anything to ODCS via the `import --spec odcs` flag
    - Export to HTML with an ODCS native template via `export --format html`
    - Export to Mermaid with an ODCS native mapping via `export --format mermaid`
- The databricks `unity` importer now supports more than a single table. You can use `--unity-table-full-name` multiple times to import multiple tables. And it will automatically add a server with the catalog and schema name.

### Changed
- `datacontract catalog [OPTIONS]`: Added version to contract cards in `index.html` of the catalog (enabled search by version)
- The type mapping of the `unity` importer no uses the native databricks types instead of relying on spark types. This allows for better type mapping and more accurate data contracts.

### Fixed

## [0.10.27] - 2025-05-22

### Added

- `datacontract export --format mermaid` Export
  to [Mermaid](https://mermaid-js.github.io/mermaid/#/) (#767, #725)

### Changed

- `datacontract export --format html`: Adding the mermaid figure to the html export
- `datacontract export --format odcs`: Export physical type to ODCS if the physical type is
  configured in config object
- `datacontract import --format spark`: Added support for spark importer table level comments (#761)
- `datacontract import` respects `--owner` and `--id` flags (#753)

### Fixed

- `datacontract export --format sodacl`: Fix resolving server when using `--server` flag (#768)
- `datacontract export --format dbt`: Fixed DBT export behaviour of constraints to default to data tests when no model type is specified in the datacontract model


## [0.10.26] - 2025-05-16

### Changed
- Databricks: Add support for Variant type (#758)
- `datacontract export --format odcs`: Export physical type if the physical type is configured in
  config object (#757)
- `datacontract export --format sql` Include datacontract descriptions in the Snowflake sql export (
  #756)

## [0.10.25] - 2025-05-07

### Added
- Extracted the DataContractSpecification and the OpenDataContractSpecification in separate pip modules and use them in the CLI.
- `datacontract import --format excel`: Import from Excel
  template https://github.com/datacontract/open-data-contract-standard-excel-template (#742)

## [0.10.24] - 2025-04-19

### Added

- `datacontract test` with DuckDB: Deep nesting of json objects in duckdb (#681)

### Changed

- `datacontract import --format csv` produces more descriptive output. Replaced
  using clevercsv with duckdb for loading and sniffing csv file.
- Updated dependencies

### Fixed

- Fix to handle logicalType format wrt avro mentioned in issue (#687)
- Fix field type from TIME to DATETIME in BigQuery converter and schema (#728)
- Fix encoding issues. (#712)
- ODCS: Fix required in export and added item and fields format (#724)

### Removed

- Deprecated QualityLinter is now removed

## [0.10.23] - 2025-03-03

### Added

- `datacontract test --output-format junit --output TEST-datacontract.xml` Export CLI test results
  to a file, in a standard format (e.g. JUnit) to improve CI/CD experience (#650)

- Added import for `ProtoBuf`
Code for proto to datacontract (#696)


- `dbt` & `dbt-sources` export formats now support the optional `--server` flag to adapt the DBT column `data_type` to specific SQL dialects
- Duckdb Connections are now configurable, when used as Python library (#666)
- export to avro format add map type

### Changed

- Changed Docker base image to python:3.11-bullseye
- Relax fastparquet dependency

### Fixed

- Unicode Encode Error when exporting data contract YAML to HTML
  (#652)
- Fix multiline descriptions in the DBT export functionality
- Incorrectly parsing $ref values in definitions (#664)
- Better error message when the server configuration is missing in a data contract (#670)
- Improved default values in ODCS generator to avoid breaking schema validation (#671)
- Updated ODCS v3 generator to drop the "is" prefix from fields like `isNullable` and `isUnique` (#669)
- Fix issue when testing databricks server with ODCS format
- avro export fix float format

## [0.10.22] - 2025-02-20

### Added

- `datacontract test` now also executes tests for service levels freshness and retention (#407)

### Changed

- `datacontract import --format sql` is now using SqlGlot as importer.
- `datacontract import --format sql --dialect <dialect>` Dialect can now to defined when importing
  SQL.

### Fixed

- Schema type checks fail on nested fields for Databricks spark (#618)
- Export to Avro add namespace on field as optional configuration (#631)

### Removed

- `datacontract test --examples`: This option was removed as it was not very popular and top-level
  examples section is deprecated in the Data Contract Specification v1.1.0 (#628)
- Support for `odcs_v2` (#645)

## [0.10.21] - 2025-02-06

### Added

- `datacontract export --format custom`: Export to custom format with Jinja
- `datacontract api` now can be protected with an API key

### Changed

- `datacontract serve` renamed to `datacontract api`

### Fixed

- Fix Error: 'dict object' has no attribute 'model_extra' when trying to use type: string with enum
  values inside an array (#619)

## [0.10.20] - 2025-01-30

### Added

- datacontract serve: now has a route for testing data contracts
- datacontract serve: now has a OpenAPI documentation on root

### Changed

- FastAPI endpoint is now moved to extra "web"

### Fixed

- API Keys for Data Mesh Manager are now also applied for on-premise installations

## [0.10.19] - 2025-01-29

### Added

- datacontract import --format csv
- publish command also supports publishing ODCS format
- Option to separate physical table name for a model via config option (#270)

### Changed
- JSON Schemas are now bundled with the application (#598)
- datacontract export --format html: The model title is now shown if it is different to the model
  name (#585)
- datacontract export --format html: Custom model attributes are now shown (#585)
- datacontract export --format html: The composite primary key is now shown. (#591)
- datacontract export --format html: now examples are rendered in the model and definition (#497)
- datacontract export --format sql: Create arrays and struct for Databricks (#467)

### Fixed
- datacontract lint: Linter 'Field references existing field' too many values to unpack (expected
  2) (#586)
- datacontract test (Azure): Error querying delta tables from azure storage. (#458)
- datacontract export --format data-caterer: Use `fields` instead of `schema`
- datacontract export --format data-caterer: Use `options` instead of `generator.options`
- datacontract export --format data-caterer: Capture array type length option and inner data type
- Fixed schemas/datacontract-1.1.0.init.yaml not included in build and `--template` not resolving file

## [0.10.18] - 2025-01-18

### Fixed
- Fixed an issue when resolving project's dependencies when all extras are installed.
- Definitions referenced by nested fields are not validated correctly (#595)
- Replaced deprecated `primary` field with `primaryKey` in exporters, importers, examples, and Jinja templates for backward compatibility. Fixes [#518](https://github.com/your-repo/your-project/issues/518).
- Cannot execute test on column of type record(bigquery) #597

## [0.10.17] - 2025-01-16

### Added
- added export format **markdown**: `datacontract export --format markdown` (#545)
- When importing in dbt format, add the dbt unique information as a datacontract unique field (#558)
- When importing in dbt format, add the dbt primary key information as a datacontract primaryKey field (#562)
- When exporting in dbt format, add the datacontract references field as a dbt relationships test (#569)
- When importing in dbt format, add the dbt relationships test field as a reference in the data contract (#570)
- Add serve command on README (#592)

### Changed
- Primary and example fields have been deprecated in Data Contract Specification v1.1.0 (#561)
- Define primaryKey and examples for model to follow the changes in datacontract-specification v1.1.0 (#559)

### Fixed
- SQL Server: cannot escape reserved word on model (#557)
- Export dbt-staging-sql error on multi models contracts (#587)

### Removed
- OpenTelemetry publisher, as it was hardly used

## [0.10.16] - 2024-12-19

### Added
- Support for exporting a Data Contract to an Iceberg schema definition.
- When importing in dbt format, add the dbt `not_null` information as a datacontract `required` field (#547)

### Changed
- Type conversion when importing contracts into dbt and exporting contracts from dbt (#534)
- Ensure 'name' is the first column when exporting in dbt format, considering column attributes (#541)
- Rename dbt's `tests` to `data_tests` (#548)

### Fixed
- Modify the arguments to narrow down the import target with `--dbt-model` (#532)
- SodaCL: Prevent `KeyError: 'fail'` from happening when testing with SodaCL
- fix: populate database and schema values for bigquery in exported dbt sources (#543)
- Fixing the options for importing and exporting to standard output (#544)
- Fixing the data quality name for model-level and field-level quality tests

## [0.10.15] - 2024-12-02

### Added
- Support for model import from parquet file metadata.
- Great Expectation export: add optional args (#496)
  - `suite_name` the name of the expectation suite to export
  - `engine` used to run checks
  - `sql_server_type` to define the type of SQL Server to use when engine is `sql`
- Changelog support for `Info` and `Terms` blocks.
- `datacontract import` now has `--output` option for saving Data Contract to file
- Enhance JSON file validation (local and S3) to return the first error for each JSON object, the max number of total errors can be configured via the environment variable: `DATACONTRACT_MAX_ERRORS`. Furthermore, the primaryKey will be additionally added to the error message.
- fixes issue where records with no fields create an invalid bq schema.

### Changed
- Changelog support for custom extension keys in `Models` and `Fields` blocks.
- `datacontract catalog --files '*.yaml'` now checks also any subfolders for such files.
- Optimize test output table on console if tests fail

### Fixed
- raise valid exception in DataContractSpecification.from_file if file does not exist
- Fix importing JSON Schemas containing deeply nested objects without `required` array
- SodaCL: Only add data quality tests for executable queries

## [0.10.14] - 2024-10-26

Data Contract CLI now supports the Open Data Contract Standard (ODCS) v3.0.0.

### Added
- `datacontract test` now also supports ODCS v3 data contract format
- `datacontract export --format odcs_v3`: Export to Open Data Contract Standard v3.0.0 (#460)
- `datacontract test` now also supports ODCS v3 anda Data Contract SQL quality checks on field and model level
- Support for import from Iceberg table definitions.
- Support for decimal logical type on avro export.
- Support for custom Trino types

### Changed
- `datacontract import --format odcs`: Now supports ODSC v3.0.0 files (#474)
- `datacontract export --format odcs`: Now creates v3.0.0 Open Data Contract Standard files (alias to odcs_v3). Old versions are still available as format `odcs_v2`. (#460)

### Fixed
- fix timestamp serialization from parquet -> duckdb (#472)


## [0.10.13] - 2024-09-20

### Added
- `datacontract export --format data-caterer`: Export to [Data Caterer YAML](https://data.catering/setup/guide/scenario/data-generation/)

### Changed
- `datacontract export --format jsonschema` handle optional and nullable fields (#409)
- `datacontract import --format unity` handle nested and complex fields (#420)
- `datacontract import --format spark` handle field descriptions (#420)
- `datacontract export --format bigquery` handle bigqueryType (#422)

### Fixed
- use correct float type with bigquery (#417)
- Support DATACONTRACT_MANAGER_API_KEY
- Some minor bug fixes

## [0.10.12] - 2024-09-08

### Added
- Support for import of DBML Models (#379)
- `datacontract export --format sqlalchemy`: Export to [SQLAlchemy ORM models](https://docs.sqlalchemy.org/en/20/orm/quickstart.html) (#399)
- Support of varchar max length in Glue import (#351)
- `datacontract publish` now also accepts the `DATACONTRACT_MANAGER_API_KEY` as an environment variable
- Support required fields for Avro schema export (#390)
- Support data type map in Spark import and export (#408)
- Support of enum on export to avro
- Support of enum title on avro import

### Changed
- Deltalake is now using DuckDB's native deltalake support (#258). Extra deltalake removed.
- When dumping to YAML (import) the alias name is used instead of the pythonic name. (#373)

### Fixed
- Fix an issue where the datacontract cli fails if installed without any extras (#400)
- Fix an issue where Glue database without a location creates invalid data contract (#351)
- Fix bigint -> long data type mapping (#351)
- Fix an issue where column description for Glue partition key column is ignored (#351)
- Corrected name of table parameter for bigquery import (#377)
- Fix a failed to connect to S3 Server (#384)
- Fix a model bug mismatching with the specification (`definitions.fields`) (#375)
- Fix array type management in Spark import (#408)


## [0.10.11] - 2024-08-08

### Added

- Support data type map in Glue import. (#340)
- Basic html export for new `keys` and `values` fields
- Support for recognition of 1 to 1 relationships when exporting to DBML
- Added support for arrays in JSON schema import (#305)

### Changed

- Aligned JSON schema import and export of required properties
- Change dbt importer to be more robust and customizable

### Fixed

- Fix required field handling in JSON schema import
- Fix an issue where the quality and definition `$ref` are not always resolved
- Fix an issue where the JSON schema validation fails for a field with type `string` and format `uuid`
- Fix an issue where common DBML renderers may not be able to parse parts of an exported file


## [0.10.10] - 2024-07-18

### Added
- Add support for dbt manifest file (#104)
- Fix import of pyspark for type-checking when pyspark isn't required as a module (#312)
- Adds support for referencing fields within a definition (#322)
- Add `map` and `enum` type for Avro schema import (#311)

### Fixed
- Fix import of pyspark for type-checking when pyspark isn't required as a module (#312)- `datacontract import --format spark`: Import from Spark tables (#326)
- Fix an issue where specifying `glue_table` as parameter did not filter the tables and instead returned all tables from `source` database (#333)

## [0.10.9] - 2024-07-03

### Added
- Add support for Trino (#278)
- Spark export: add Spark StructType exporter (#277)
- add `--schema` option for the `catalog` and `export` command to provide the schema also locally
- Integrate support into the pre-commit workflow. For further details, please refer to the information provided [here](./README.md#use-with-pre-commit).
- Improved HTML export, supporting links, tags, and more
- Add support for AWS SESSION_TOKEN (#309)

### Changed
- Added array management on HTML export (#299)

### Fixed
- Fix `datacontract import --format jsonschema` when description is missing (#300)
- Fix `datacontract test` with case-sensitive Postgres table names (#310)

## [0.10.8] - 2024-06-19

### Added
- `datacontract serve` start a local web server to provide a REST-API for the commands
- Provide server for sql export for the appropriate schema (#153)
- Add struct and array management to Glue export (#271)

### Changed
- Introduced optional dependencies/extras for significantly faster installation times. (#213)
- Added delta-lake as an additional optional dependency
- support `GOOGLE_APPLICATION_CREDENTIALS` as variable for connecting to bigquery in `datacontract test`
- better support bigqueries `type` attribute, don't assume all imported models are tables
- added initial implementation of an importer from unity catalog (not all data types supported, yet)
- added the importer factory. This refactoring aims to make it easier to create new importers and consequently the growth and maintainability of the project. (#273)

### Fixed
- `datacontract export --format avro` fixed array structure (#243)

## [0.10.7] - 2024-05-31

### Added
- Test data contract against dataframes / temporary views (#175)

### Fixed
- AVRO export: Logical Types should be nested (#233)

## [0.10.6] - 2024-05-29

### Fixed

- Fixed Docker build by removing msodbcsql18 dependency (temporary workaround)

## [0.10.5] - 2024-05-29

### Added
- Added support for `sqlserver` (#196)
- `datacontract export --format dbml`: Export to [Database Markup Language (DBML)](https://dbml.dbdiagram.io/home/) (#135)
- `datacontract export --format avro`: Now supports config map on field level for logicalTypes and default values [Custom Avro Properties](./README.md#custom-avro-properties)
- `datacontract import --format avro`: Now supports importing logicalType and default definition on avro files [Custom Avro Properties](./README.md#custom-avro-properties)
- Support `config.bigqueryType` for testing BigQuery types
- Added support for selecting specific tables in an AWS Glue `import` through the `glue-table` parameter (#122)

### Fixed

- Fixed jsonschema export for models with empty object-typed fields (#218)
- Fixed testing BigQuery tables with BOOL fields
- `datacontract catalog` Show search bar also on mobile

## [0.10.4] - 2024-05-17

### Added

- `datacontract catalog` Search
- `datacontract publish`: Publish the data contract to the Data Mesh Manager
- `datacontract import --format bigquery`: Import from BigQuery format (#110)
- `datacontract export --format bigquery`: Export to BigQuery format (#111)
- `datacontract export --format avro`: Now supports [Avro logical types](https://avro.apache.org/docs/1.11.1/specification/#logical-types) to better model date types. `date`, `timestamp`/`timestamp-tz` and `timestamp-ntz` are now mapped to the appropriate logical types. (#141)
- `datacontract import --format jsonschema`: Import from JSON schema (#91)
- `datacontract export --format jsonschema`: Improved export by exporting more additional information
- `datacontract export --format html`: Added support for Service Levels, Definitions, Examples and nested Fields
- `datacontract export --format go`: Export to go types format

## [0.10.3] - 2024-05-05

### Fixed
- datacontract catalog: Add index.html to manifest

## [0.10.2] - 2024-05-05

### Added

- Added import glue (#166)
- Added test support for `azure` (#146)
- Added support for `delta` tables on S3 (#24)
- Added new command `datacontract catalog` that generates a data contract catalog with an `index.html` file.
- Added field format information to HTML export

### Fixed
- RDF Export: Fix error if owner is not a URI/URN


## [0.10.1] - 2024-04-19

### Fixed

- Fixed docker columns

## [0.10.0] - 2024-04-19

### Added

- Added timestamp when ah HTML export was created

### Fixed

- Fixed export format **html**

## [0.9.9] - 2024-04-18

### Added

- Added export format **html** (#15)
- Added descriptions as comments to `datacontract export --format sql` for Databricks dialects
- Added import of arrays in Avro import

## [0.9.8] - 2024-04-01

### Added

- Added export format **great-expectations**: `datacontract export --format great-expectations`
- Added gRPC support to OpenTelemetry integration for publishing test results
- Added AVRO import support for namespace (#121)
- Added handling for optional fields in avro import (#112)
- Added Databricks SQL dialect for `datacontract export --format sql`

### Fixed

- Use `sql_type_converter` to build checks.
- Fixed AVRO import when doc is missing (#121)

## [0.9.7] - 2024-03-15

### Added

- Added option publish test results to **OpenTelemetry**: `datacontract test --publish-to-opentelemetry`
- Added export format **protobuf**: `datacontract export --format protobuf`
- Added export format **terraform**: `datacontract export --format terraform` (limitation: only works for AWS S3 right now)
- Added export format **sql**: `datacontract export --format sql`
- Added export format **sql-query**: `datacontract export --format sql-query`
- Added export format **avro-idl**: `datacontract export --format avro-idl`: Generates an Avro IDL file containing records for each model.
- Added new command **changelog**: `datacontract changelog datacontract1.yaml datacontract2.yaml` will now generate a changelog based on the changes in the data contract. This will be useful for keeping track of changes in the data contract over time.
- Added extensive linting on data contracts. `datacontract lint` will now check for a variety of possible errors in the data contract, such as missing descriptions, incorrect references to models or fields, nonsensical constraints, and more.
- Added importer for avro schemas. `datacontract import --format avro` will now import avro schemas into a data contract.

### Fixed

- Fixed a bug where the export to YAML always escaped the unicode characters.


## [0.9.6-2] - 2024-03-04

### Added

- test kafka for avro messages
- added export format **avro**: `datacontract export --format avro`

## [0.9.6] - 2024-03-04

This is a huge step forward, we now support testing Kafka messages.
We start with JSON messages and avro, and Protobuf will follow.

### Added
- test kafka for JSON messages
- added import format **sql**: `datacontract import --format sql` (#51)
- added export format **dbt-sources**: `datacontract export --format dbt-sources`
- added export format **dbt-staging-sql**: `datacontract export --format dbt-staging-sql`
- added export format **rdf**: `datacontract export --format rdf` (#52)
- added command `datacontract breaking` to detect breaking changes in between two data contracts.

## [0.9.5] - 2024-02-22

### Added
- export to dbt models (#37).
- export to ODCS (#49).
- test - show a test summary table.
- lint - Support local schema (#46).

## [0.9.4] - 2024-02-18

### Added
- Support for Postgres
- Support for Databricks

## [0.9.3] - 2024-02-10

### Added
- Support for BigQuery data connection
- Support for multiple models with S3

### Fixed

- Fix Docker images. Disable builds for linux/amd64.

## [0.9.2] - 2024-01-31

### Added
- Publish to Docker Hub

## [0.9.0] - 2024-01-26 - BREAKING

This is a breaking change (we are still on a 0.x.x version).
The project migrated from Golang to Python.
The Golang version can be found at [cli-go](https://github.com/datacontract/cli-go)

### Added
- `test` Support to directly run tests and connect to data sources defined in servers section.
- `test` generated schema tests from the model definition.
- `test --publish URL` Publish test results to a server URL.
- `export` now exports the data contract so format jsonschema and sodacl.

### Changed
- The `--file` option removed in favor of a direct argument.: Use `datacontract test datacontract.yaml` instead of `datacontract test --file datacontract.yaml`.

### Removed
- `model` is now part of `export`
- `quality` is now part of `export`
- Temporary Removed: `diff` needs to be migrated to Python.
- Temporary Removed: `breaking` needs to be migrated to Python.
- Temporary Removed: `inline` needs to be migrated to Python.

## [0.6.0]
### Added
- Support local json schema in lint command.
- Update to specification 0.9.2.

## [0.5.3]
### Fixed
- Fix format flag bug in model (print) command.

## [0.5.2]
### Changed
- Log to STDOUT.
- Rename `model` command parameter, `type` -> `format`.

## [0.5.1]
### Removed
- Remove `schema` command.

### Fixed
- Fix documentation.
- Security update of x/sys.

## [0.5.0]
### Added
- Adapt Data Contract Specification in version 0.9.2.
- Use `models` section for `diff`/`breaking`.
- Add `model` command.
- Let `inline` print to STDOUT instead of overwriting datacontract file.
- Let `quality` write input from STDIN if present.

## [0.4.0]
### Added
- Basic implementation of `test` command for Soda Core.

### Changed
- Change package structure to allow usage as library.

## [0.3.2]
### Fixed
- Fix field parsing for dbt models, affects stability of `diff`/`breaking`.

## [0.3.1]
### Fixed
- Fix comparing order of contracts in `diff`/`breaking`.

## [0.3.0]
### Added
- Handle non-existent schema specification when using `diff`/`breaking`.
- Resolve local and remote resources such as schema specifications when using "$ref: ..." notation.
- Implement `schema` command: prints your schema.
- Implement `quality` command: prints your quality definitions.
- Implement the `inline` command: resolves all references using the "$ref: ..." notation and writes them to your data contract.

### Changed
- Allow remote and local location for all data contract inputs (`--file`, `--with`).

## [0.2.0]
### Added
- Add `diff` command for dbt schema specification.
- Add `breaking` command for dbt schema specification.

### Changed
- Suggest a fix during `init` when the file already exists.
- Rename `validate` command to `lint`.

### Removed
- Remove `check-compatibility` command.

### Fixed
- Improve usage documentation.

## [0.1.1]
### Added
- Initial release.
