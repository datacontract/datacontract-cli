# Data Contract CLI

<p>
  <a href="https://github.com/datacontract/cli/actions/workflows/ci.yaml?query=branch%3Amain">
    <img alt="Test Workflow" src="https://img.shields.io/github/actions/workflow/status/datacontract/cli/ci.yaml?branch=main"></a>
  <a href="https://img.shields.io/github/stars/datacontract/cli">
    <img alt="Stars" src="https://img.shields.io/github/stars/datacontract/cli" /></a>
</p>

The `datacontract` CLI is an open source command-line tool for working with [Data Contracts](https://datacontract.com/).
It uses data contract YAML files to lint the data contract, connect to data sources and execute schema and quality tests, detect breaking changes, and export to different formats. The tool is written in Python. It can be used as a standalone CLI tool, in a CI/CD pipeline, or directly as a Python library.

> **_NOTE:_**  This project has been migrated from Go to Python which adds the possibility to use `datacontract` within Python code as library, but it comes with some [breaking changes](CHANGELOG.md). The Go version has been [forked](https://github.com/datacontract/cli-go), if you still rely on that.


## Getting started

Let's use [pip](https://pip.pypa.io/en/stable/getting-started/) to install the CLI.  
```bash
$ pip install datacontract-cli
```

Now, let's look at this data contract: https://raw.githubusercontent.com/datacontract/datacontract-specification/main/examples/covid-cases/datacontract.yaml

We have a _servers_ section with endpoint details to the (public) S3 bucket, a _model_ for the structure of the data, and _quality_ attributes that describe the expected freshness and number of rows.

This data contract contains all data to connect to S3 and check if the actual data meets the defined schema and quality requirements.

We run the tests:

```bash
$ datacontract test https://raw.githubusercontent.com/datacontract/datacontract-specification/main/examples/covid-cases/datacontract.yaml
# returns: 🟢 data contract is valid. Run 12 checks.
```

Voilà, the CLI tested, that the _datacontract.yaml_ itself is valid, all records comply with the schema, and all quality attributes are met.

## Usage

```bash
# create a new data contract from example and write it to datacontract.yaml
$ datacontract init datacontract.yaml

# lint the datacontract.yaml
$ datacontract lint datacontract.yaml

# execute schema and quality checks
$ datacontract test datacontract.yaml

# find differences between to data contracts (Coming Soon)
$ datacontract diff datacontract-v1.yaml datacontract-v2.yaml

# fail pipeline on breaking changes  (Coming Soon)
$ datacontract breaking datacontract-v1.yaml datacontract-v2.yaml

# export model as jsonschema
$ datacontract export --format jsonschema datacontract.yaml

# export model as dbt  (Coming Soon)
$ datacontract export --format dbt datacontract.yaml

# import protobuf as model (Coming Soon)
$ datacontract import --format protobuf --source my_protobuf_file.proto datacontract.yaml
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

If you use [Data Mesh Manager](https://datamesh-manager.com/), you can use the data contract URL and append the `--publish` option to send and display the test results. Set an environment variable for your API key.

```bash
# Fetch current data contract, execute tests on production, and publish result to data mesh manager
$ EXPORT DATAMESH_MANAGER_API_KEY=xxx
$ datacontract test https://demo.datamesh-manager.com/demo279750347121/datacontracts/4df9d6ee-e55d-4088-9598-b635b2fdcbbc/datacontract.yaml --server production --publish
```





## Installation

Choose the most appropriate installation method for your needs:

### pip
Python 3.11 recommended.

```bash
pip install datacontract-cli
```

### pipx
pipx installs into an isolated environment.
```bash
pipx install datacontract-cli
```

### Homebrew (coming soon)

```bash
brew install datacontract/brew/datacontract
```

### Docker (coming soon)

```bash
docker pull datacontract/cli
docker run --rm -v ${PWD}:/datacontract datacontract/cli
```

## Documentation

### Tests

Data Contract CLI can connect to data sources and run schema and quality tests to verify that the data contract is valid.

```bash 
$ datacontract test --server production datacontract.yaml
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
docker build -t datacontract/cli .
docker run --rm -v ${PWD}:/datacontract datacontract/cli
```

## Contribution

We are happy to receive your contributions. Propose your change in an issue or directly create a pull request with your improvements.

## License

[MIT License](LICENSE)

## Credits

Created by [Stefan Negele](https://www.linkedin.com/in/stefan-negele-573153112/) and [Jochen Christ](https://www.linkedin.com/in/jochenchrist/).
