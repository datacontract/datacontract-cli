# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## Unreleased

### Added

### Fixed

- Fix `datacontract init` to generate ODCS format instead of deprecated Data Contract Specification (#984)
- Fix ODCS lint failing on optional relationship `type` field by updating open-data-contract-standard to v3.1.2 (#971)
- Restrict DuckDB dependency to < 1.4.0 (#972)
- Fixed schema evolution support for optional fields in CSV and Parquet formats. Optional fields marked with `required: false` are no longer incorrectly treated as required during validation, enabling proper schema evolution where optional fields can be added to contracts without breaking validation of historical data files (#977)
- Fixed decimals in pydantic model export. Fields marked with `type: decimal` will be mapped to `decimal.Decimal` instead of `float`.

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
