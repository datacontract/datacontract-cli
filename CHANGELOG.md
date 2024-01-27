# 0.9.0 BREAKING

BREAKING: Project migrated from Golang to Python.
The Golang version can be found at https://github.com/datacontract/cli-go

- Added: `test` Support to directly run tests and connect to data sources defined in servers section.
- Added: `test` generated schema tests from the model definition
- Added: `test --publish URL` Publish test results to a server URL
- Added: `export` now exports the data contract so format jsonschema and sodacl
- Changed: The `--file` option in favor of a direct argument. Use `datacontract test datacontract.yaml` instead of `datacontract test --file datacontract.yaml`
- Temporary Removed: `diff` is still in development and coming soon
- Temporary Removed: `breaking` is still in development and coming soon
- Temporary Removed: `inline` is still in development and coming soon

# 0.6.0
- Support local json schema in lint command
- Update to specification 0.9.2

# 0.5.3
- Fix format flag bug in model (print) command

# 0.5.2
- Log to STDOUT
- Rename `model` command parameter, `type` -> `format`

# 0.5.1
- Remove `schema` command
- Fix documentation
- Security update of x/sys

# 0.5.0
- Adapt Data Contract Specification in version 0.9.2
- Use `models` section for `diff`/`breaking`
- Add `model` command
- Let `inline` print to STDOUT instead of overwriting datacontract file
- Let `quality` write input from STDIN if present 

# 0.4.0
- Basic implementation of `test` command for Soda Core
- change package structure to allow usage as library

# 0.3.2
- Fix field parsing for dbt models, affects stability of `diff`/`breaking`

# 0.3.1
- Fix comparing order of contracts in `diff`/`breaking`

# 0.3.0
- Handle non-existent schema specification when using `diff`/`breaking`
- Resolve local and remote resources such as schema specifications when using "$ref: ..." notation
- Implement `schema` command: prints your schema
- Implement `quality` command: prints your quality definitions 
- Implement the `inline' command: resolves all references using the "$ref: ..." notation and writes them to your data contract.
- Allow remote and local location for all data contract inputs (`--file`, `--with`)

# 0.2.0

- Suggest a fix during `init` when the file already exists
- Rename `validate` command to `lint`
- Add `diff` command for dbt schema specification
- Add `breaking` command for dbt schema specification
- Remove `check-compatibility` command
- Improve usage documentation

# 0.1.1

Initial release
