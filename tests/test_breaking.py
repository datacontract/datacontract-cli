from typer.testing import CliRunner

from datacontract.cli import app

runner = CliRunner()

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_no_breaking_changes():
    result = runner.invoke(
        app,
        [
            "breaking",
            "./fixtures/breaking/datacontract-fields-v2.yaml",
            "./fixtures/breaking/datacontract-fields-v2.yaml",
        ],
    )
    assert result.exit_code == 0
    assert "0 breaking changes: 0 error, 0 warning\n" in result.stdout


def test_quality_added():
    result = runner.invoke(
        app,
        [
            "breaking",
            "./fixtures/breaking/datacontract-quality-v1.yaml",
            "./fixtures/breaking/datacontract-quality-v2.yaml",
        ],
    )
    assert result.exit_code == 0
    assert "0 breaking changes: 0 error, 0 warning\n" in result.stdout


def test_quality_removed():
    result = runner.invoke(
        app,
        [
            "breaking",
            "./fixtures/breaking/datacontract-quality-v2.yaml",
            "./fixtures/breaking/datacontract-quality-v1.yaml",
        ],
    )
    assert result.exit_code == 0
    assert "1 breaking changes: 0 error, 1 warning\n" in result.stdout


def test_quality_updated():
    result = runner.invoke(
        app,
        [
            "breaking",
            "./fixtures/breaking/datacontract-quality-v2.yaml",
            "./fixtures/breaking/datacontract-quality-v3.yaml",
        ],
    )
    assert result.exit_code == 0
    assert "2 breaking changes: 0 error, 2 warning\n" in result.stdout


def test_models_added():
    result = runner.invoke(
        app,
        [
            "breaking",
            "./fixtures/breaking/datacontract-models-v1.yaml",
            "./fixtures/breaking/datacontract-models-v2.yaml",
        ],
    )

    output = result.stdout

    assert result.exit_code == 0
    assert "0 breaking changes: 0 error, 0 warning\n" in output
    assert "model_added" not in output
    assert "model_description_added" not in output


def test_models_removed():
    result = runner.invoke(
        app,
        [
            "breaking",
            "./fixtures/breaking/datacontract-models-v2.yaml",
            "./fixtures/breaking/datacontract-models-v1.yaml",
        ],
    )

    output = result.stdout

    assert result.exit_code == 1
    assert "1 breaking changes: 1 error, 0 warning\n" in output
    assert "model_description_removed" not in output


def test_models_updated():
    result = runner.invoke(
        app,
        [
            "breaking",
            "./fixtures/breaking/datacontract-models-v2.yaml",
            "./fixtures/breaking/datacontract-models-v3.yaml",
        ],
    )

    output = result.stdout

    assert result.exit_code == 1
    assert "1 breaking changes: 1 error, 0 warning\n" in output
    assert "model_description_updated" not in output


def test_fields_added():
    result = runner.invoke(
        app,
        [
            "breaking",
            "./fixtures/breaking/datacontract-fields-v1.yaml",
            "./fixtures/breaking/datacontract-fields-v2.yaml",
        ],
    )

    output = result.stdout

    assert result.exit_code == 0
    assert "14 breaking changes: 0 error, 14 warning\n" in output
    assert "field_added" not in output
    assert "field_description_added" not in output
    assert "field_tags_added" not in output


def test_fields_removed():
    result = runner.invoke(
        app,
        [
            "breaking",
            "./fixtures/breaking/datacontract-fields-v2.yaml",
            "./fixtures/breaking/datacontract-fields-v1.yaml",
        ],
    )

    output = result.stdout

    assert result.exit_code == 1
    assert "15 breaking changes: 5 error, 10 warning\n" in output
    assert "field_description_removed" not in output
    assert "field_enum_removed" not in output
    assert "field_tags_removed" not in output


def test_fields_updated():
    result = runner.invoke(
        app,
        [
            "breaking",
            "./fixtures/breaking/datacontract-fields-v2.yaml",
            "./fixtures/breaking/datacontract-fields-v3.yaml",
        ],
    )

    output = result.stdout

    assert result.exit_code == 1
    assert "18 breaking changes: 15 error, 3 warning\n" in output
    assert "field_description_updated" not in output
    assert "field_tags_updated" not in output


def test_definition_added():
    result = runner.invoke(
        app,
        [
            "breaking",
            "./fixtures/breaking/datacontract-definitions-v1.yaml",
            "./fixtures/breaking/datacontract-definitions-v2.yaml",
        ],
    )

    output = result.stdout

    assert result.exit_code == 0
    assert "13 breaking changes: 0 error, 13 warning\n" in output
    assert "field_description_added" not in output
    assert "field_tags_added" not in output


def test_definition_removed():
    result = runner.invoke(
        app,
        [
            "breaking",
            "./fixtures/breaking/datacontract-definitions-v2.yaml",
            "./fixtures/breaking/datacontract-definitions-v1.yaml",
        ],
    )

    output = result.stdout

    assert result.exit_code == 1
    assert "12 breaking changes: 3 error, 9 warning\n" in output
    assert "field_description_removed" not in output
    assert "field_tags_removed" not in output
    assert "field_enum_removed" not in output


def test_definition_updated():
    result = runner.invoke(
        app,
        [
            "breaking",
            "./fixtures/breaking/datacontract-definitions-v2.yaml",
            "./fixtures/breaking/datacontract-definitions-v3.yaml",
        ],
    )

    output = result.stdout

    assert result.exit_code == 1
    assert "13 breaking changes: 12 error, 1 warning\n" in output
    assert "field_description_updated" not in output
    assert "field_tags_updated" not in output


def test_array_fields_updated():
    result = runner.invoke(
        app,
        [
            "breaking",
            "./fixtures/breaking/datacontract-fields-array-v1.yaml",
            "./fixtures/breaking/datacontract-fields-array-v2.yaml",
        ],
    )

    output = result.stdout

    assert result.exit_code == 1
    assert "3 breaking changes: 3 error, 0 warning\n" in output
    assert "field_pii_updated" in output
    assert "in models.DataType.fields.Records.items.fields.Field1.pii" in output
    assert "changed from `false` to `true`" in output

    assert "field_classification_updated" in output
    assert "changed from `Unclassified` to `classified`" in output

    assert "field_type_updated" in output
    assert "changed from `string` to `int`" in output

    assert "field_description_removed" not in output
    assert "field_tags_removed" not in output
    assert "field_enum_removed" not in output
