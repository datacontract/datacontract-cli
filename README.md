# Data Contract CLI

<p>
  <a href="https://github.com/datacontract/cli/actions/workflows/ci.yaml?query=branch%3Amain">
    <img alt="Test Workflow" src="https://img.shields.io/github/actions/workflow/status/datacontract/cli/ci.yaml?branch=main"></a>
  <a href="https://img.shields.io/github/stars/datacontract/cli">
    <img alt="Stars" src="https://img.shields.io/github/stars/datacontract/cli" /></a>
</p>

The `datacontract` CLI lets you work with your `datacontract.yaml` files locally, and in your CI pipeline. It uses the [Data Contract Specification](https://datacontract.com/) to validate the contract, connect to your data sources and execute tests. The CLI is open source and written in Python. It can be used as a CLI tool or directly as a Python library.

> **_NOTE:_**  This project has been migrated grom Go to Python which adds the possibility to use `datacontract` withing Python code as library, but it comes with some [breaking changes](CHANGELOG.md). The Golang version has been [forked](https://github.com/datacontract/cli-go), if you rely on that.


## Usage

`datacontract` usually works with a `datacontract.yaml` file in your current working directory. You can specify a different file or URL as an additional argument.

```bash
# create a new data contract
$ datacontract init

# execute schema and quality checks
$ datacontract test
```

## Advanced Usage
```bash
# lint the data contract
$ datacontract lint datacontract.yaml

# find differences between to data contracts (Coming Soon)
$ datacontract diff datacontract-v1.yaml datacontract-v2.yaml

# fail pipeline on breaking changes  (Coming Soon)
$ datacontract breaking datacontract-v1.yaml datacontract-v2.yaml

# export model as jsonschema
$ datacontract export --format jsonschema

# export model as dbt  (Coming Soon)
$ datacontract export --format dbt

# import protobuf as model (Coming Soon)
$ datacontract import --format protobuf --source my_protobuf_file.proto
```

## Programmatic (Python)
```python
from datacontract.data_contract import DataContract

data_contract = DataContract(data_contract_file="datacontract.yaml")
run = data_contract.test()
if not run.has_passed():
    print("Data quality validation failed.")
    # Abort pipeline, alert, or take corrective actions...
```

## Scenario: Integration with Data Mesh Manager
```bash
# Fetch current data contract, execute tests on production, and publish result to data mesh manager
$ EXPORT DATAMESH_MANAGER_API_KEY=xxx
$ datacontract test https://demo.datamesh-manager.com/demo279750347121/datacontracts/4df9d6ee-e55d-4088-9598-b635b2fdcbbc/datacontract.yaml --server production --publish
```

## Scenario: CI/CD testing for breaking changes
```bash
# fail pipeline on breaking changes in the data contract yaml (coming soon)
$ datacontract breaking datacontract.yaml https://raw.githubusercontent.com/datacontract/cli/main/examples/my-data-contract-id_v0.0.1.yaml
```


## Installation

### Pip
```bash
pip install datacontract-cli
```


[//]: # (### Homebrew)

[//]: # (```bash)

[//]: # (brew install datacontract/brew/datacontract)

[//]: # (```)

## Documentation

### Tests

Data Contract CLI can connect to data sources and run schema and quality tests to verify that the data contract is valid.

```
datacontract test
```

To connect to the databases the `server` block in the datacontract.yaml is used to set up the connection. In addition, credentials, such as username and passwords, may be defined with environment variables.

The application uses different engines, based on the server `type`.

| Type         | Format     | Description                                                               | Status      | Engines                             |
|--------------|------------|---------------------------------------------------------------------------|-------------|-------------------------------------|
| `s3`         | `parquet`  | Works for any S3-compliant endpoint., e.g., AWS S3, GCS, MinIO, Ceph, ... | ✅           | soda-core-duckdb                    |
| `s3`         | `json`     | Support for `new_line` delimited JSON files and one JSON record per file. | ✅           | fastjsonschema<br> soda-core-duckdb |
| `s3`         | `csv`      |                                                                           | ✅           | soda-core-duckdb                    |
| `s3`         | `delta`    |                                                                           | Coming soon | TBD                                 |
| `postgres`   | n/a        |                                                                           | Coming soon | TBD                                 |
| `snowflake`  | n/a        |                                                                           | ✅ | soda-core-snowflake                 |
| `bigquery`   | n/a        |                                                                           | Coming soon | TBD                                 |
| `redshift`   | n/a        |                                                                           | Coming soon | TBD                                 |
| `databricks` | n/a        |                                                                           | Coming soon | TBD                                 |
| `kafka`      | `json`     |                                                                           | Coming soon | TBD                                 |
| `kafka`      | `avro`     |                                                                           | Coming soon | TBD                                 |
| `kafka`      | `protobuf` |                                                                           | Coming soon | TBD                                 |
| `local`      | `parquet`  |                                                                           | ✅           | soda-core-duckdb                    |
| `local`      | `json`     | Support for `new_line` delimited JSON files and one JSON record per file. | ✅           | fastjsonschema<br> soda-core-duckdb |
| `local`      | `csv`      |                                                                           | ✅           | soda-core-duckdb                    |

Feel free to create an issue, if you need support for an additional type.

### Server Type S3

Example:

datacontract.yaml
```
servers:
  production:
    type: s3
    endpointUrl: https://minio.example.com # not needed with AWS S3
    location: s3://bucket-name/path/*/*.json
    delimiter: new_line # new_line, array, or none
    format: json
```

Environment variables
```
export DATACONTRACT_S3_REGION=eu-central-1
export DATACONTRACT_S3_ACCESS_KEY_ID=AKIAXV5Q5QABCDEFGH
export DATACONTRACT_S3_SECRET_ACCESS_KEY=93S7LRrJcqLkdb2/XXXXXXXXXXXXX
```


## Development Setup

Python base interpreter should be 3.11.x

```bash
# create venv
python3 -m venv venv
source venv/bin/activate

# Install Requirements
pip install --upgrade pip setuptools wheel
pip install -e '.[dev]'
cd tests/
pytest
```

Release

```
git tag v0.9.0
git push origin v0.9.0
python3 -m pip install --upgrade build twine
rm -r dist/
python3 -m build
# for now only test.pypi.org
python3 -m twine upload --repository testpypi dist/*
```

Docker Build

```
docker build -t datacontract .
docker run --rm -v ${PWD}:/app datacontract
```

## Contribution

We are happy to receive your contributions. Propose your change in an issue or directly create a pull request with your improvements.

## License

[MIT License](LICENSE)

## Credits

Created by [Stefan Negele](https://www.linkedin.com/in/stefan-negele-573153112/) and [Jochen Christ](https://www.linkedin.com/in/jochenchrist/).
