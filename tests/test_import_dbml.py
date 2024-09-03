import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--format",
            "dbml",
            "--source",
            "fixtures/dbml/import/dbml.txt",
        ],
    )
    assert result.exit_code == 0


def test_cli_with_filters():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--format",
            "dbml",
            "--source",
            "fixtures/dbml/import/dbml.txt",
            "--dbml-schema",
            "test",
            "--dbml-table",
            "foo",
        ],
    )
    assert result.exit_code == 0


def test_dbml_import():
    result = DataContract().import_from_source("dbml", "fixtures/dbml/import/dbml.txt")

    print("Result:\n", result.to_yaml())
    with open("fixtures/dbml/import/datacontract.yaml") as file:
        expected = file.read()
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)


def test_dbml_import_with_schema_filter():
    result = DataContract().import_from_source("dbml", "fixtures/dbml/import/dbml.txt", dbml_schema=["orders"])

    print("Result:\n", result.to_yaml())
    with open("fixtures/dbml/import/datacontract_schema_filtered.yaml") as file:
        expected = file.read()
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)


def test_dbml_import_with_tablename_filter():
    result = DataContract().import_from_source("dbml", "fixtures/dbml/import/dbml.txt", dbml_table=["orders"])

    print("Result:\n", result.to_yaml())
    with open("fixtures/dbml/import/datacontract_table_filtered.yaml") as file:
        expected = file.read()
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
