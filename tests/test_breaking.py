import logging

import pytest
from typer.testing import CliRunner

from datacontract.cli import app

runner = CliRunner()

logging.basicConfig(level=logging.DEBUG, force=True)


def test_no_breaking_changes():
    result = runner.invoke(app, ["breaking", "./examples/breaking/datacontract-fields-v2.yaml",
                                 "./examples/breaking/datacontract-fields-v2.yaml"])
    assert result.exit_code == 0
    assert "0 breaking changes: 0 error, 0 warning" in result.stdout


class TestModelsAdded:

    @pytest.fixture(scope='class')
    def output(self):
        result = runner.invoke(app, ["breaking", "./examples/breaking/datacontract-models-v1.yaml",
                                     "./examples/breaking/datacontract-models-v2.yaml"])
        assert result.exit_code == 0
        return result.stdout

    def test_headline(self, output):
        assert "0 breaking changes: 0 error, 0 warning" in output

    def test_model_added(self, output):
        assert "model_added" not in output

    def test_description_added(self, output):
        assert "model_description_added" not in output


class TestModelsRemoved:

    @pytest.fixture(scope='class')
    def output(self):
        result = runner.invoke(app, ["breaking", "./examples/breaking/datacontract-models-v2.yaml",
                                     "./examples/breaking/datacontract-models-v1.yaml"])
        assert result.exit_code == 1
        return result.stdout

    def test_headline(self, output):
        assert "1 breaking changes: 1 error, 0 warning" in output

    def test_model_removed(self, output):
        assert r"""error   [model_removed] at ./examples/breaking/datacontract-models-v1.yaml
        in models.my_table_2
            removed the model""" in output

    def test_description_removed(self, output):
        assert "model_description_removed" not in output


class TestModelsUpdated:

    @pytest.fixture(scope='class')
    def output(self):
        result = runner.invoke(app, ["breaking", "./examples/breaking/datacontract-models-v2.yaml",
                                     "./examples/breaking/datacontract-models-v3.yaml"])
        assert result.exit_code == 1
        return result.stdout

    def test_headline(self, output):
        assert "1 breaking changes: 1 error, 0 warning" in output

    def test_model_type_updated(self, output):
        assert r"""error   [model_type_updated] at ./examples/breaking/datacontract-models-v3.yaml
        in models.my_table.type
            changed from `table` to `object`""" in output

    def test_model_description_updated(self, output):
        assert "model_description_updated" not in output


class TestFieldsAdded:

    @pytest.fixture(scope='class')
    def output(self):
        result = runner.invoke(app, ["breaking", "./examples/breaking/datacontract-fields-v1.yaml",
                                     "./examples/breaking/datacontract-fields-v2.yaml"])
        assert result.exit_code == 0
        return result.stdout

    def test_headline(self, output):
        assert "12 breaking changes: 0 error, 12 warning" in output

    def test_field_added(self, output):
        assert "field_added" not in output

    def test_type_added(self, output):
        assert r"""warning [field_type_added] at ./examples/breaking/datacontract-fields-v2.yaml
        in models.my_table.field_type.type
            added with value: `string`""" in output

    def test_format_added(self, output):
        assert r"""warning [field_format_added] at ./examples/breaking/datacontract-fields-v2.yaml
        in models.my_table.field_format.format
            added with value: `email`""" in output

    def test_description_added(self, output):
        assert "field_description_added" not in output

    def test_pii_added(self, output):
        assert r"""warning [field_pii_added] at ./examples/breaking/datacontract-fields-v2.yaml
        in models.my_table.field_pii.pii
            added with value: `true`""" in output

    def test_classification_added(self, output):
        assert r"""warning [field_classification_added] at 
./examples/breaking/datacontract-fields-v2.yaml
        in models.my_table.field_classification.classification
            added with value: `sensitive`""" in output

    def test_pattern_added(self, output):
        assert r"""warning [field_pattern_added] at ./examples/breaking/datacontract-fields-v2.yaml
        in models.my_table.field_pattern.pattern
            added with value: `^[A-Za-z0-9]{8,14}$`""" in output

    def test_min_length_added(self, output):
        assert r"""warning [field_minLength_added] at 
./examples/breaking/datacontract-fields-v2.yaml
        in models.my_table.field_minLength.minLength
            added with value: `8`""" in output

    def test_max_length_added(self, output):
        assert r"""warning [field_maxLength_added] at 
./examples/breaking/datacontract-fields-v2.yaml
        in models.my_table.field_maxLength.maxLength
            added with value: `14`""" in output

    def test_minimum_added(self, output):
        assert r"""warning [field_minimum_added] at ./examples/breaking/datacontract-fields-v2.yaml
        in models.my_table.field_minimum.minimum
            added with value: `8`""" in output

    def test_minimum_exclusive_added(self, output):
        assert r"""warning [field_minimumExclusive_added] at 
./examples/breaking/datacontract-fields-v2.yaml
        in models.my_table.field_minimumExclusive.minimumExclusive
            added with value: `8`""" in output

    def test_maximum_added(self, output):
        assert r"""warning [field_maximum_added] at ./examples/breaking/datacontract-fields-v2.yaml
        in models.my_table.field_maximum.maximum
            added with value: `14`""" in output

    def test_maximum_exclusive_added(self, output):
        assert r"""warning [field_maximumExclusive_added] at 
./examples/breaking/datacontract-fields-v2.yaml
        in models.my_table.field_maximumExclusive.maximumExclusive
            added with value: `14`""" in output

    def test_enum_added(self, output):
        assert r"""warning [field_enum_added] at ./examples/breaking/datacontract-fields-v2.yaml
        in models.my_table.field_enum.enum
            added with value: `['one']`""" in output

    def test_tags_added(self, output):
        assert "field_tags_added" not in output


class TestFieldsRemoved:
    @pytest.fixture(scope='class')
    def output(self):
        result = runner.invoke(app, ["breaking", "./examples/breaking/datacontract-fields-v2.yaml",
                                     "./examples/breaking/datacontract-fields-v1.yaml"])
        assert result.exit_code == 1
        return result.stdout

    def test_headline(self, output):
        assert "13 breaking changes: 5 error, 8 warning" in output

    def test_type_removed(self, output):
        assert r"""warning [field_type_removed] at ./examples/breaking/datacontract-fields-v1.yaml
        in models.my_table.field_type.type
            removed field property""" in output

    def test_format_removed(self, output):
        assert r"""warning [field_format_removed] at 
./examples/breaking/datacontract-fields-v1.yaml
        in models.my_table.field_format.format
            removed field property""" in output

    def test_description_removed(self, output):
        assert "field_description_removed" not in output

    def test_pii_removed(self, output):
        assert r"""error   [field_pii_removed] at ./examples/breaking/datacontract-fields-v1.yaml
        in models.my_table.field_pii.pii
            removed field property""" in output

    def test_classification_removed(self, output):
        assert r"""error   [field_classification_removed] at 
./examples/breaking/datacontract-fields-v1.yaml
        in models.my_table.field_classification.classification
            removed field property""" in output

    def test_pattern_removed(self, output):
        assert r"""error   [field_pattern_removed] at 
./examples/breaking/datacontract-fields-v1.yaml
        in models.my_table.field_pattern.pattern
            removed field property""" in output

    def test_min_length_removed(self, output):
        assert r"""warning [field_minLength_removed] at 
./examples/breaking/datacontract-fields-v1.yaml
        in models.my_table.field_minLength.minLength
            removed field property""" in output

    def test_max_length_removed(self, output):
        assert r"""warning [field_maxLength_removed] at 
./examples/breaking/datacontract-fields-v1.yaml
        in models.my_table.field_maxLength.maxLength
            removed field property""" in output

    def test_minimum_removed(self, output):
        assert r"""warning [field_minimum_removed] at 
./examples/breaking/datacontract-fields-v1.yaml
        in models.my_table.field_minimum.minimum
            removed field property""" in output

    def test_minimum_exclusive_removed(self, output):
        assert r"""warning [field_minimumExclusive_removed] at 
./examples/breaking/datacontract-fields-v1.yaml
        in models.my_table.field_minimumExclusive.minimumExclusive
            removed field property""" in output

    def test_maximum_removed(self, output):
        assert r"""warning [field_maximum_removed] at 
./examples/breaking/datacontract-fields-v1.yaml
        in models.my_table.field_maximum.maximum
            removed field property""" in output

    def test_maximum_exclusive_removed(self, output):
        assert r"""warning [field_maximumExclusive_removed] at 
./examples/breaking/datacontract-fields-v1.yaml
        in models.my_table.field_maximumExclusive.maximumExclusive
            removed field property""" in output

    def test_enum_removed(self, output):
        assert "field_enum_removed" not in output

    def test_tags_removed(self, output):
        assert "field_tags_removed" not in output

    def test_nested_field_removed(self, output):
        assert r"""error   [field_removed] at ./examples/breaking/datacontract-fields-v1.yaml
        in models.my_table.field_fields.fields.new_nested_field
            removed the field""" in output

    def test_field_removed(self, output):
        assert r"""error   [field_removed] at ./examples/breaking/datacontract-fields-v1.yaml
        in models.my_table.new_field
            removed the field""" in output


class TestFieldsUpdated:

    @pytest.fixture(scope='class')
    def output(self):
        result = runner.invoke(app, ["breaking", "./examples/breaking/datacontract-fields-v2.yaml",
                                     "./examples/breaking/datacontract-fields-v3.yaml"])
        assert result.exit_code == 1
        return result.stdout

    def test_headline(self, output):
        print(output)
        assert "15 breaking changes: 15 error, 0 warning" in output

    def test_type_updated(self, output):
        assert r"""error   [field_type_updated] at ./examples/breaking/datacontract-fields-v3.yaml
        in models.my_table.field_type.type
            changed from `string` to `integer`""" in output

    def test_format_updated(self, output):
        assert """error   [field_format_updated] at 
./examples/breaking/datacontract-fields-v3.yaml
        in models.my_table.field_format.format
            changed from `email` to `url`""" in output

    def test_required_updated(self, output):
        assert """error   [field_required_updated] at 
./examples/breaking/datacontract-fields-v3.yaml
        in models.my_table.field_required.required
            changed from `false` to `true`""" in output

    def test_unique_updated(self, output):
        assert r"""error   [field_unique_updated] at 
./examples/breaking/datacontract-fields-v3.yaml
        in models.my_table.field_unique.unique
            changed from `false` to `true`""" in output

    def test_description_updated(self, output):
        assert "field_description_updated" not in output

    def test_pii_updated(self, output):
        assert r"""error   [field_pii_updated] at ./examples/breaking/datacontract-fields-v3.yaml
        in models.my_table.field_pii.pii
            changed from `true` to `false`""" in output

    def test_classification_updated(self, output):
        assert r"""error   [field_classification_updated] at 
./examples/breaking/datacontract-fields-v3.yaml
        in models.my_table.field_classification.classification
            changed from `sensitive` to `restricted`""" in output

    def test_pattern_updated(self, output):
        assert r"""error   [field_pattern_updated] at 
./examples/breaking/datacontract-fields-v3.yaml
        in models.my_table.field_pattern.pattern
            changed from `^[A-Za-z0-9]{8,14}$` to `^[A-Za-z0-9]$`""" in output

    def test_min_length_updated(self, output):
        assert r"""error   [field_minLength_updated] at 
./examples/breaking/datacontract-fields-v3.yaml
        in models.my_table.field_minLength.minLength
            changed from `8` to `10`""" in output

    def test_max_length_updated(self, output):
        assert r"""error   [field_maxLength_updated] at 
./examples/breaking/datacontract-fields-v3.yaml
        in models.my_table.field_maxLength.maxLength
            changed from `14` to `20`""" in output

    def test_minimum_updated(self, output):
        assert r"""error   [field_minimum_updated] at 
./examples/breaking/datacontract-fields-v3.yaml
        in models.my_table.field_minimum.minimum
            changed from `8` to `10`""" in output

    def test_minimum_exclusive_updated(self, output):
        assert r"""error   [field_minimumExclusive_updated] at 
./examples/breaking/datacontract-fields-v3.yaml
        in models.my_table.field_minimumExclusive.minimumExclusive
            changed from `8` to `10`""" in output

    def test_maximum_updated(self, output):
        assert r"""error   [field_maximum_updated] at 
./examples/breaking/datacontract-fields-v3.yaml
        in models.my_table.field_maximum.maximum
            changed from `14` to `20`""" in output

    def test_maximum_exclusive_updated(self, output):
        assert r"""error   [field_maximumExclusive_updated] at 
./examples/breaking/datacontract-fields-v3.yaml
        in models.my_table.field_maximumExclusive.maximumExclusive
            changed from `14` to `20`""" in output

    def test_enum_updated(self, output):
        assert r"""error   [field_enum_updated] at ./examples/breaking/datacontract-fields-v3.yaml
        in models.my_table.field_enum.enum
            changed from `['one']` to `['one', 'two']`""" in output

    def test_tags_updated(self, output):
        assert "field_tags_updated" not in output

    def test_nested_type_updated(self, output):
        assert r"""error   [field_type_updated] at ./examples/breaking/datacontract-fields-v3.yaml
        in models.my_table.field_fields.fields.nested_field_1.type
            changed from `string` to `integer`""" in output
