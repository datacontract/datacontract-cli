import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

# logging.basicConfig(level=logging.DEBUG, force=True)

csv_file_path = "fixtures/csv/data/sample_data.csv"


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "--format",
            "csv",
            "--source",
            csv_file_path,
        ],
    )
    assert result.exit_code == 0


def test_import_csv():
    source = "fixtures/csv/data/sample_data_5_column.csv"
    result = DataContract().import_from_source("csv", source)
    model = result.models["sample_data_5_column"]
    assert model is not None
    assert len(model.fields["field_one"].examples) == 5
    assert len(model.fields["field_two"].examples) > 0
    assert len(model.fields["field_three"].examples) > 0
    assert model.fields["field_four"].examples is None
    assert model.fields["field_five"].examples is None
    for k in model.fields.keys():
        model.fields[k].examples = None

    expected = f"""dataContractSpecification: 1.1.0
id: my-data-contract-id
info:
  title: My Data Contract
  version: 0.0.1
servers:
  production:
    type: local
    format: csv
    path: {source}
    delimiter: ','
models:
  sample_data_5_column:
    description: Generated model of fixtures/csv/data/sample_data_5_column.csv
    type: table
    fields:
      field_one:
        type: string
        required: true
        unique: true
      field_two:
        type: integer
        required: true
        minimum: 14
        maximum: 89
      field_three:
        type: timestamp
        unique: true
      field_four:
        type: string
      field_five:
        type: boolean
        required: true
      field_six:
        type: string
        format: email
    """
    print("Result", result.to_yaml())
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected)
    # Disable linters so we don't get "missing description" warnings
    assert DataContract(data_contract_str=expected).lint(enabled_linters=set()).has_passed()
