from unittest.mock import MagicMock

import yaml
from google.cloud import bigquery
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract
from datacontract.imports.bigquery_importer import import_bigquery_from_api, import_bigquery_from_json

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "bigquery",
            "--source",
            "fixtures/bigquery/import/complete_table_schema.json",
        ],
    )
    assert result.exit_code == 0


def test_import_bigquery_schema():
    result = DataContract.import_from_source("bigquery", "fixtures/bigquery/import/complete_table_schema.json")

    print("Result:\n", result.to_yaml())
    with open("fixtures/bigquery/import/datacontract.yaml") as file:
        expected = file.read()
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)


def test_import_multiple_bigquery_schemas_with_different_types():
    # Import multiple BigQuery schemas and combine them
    result = DataContract.import_from_source("bigquery", "fixtures/bigquery/import/multi_import_table.json")

    # Import additional schemas and append to the result
    for source in [
        "fixtures/bigquery/import/multi_import_external_table.json",
        "fixtures/bigquery/import/multi_import_snapshot.json",
        "fixtures/bigquery/import/multi_import_view.json",
        "fixtures/bigquery/import/multi_import_materialized_view.json",
        "fixtures/bigquery/import/multi_import_table_valued_function.json",
    ]:
        additional = import_bigquery_from_json(source)
        result.schema_.extend(additional.schema_)

    print("Result:\n", result.to_yaml())
    with open("fixtures/bigquery/import/datacontract_multi_import.yaml") as file:
        expected = file.read()
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)


def test_import_bigquery_table_valued_function_from_api(monkeypatch):
    client = MagicMock()
    client.get_routine.return_value.to_api_repr.return_value = {
        "description": "A table function",
        "arguments": [{"name": "start_ts", "dataType": {"typeKind": "TIMESTAMP"}}],
        "returnTableType": {"columns": [{"name": "id", "type": {"typeKind": "STRING"}}]},
    }
    monkeypatch.setattr(bigquery, "Client", lambda project: client)

    result = import_bigquery_from_api(None, "p", "d", ["fn"])

    client.list_tables.assert_not_called()
    schema = result.schema_[0]
    assert (schema.name, schema.physicalType, schema.properties[0].name) == ("fn", "table_valued_function", "id")
    assert schema.customProperties[0].value == [{"name": "start_ts", "physicalType": "TIMESTAMP"}]
