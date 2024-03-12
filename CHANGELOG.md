# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

- Fixed a bug where the export to YAML always escaped the unicode characters.
- Added export format **protobuf**: `datacontract export --format protobuf`
- Added export format **terraform**: `datacontract export --format terraform`
- Added extensive linting on data contracts. `datacontract lint` will now check for a variety of possible errors in the data contract, such as missing descriptions, incorrect references to models or fields, nonsensical constraints, and more.

## [0.9.6-2] - 2024-03-04

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
