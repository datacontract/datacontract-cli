import logging

from typer.testing import CliRunner

from datacontract.cli import app

runner = CliRunner()

logging.basicConfig(level=logging.DEBUG, force=True)


class TestBreakingModels:

    def test_model_removed(self):
        result = runner.invoke(app, ["breaking", "./examples/breaking/datacontract.yaml",
                                     "./examples/breaking/datacontract-models.yaml"])
        assert result.exit_code == 1
        assert r"""1 breaking changes: 1 error, 0 warning
error   [model-removed] at ./examples/breaking/datacontract-models.yaml
        in models
            removed the model `my_table`
""" in result.stdout


class TestBreakingFields:

    def test_headline(self):
        result = runner.invoke(app, ["breaking", "./examples/breaking/datacontract.yaml",
                                     "./examples/breaking/datacontract-fields.yaml"])
        assert result.exit_code == 1
        assert "4 breaking changes: 3 error, 1 warning" in result.stdout

    def test_field_removed(self):
        result = runner.invoke(app, ["breaking", "./examples/breaking/datacontract.yaml",
                                     "./examples/breaking/datacontract-fields.yaml"])
        assert result.exit_code == 1
        assert r"""error   [field-removed] at ./examples/breaking/datacontract-fields.yaml
        in models -> my_table
            removed the field `updated_at`
""" in result.stdout

    def test_type_changed(self):
        result = runner.invoke(app, ["breaking", "./examples/breaking/datacontract.yaml",
                                     "./examples/breaking/datacontract-fields.yaml"])
        assert result.exit_code == 1
        assert r"""error   [field-type-changed] at ./examples/breaking/datacontract-fields.yaml
        in models -> my_table -> id
            changed the type from `integer` to `string`
""" in result.stdout

    def test_format_changed(self):
        result = runner.invoke(app, ["breaking", "./examples/breaking/datacontract.yaml",
                                     "./examples/breaking/datacontract-fields.yaml"])
        assert result.exit_code == 1
        assert r"""error   [field-format-changed] at ./examples/breaking/datacontract-fields.yaml
        in models -> my_table -> created_at
            changed the format from `YYYY-MM-DD` to `YYYY/MM/DD`
""" in result.stdout

    def test_description_changed(self):
        result = runner.invoke(app, ["breaking", "./examples/breaking/datacontract.yaml",
                                     "./examples/breaking/datacontract-fields.yaml"])
        assert result.exit_code == 1
        assert r"""warning [field-description-changed] at 
./examples/breaking/datacontract-fields.yaml
        in models -> my_table -> id
            changed the description
""" in result.stdout


