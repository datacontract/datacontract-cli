# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Development Environment Setup

```bash
# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install Requirements 
pip install --upgrade pip setuptools wheel
pip install -e '.[dev]'

# Setup pre-commit hooks
pre-commit install
```

Alternatively, using uv (recommended):

```bash
# Pin Python version
uv python pin 3.11
uv pip install -e '.[dev]'
```

### Java (required for PySpark tests)

Tests that use PySpark (e.g., `test_test_kafka.py`, `test_test_delta.py`, `test_test_dataframe.py`, `test_import_spark.py`) require Java 21. Set `JAVA_HOME` to a Java 21 installation before running these tests.

```bash
# Using SDKMAN
source ~/.sdkman/bin/sdkman-init.sh
sdk use java 21-open

# Or set JAVA_HOME directly
export JAVA_HOME=$(/usr/libexec/java_home -v 21)
```

## Common Commands

### Testing

```bash
# Run all tests
pytest

# Run tests in parallel
pytest -n 8

# Run a specific test file
pytest tests/test_specific.py

# Run a specific test function
pytest tests/test_specific.py::test_function_name
```

### Linting and Formatting

```bash
# Check code with ruff
ruff check .

# Fix linting issues automatically
ruff check --fix .

# Format code
ruff format .

# Run all pre-commit hooks
pre-commit run --all-files
```

### CLI Usage

```bash
# Initialize a new data contract
datacontract init

# Lint a data contract file
datacontract lint datacontract.yaml

# Test a data contract against actual data
datacontract test datacontract.yaml

# Export a data contract to a different format
datacontract export --format html datacontract.yaml --output datacontract.html

# Import from a different format
datacontract import --format sql --source my-ddl.sql --dialect postgres --output datacontract.yaml

# Find differences between data contracts
datacontract diff datacontract-v1.yaml datacontract-v2.yaml

```

## Project Architecture

The Data Contract CLI is an open-source command-line tool for working with data contracts:

### Core Components

1. **CLI Interface (`datacontract/cli.py`)**: Entry point for the command-line interface using Typer.

2. **Data Contract Core (`datacontract/data_contract.py`)**: Central class for working with data contracts, handling operations like testing, validation, and export/import.

3. **Engines**: Modules for connecting to different data stores and executing tests:
   - `datacontract/engines/`: Contains implementations for testing against various data sources
   - Supports multiple backend types: S3, BigQuery, Postgres, Snowflake, Kafka, etc.

4. **Export/Import**: Modules for converting data contracts to/from different formats:
   - `datacontract/export/`: Converters for formats like Avro, SQL, dbt, HTML, etc.
   - `datacontract/imports/`: Importers from formats like SQL, Avro, JSON Schema, etc.

5. **Linting (`datacontract/lint/`)**: Tools for validating data contract files against schema and best practices.

6. **Semantic Diff (`datacontract/reports/diff/`)**: Semantic diff engine with HTML and text report renderers.

   **Normalization — planned improvement**: The natural keys used to match list items (e.g. `schema[].name`, `customProperties[].property`) are currently hardcoded in `diff.py` as a 20-line path-to-key table, backed by six helper methods (`_normalize_by`, `_normalize_schema_fields`, `_normalize_quality`, `_normalize_auth_defs`, `_normalize_relationships`, `_normalize_properties`). The intended long-term fix is to encode these natural keys directly in the ODCS JSON Schema — as an `x-natural-key` extension or similar — and carry that through to the upstream `open-data-contract-standard` Pydantic models (via a `__natural_key__` class var or `Field` annotation). This is an improvement beyond just simplifying this code: it makes the identity semantics of each model explicit and authoritative in the schema itself, rather than having them implied by convention or rediscovered by downstream consumers. Once that lands, all six helpers and the key table collapse into a single ~15-line recursive function that walks the model tree by reflection — adding or changing a list field in the ODCS schema would require no changes here. See the `NOTE` in `ContractDiff._normalize()` for the exact upstream change required.

### Extension Pattern

The project uses factory patterns for extensibility:
- `exporter_factory` and `importer_factory` allow registering custom exporters/importers
- You can create custom exporters for new output formats or importers for new input formats

### Testing Approach

- Tests are organized in the `tests/` directory
- Many tests use fixtures in `tests/fixtures/` which provide sample data contracts and test data
- Supports integration testing with various databases and data stores
- **Tests describe expected behavior, not actual behavior.** Write the test for what the code *should* do. If the test fails, fix the code under test, not the test (unless there is a justified reason for simplification).

## Code Conventions

- Python 3.10+ syntax and features
- Uses Pydantic for data validation and schema definition
- Type hints throughout the codebase
- Follows PEP 8 style guidelines with some adjustments (120 character line length)