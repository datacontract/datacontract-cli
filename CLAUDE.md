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

# Check for breaking changes
datacontract breaking datacontract-v1.yaml datacontract-v2.yaml
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

6. **Breaking Change Detection (`datacontract/breaking/`)**: Logic for identifying breaking changes between versions.

### Extension Pattern

The project uses factory patterns for extensibility:
- `exporter_factory` and `importer_factory` allow registering custom exporters/importers
- You can create custom exporters for new output formats or importers for new input formats

### Testing Approach

- Tests are organized in the `tests/` directory
- Many tests use fixtures in `tests/fixtures/` which provide sample data contracts and test data
- Supports integration testing with various databases and data stores

## Code Conventions

- Python 3.10+ syntax and features
- Uses Pydantic for data validation and schema definition
- Type hints throughout the codebase
- Follows PEP 8 style guidelines with some adjustments (120 character line length)