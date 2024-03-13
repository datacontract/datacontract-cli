import logging

import pytest
from typer.testing import CliRunner

from datacontract.cli import app

runner = CliRunner()

logging.basicConfig(level=logging.DEBUG, force=True)


def test_no_changes():
    result = runner.invoke(app, ["changelog", "./examples/breaking/datacontract-fields-v2.yaml",
                                 "./examples/breaking/datacontract-fields-v2.yaml"])
    assert result.exit_code == 0
    assert "0 changes: 0 error, 0 warning, 0 info\n" in result.stdout


class TestQualityAdded:
    @pytest.fixture(scope='class')
    def result(self):
        result = runner.invoke(app, ["changelog", "./examples/breaking/datacontract-quality-v1.yaml",
                                     "./examples/breaking/datacontract-quality-v2.yaml"])
        return result

    @pytest.fixture(scope='class')
    def output(self, result):
        return result.stdout

    def test_exit_code(self, result):
        assert result.exit_code == 0

    def test_headline(self, output):
        assert "1 changes: 0 error, 0 warning, 1 info\n" in output

    def test_quality_added(self, output):
        assert """info    [quality_added] at ./examples/breaking/datacontract-quality-v2.yaml
        in quality
            added quality""" in output


class TestQualityRemoved:

    @pytest.fixture(scope='class')
    def result(self):
        result = runner.invoke(app, ["changelog", "./examples/breaking/datacontract-quality-v2.yaml",
                                     "./examples/breaking/datacontract-quality-v1.yaml"])
        return result

    @pytest.fixture(scope='class')
    def output(self, result):
        return result.stdout

    def test_exit_code(self, result):
        assert result.exit_code == 0

    def test_headline(self, output):
        assert "1 changes: 0 error, 1 warning, 0 info\n" in output

    def test_quality_removed(self, output):
        assert r"""warning [quality_removed] at ./examples/breaking/datacontract-quality-v1.yaml
        in quality
            removed quality""" in output


class TestQualityUpdated:

    @pytest.fixture(scope='class')
    def result(self):
        result = runner.invoke(app, ["changelog", "./examples/breaking/datacontract-quality-v2.yaml",
                                     "./examples/breaking/datacontract-quality-v3.yaml"])
        return result

    @pytest.fixture(scope='class')
    def output(self, result):
        return result.stdout

    def test_exit_code(self, result):
        assert result.exit_code == 0

    def test_headline(self, output):
        assert "2 changes: 0 error, 2 warning, 0 info\n" in output

    def test_type_updated(self, output):
        assert r"""warning [quality_type_updated] at 
./examples/breaking/datacontract-quality-v3.yaml
        in quality.type
            changed from `SodaCL` to `custom`""" in output

    def test_specification_updated(self, output):
        assert r"""warning [quality_specification_updated] at 
./examples/breaking/datacontract-quality-v3.yaml
        in quality.specification
            changed from `checks for orders:
  - freshness(column_1) < 1d` to `checks for orders:
  - freshness(column_1) < 2d`""" in output


class TestModelsAdded:

    @pytest.fixture(scope='class')
    def result(self):
        result = runner.invoke(app, ["changelog", "./examples/breaking/datacontract-models-v1.yaml",
                                     "./examples/breaking/datacontract-models-v2.yaml"])
        return result

    @pytest.fixture(scope='class')
    def output(self, result):
        return result.stdout

    def test_exit_code(self, result):
        assert result.exit_code == 0

    def test_headline(self, output):
        assert "2 changes: 0 error, 0 warning, 2 info\n" in output

    def test_model_added(self, output):
        assert """info    [model_added] at ./examples/breaking/datacontract-models-v2.yaml
        in models.my_table_2
            added the model""" in output

    def test_description_added(self, output):
        assert """info    [model_description_added] at 
./examples/breaking/datacontract-models-v2.yaml
        in models.my_table.description
            added with value: `My Model Description`""" in output


class TestModelsRemoved:

    @pytest.fixture(scope='class')
    def result(self):
        result = runner.invoke(app, ["changelog", "./examples/breaking/datacontract-models-v2.yaml",
                                     "./examples/breaking/datacontract-models-v1.yaml"])
        return result

    @pytest.fixture(scope='class')
    def output(self, result):
        return result.stdout

    def test_exit_code(self, result):
        assert result.exit_code == 0

    def test_headline(self, output):
        assert "2 changes: 1 error, 0 warning, 1 info\n" in output

    def test_model_removed(self, output):
        assert r"""error   [model_removed] at ./examples/breaking/datacontract-models-v1.yaml
        in models.my_table_2
            removed the model""" in output

    def test_description_removed(self, output):
        assert """info    [model_description_removed] at 
./examples/breaking/datacontract-models-v1.yaml
        in models.my_table.description
            removed model property""" in output


class TestModelsUpdated:

    @pytest.fixture(scope='class')
    def result(self):
        result = runner.invoke(app, ["changelog", "./examples/breaking/datacontract-models-v2.yaml",
                                     "./examples/breaking/datacontract-models-v3.yaml"])
        return result

    @pytest.fixture(scope='class')
    def output(self, result):
        return result.stdout

    def test_exit_code(self, result):
        assert result.exit_code == 0

    def test_headline(self, output):
        assert "2 changes: 1 error, 0 warning, 1 info\n" in output

    def test_model_type_updated(self, output):
        assert r"""error   [model_type_updated] at ./examples/breaking/datacontract-models-v3.yaml
        in models.my_table.type
            changed from `table` to `object`""" in output

    def test_model_description_updated(self, output):
        assert """info    [model_description_updated] at 
./examples/breaking/datacontract-models-v3.yaml
        in models.my_table.description
            changed from `My Model Description` to `My Updated Model 
Description`""" in output


class TestFieldsAdded:

    @pytest.fixture(scope='class')
    def result(self):
        result = runner.invoke(app, ["changelog", "./examples/breaking/datacontract-fields-v1.yaml",
                                     "./examples/breaking/datacontract-fields-v2.yaml"])
        return result

    @pytest.fixture(scope='class')
    def output(self, result):
        return result.stdout

    def test_exit_code(self, result):
        assert result.exit_code == 0

    def test_headline(self, output):
        assert "18 changes: 0 error, 14 warning, 4 info\n" in output

    def test_field_added(self, output):
        assert """info    [field_added] at ./examples/breaking/datacontract-fields-v2.yaml
        in models.my_table.fields.new_field
            added the field""" in output

    def test_references_added(self, output):
        assert """warning [field_references_added] at 
./examples/breaking/datacontract-fields-v2.yaml
        in models.my_table.fields.field_references.references
            added with value: `my_table.field_type`""" in output

    def test_type_added(self, output):
        assert r"""warning [field_type_added] at ./examples/breaking/datacontract-fields-v2.yaml
        in models.my_table.fields.field_type.type
            added with value: `string`""" in output

    def test_format_added(self, output):
        assert r"""warning [field_format_added] at ./examples/breaking/datacontract-fields-v2.yaml
        in models.my_table.fields.field_format.format
            added with value: `email`""" in output

    def test_description_added(self, output):
        assert """info    [field_description_added] at 
./examples/breaking/datacontract-fields-v2.yaml
        in models.my_table.fields.field_description.description
            added with value: `My Description`""" in output

    def test_pii_added(self, output):
        assert r"""warning [field_pii_added] at ./examples/breaking/datacontract-fields-v2.yaml
        in models.my_table.fields.field_pii.pii
            added with value: `true`""" in output

    def test_classification_added(self, output):
        assert r"""warning [field_classification_added] at 
./examples/breaking/datacontract-fields-v2.yaml
        in models.my_table.fields.field_classification.classification
            added with value: `sensitive`""" in output

    def test_pattern_added(self, output):
        assert r"""warning [field_pattern_added] at ./examples/breaking/datacontract-fields-v2.yaml
        in models.my_table.fields.field_pattern.pattern
            added with value: `^[A-Za-z0-9]{8,14}$`""" in output

    def test_min_length_added(self, output):
        assert r"""warning [field_min_length_added] at 
./examples/breaking/datacontract-fields-v2.yaml
        in models.my_table.fields.field_minLength.minLength
            added with value: `8`""" in output

    def test_max_length_added(self, output):
        assert r"""warning [field_max_length_added] at 
./examples/breaking/datacontract-fields-v2.yaml
        in models.my_table.fields.field_maxLength.maxLength
            added with value: `14`""" in output

    def test_minimum_added(self, output):
        assert r"""warning [field_minimum_added] at ./examples/breaking/datacontract-fields-v2.yaml
        in models.my_table.fields.field_minimum.minimum
            added with value: `8`""" in output

    def test_minimum_exclusive_added(self, output):
        assert r"""warning [field_exclusive_minimum_added] at 
./examples/breaking/datacontract-fields-v2.yaml
        in models.my_table.fields.field_exclusiveMinimum.exclusiveMinimum
            added with value: `8`""" in output

    def test_maximum_added(self, output):
        assert r"""warning [field_maximum_added] at ./examples/breaking/datacontract-fields-v2.yaml
        in models.my_table.fields.field_maximum.maximum
            added with value: `14`""" in output

    def test_maximum_exclusive_added(self, output):
        assert r"""warning [field_exclusive_maximum_added] at 
./examples/breaking/datacontract-fields-v2.yaml
        in models.my_table.fields.field_exclusiveMaximum.exclusiveMaximum
            added with value: `14`""" in output

    def test_enum_added(self, output):
        assert r"""warning [field_enum_added] at ./examples/breaking/datacontract-fields-v2.yaml
        in models.my_table.fields.field_enum.enum
            added with value: `['one']`""" in output

    def test_tags_added(self, output):
        assert """info    [field_tags_added] at ./examples/breaking/datacontract-fields-v2.yaml
        in models.my_table.fields.field_tags.tags
            added with value: `['one']`""" in output

    def test_ref_added(self, output):
        assert r"""warning [field_ref_added] at ./examples/breaking/datacontract-fields-v2.yaml
        in models.my_table.fields.field_ref.$ref
            added with value: `#/definitions/my_definition`""" in output

    def test_nested_field_added(self, output):
        assert """info    [field_added] at ./examples/breaking/datacontract-fields-v2.yaml
        in models.my_table.fields.field_fields.fields.new_nested_field
            added the field""" in output


class TestFieldsRemoved:
    @pytest.fixture(scope='class')
    def result(self):
        result = runner.invoke(app, ["changelog", "./examples/breaking/datacontract-fields-v2.yaml",
                                     "./examples/breaking/datacontract-fields-v1.yaml"])
        return result

    @pytest.fixture(scope='class')
    def output(self, result):
        return result.stdout

    def test_exit_code(self, result):
        assert result.exit_code == 0

    def test_headline(self, output):
        assert "18 changes: 5 error, 10 warning, 3 info\n" in output

    def test_type_removed(self, output):
        assert r"""warning [field_type_removed] at ./examples/breaking/datacontract-fields-v1.yaml
        in models.my_table.fields.field_type.type
            removed field property""" in output

    def test_format_removed(self, output):
        assert r"""warning [field_format_removed] at 
./examples/breaking/datacontract-fields-v1.yaml
        in models.my_table.fields.field_format.format
            removed field property""" in output

    def test_references_removed(self, output):
        assert """warning [field_references_removed] at 
./examples/breaking/datacontract-fields-v1.yaml
        in models.my_table.fields.field_references.references
            removed field property""" in output

    def test_description_removed(self, output):
        assert """info    [field_description_removed] at 
./examples/breaking/datacontract-fields-v1.yaml
        in models.my_table.fields.field_description.description
            removed field property""" in output

    def test_pii_removed(self, output):
        assert r"""error   [field_pii_removed] at ./examples/breaking/datacontract-fields-v1.yaml
        in models.my_table.fields.field_pii.pii
            removed field property""" in output

    def test_classification_removed(self, output):
        assert r"""error   [field_classification_removed] at 
./examples/breaking/datacontract-fields-v1.yaml
        in models.my_table.fields.field_classification.classification
            removed field property""" in output

    def test_pattern_removed(self, output):
        assert r"""error   [field_pattern_removed] at 
./examples/breaking/datacontract-fields-v1.yaml
        in models.my_table.fields.field_pattern.pattern
            removed field property""" in output

    def test_min_length_removed(self, output):
        assert r"""warning [field_min_length_removed] at 
./examples/breaking/datacontract-fields-v1.yaml
        in models.my_table.fields.field_minLength.minLength
            removed field property""" in output

    def test_max_length_removed(self, output):
        assert r"""warning [field_max_length_removed] at 
./examples/breaking/datacontract-fields-v1.yaml
        in models.my_table.fields.field_maxLength.maxLength
            removed field property""" in output

    def test_minimum_removed(self, output):
        assert r"""warning [field_minimum_removed] at 
./examples/breaking/datacontract-fields-v1.yaml
        in models.my_table.fields.field_minimum.minimum
            removed field property""" in output

    def test_minimum_exclusive_removed(self, output):
        assert r"""warning [field_exclusive_minimum_removed] at 
./examples/breaking/datacontract-fields-v1.yaml
        in models.my_table.fields.field_exclusiveMinimum.exclusiveMinimum
            removed field property""" in output

    def test_maximum_removed(self, output):
        assert r"""warning [field_maximum_removed] at 
./examples/breaking/datacontract-fields-v1.yaml
        in models.my_table.fields.field_maximum.maximum
            removed field property""" in output

    def test_maximum_exclusive_removed(self, output):
        assert r"""warning [field_exclusive_maximum_removed] at 
./examples/breaking/datacontract-fields-v1.yaml
        in models.my_table.fields.field_exclusiveMaximum.exclusiveMaximum
            removed field property""" in output

    def test_ref_removed(self, output):
        assert r"""warning [field_ref_removed] at ./examples/breaking/datacontract-fields-v1.yaml
        in models.my_table.fields.field_ref.$ref
            removed field property""" in output

    def test_enum_removed(self, output):
        assert """info    [field_enum_removed] at ./examples/breaking/datacontract-fields-v1.yaml
        in models.my_table.fields.field_enum.enum
            removed field property""" in output

    def test_tags_removed(self, output):
        assert """info    [field_tags_removed] at ./examples/breaking/datacontract-fields-v1.yaml
        in models.my_table.fields.field_tags.tags
            removed field property""" in output

    def test_nested_field_removed(self, output):
        assert r"""error   [field_removed] at ./examples/breaking/datacontract-fields-v1.yaml
        in models.my_table.fields.field_fields.fields.new_nested_field
            removed the field""" in output

    def test_field_removed(self, output):
        assert r"""error   [field_removed] at ./examples/breaking/datacontract-fields-v1.yaml
        in models.my_table.fields.new_field
            removed the field""" in output


class TestFieldsUpdated:

    @pytest.fixture(scope='class')
    def result(self):
        result = runner.invoke(app, ["changelog", "./examples/breaking/datacontract-fields-v2.yaml",
                                     "./examples/breaking/datacontract-fields-v3.yaml"])
        return result

    @pytest.fixture(scope='class')
    def output(self, result):
        return result.stdout

    def test_exit_code(self, result):
        assert result.exit_code == 0

    def test_headline(self, output):
        assert "20 changes: 15 error, 3 warning, 2 info\n" in output

    def test_type_updated(self, output):
        assert r"""error   [field_type_updated] at ./examples/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_type.type
            changed from `string` to `integer`""" in output

    def test_format_updated(self, output):
        assert """error   [field_format_updated] at 
./examples/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_format.format
            changed from `email` to `url`""" in output

    def test_required_updated(self, output):
        assert """error   [field_required_updated] at 
./examples/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_required.required
            changed from `false` to `true`""" in output

    def test_primary_updated(self, output):
        assert """warning [field_primary_updated] at 
./examples/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_primary.primary
            changed from `false` to `true`""" in output

    def test_references_updated(self, output):
        assert """warning [field_references_updated] at 
./examples/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_references.references
            changed from `my_table.field_type` to `my_table.field_format`""" in output

    def test_unique_updated(self, output):
        assert r"""error   [field_unique_updated] at 
./examples/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_unique.unique
            changed from `false` to `true`""" in output

    def test_description_updated(self, output):
        assert """info    [field_description_updated] at 
./examples/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_description.description
            changed from `My Description` to `My updated Description`""" in output

    def test_pii_updated(self, output):
        assert r"""error   [field_pii_updated] at ./examples/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_pii.pii
            changed from `true` to `false`""" in output

    def test_classification_updated(self, output):
        assert r"""error   [field_classification_updated] at 
./examples/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_classification.classification
            changed from `sensitive` to `restricted`""" in output

    def test_pattern_updated(self, output):
        assert r"""error   [field_pattern_updated] at 
./examples/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_pattern.pattern
            changed from `^[A-Za-z0-9]{8,14}$` to `^[A-Za-z0-9]$`""" in output

    def test_min_length_updated(self, output):
        assert r"""error   [field_min_length_updated] at 
./examples/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_minLength.minLength
            changed from `8` to `10`""" in output

    def test_max_length_updated(self, output):
        assert r"""error   [field_max_length_updated] at 
./examples/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_maxLength.maxLength
            changed from `14` to `20`""" in output

    def test_minimum_updated(self, output):
        assert r"""error   [field_minimum_updated] at 
./examples/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_minimum.minimum
            changed from `8` to `10`""" in output

    def test_minimum_exclusive_updated(self, output):
        assert r"""error   [field_exclusive_minimum_updated] at 
./examples/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_exclusiveMinimum.exclusiveMinimum
            changed from `8` to `10`""" in output

    def test_maximum_updated(self, output):
        assert r"""error   [field_maximum_updated] at 
./examples/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_maximum.maximum
            changed from `14` to `20`""" in output

    def test_maximum_exclusive_updated(self, output):
        assert r"""error   [field_exclusive_maximum_updated] at 
./examples/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_exclusiveMaximum.exclusiveMaximum
            changed from `14` to `20`""" in output

    def test_enum_updated(self, output):
        assert r"""error   [field_enum_updated] at ./examples/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_enum.enum
            changed from `['one']` to `['one', 'two']`""" in output

    def test_ref_updated(self, output):
        assert r"""warning [field_ref_updated] at ./examples/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_ref.$ref
            changed from `#/definitions/my_definition` to 
`#/definitions/my_definition_2`""" in output

    def test_tags_updated(self, output):
        assert """info    [field_tags_updated] at ./examples/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_tags.tags
            changed from `['one']` to `['one', 'two']`""" in output

    def test_nested_type_updated(self, output):
        assert r"""error   [field_type_updated] at ./examples/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_fields.fields.nested_field_1.type
            changed from `string` to `integer`""" in output


class TestDefinitionAdded:

    @pytest.fixture(scope='class')
    def result(self):
        result = runner.invoke(app, ["changelog", "./examples/breaking/datacontract-definitions-v1.yaml",
                                     "./examples/breaking/datacontract-definitions-v2.yaml"])
        return result

    @pytest.fixture(scope='class')
    def output(self, result):
        return result.stdout

    def test_exit_code(self, result):
        assert result.exit_code == 0

    def test_headline(self, output):
        assert "15 changes: 0 error, 13 warning, 2 info\n" in output

    def test_ref_added(self, output):
        assert r"""warning [field_ref_added] at 
./examples/breaking/datacontract-definitions-v2.yaml
        in models.my_table.fields.my_field.$ref
            added with value: `#/definitions/my_definition`""" in output

    def test_type_added(self, output):
        assert r"""warning [field_type_added] at 
./examples/breaking/datacontract-definitions-v2.yaml
        in models.my_table.fields.my_field.type
            added with value: `string`""" in output

    def test_description_added(self, output):
        assert """info    [field_description_added] at 
./examples/breaking/datacontract-definitions-v2.yaml
        in models.my_table.fields.my_field.description
            added with value: `My Description`""" in output

    def test_format_added(self, output):
        assert r"""warning [field_format_added] at 
./examples/breaking/datacontract-definitions-v2.yaml
        in models.my_table.fields.my_field.format
            added with value: `uuid`""" in output

    def test_pii_added(self, output):
        assert r"""warning [field_pii_added] at 
./examples/breaking/datacontract-definitions-v2.yaml
        in models.my_table.fields.my_field.pii
            added with value: `false`""" in output

    def test_classification_added(self, output):
        assert r"""warning [field_classification_added] at 
./examples/breaking/datacontract-definitions-v2.yaml
        in models.my_table.fields.my_field.classification
            added with value: `internal`""" in output

    def test_pattern_added(self, output):
        assert r"""warning [field_pattern_added] at 
./examples/breaking/datacontract-definitions-v2.yaml
        in models.my_table.fields.my_field.pattern
            added with value: `.*`""" in output

    def test_min_length_added(self, output):
        assert r"""warning [field_min_length_added] at 
./examples/breaking/datacontract-definitions-v2.yaml
        in models.my_table.fields.my_field.minLength
            added with value: `8`""" in output

    def test_max_length_added(self, output):
        assert r"""warning [field_max_length_added] at 
./examples/breaking/datacontract-definitions-v2.yaml
        in models.my_table.fields.my_field.maxLength
            added with value: `14`""" in output

    def test_minimum_added(self, output):
        assert r"""warning [field_minimum_added] at 
./examples/breaking/datacontract-definitions-v2.yaml
        in models.my_table.fields.my_field.minimum
            added with value: `8`""" in output

    def test_minimum_exclusive_added(self, output):
        assert r"""warning [field_exclusive_minimum_added] at 
./examples/breaking/datacontract-definitions-v2.yaml
        in models.my_table.fields.my_field.exclusiveMinimum
            added with value: `14`""" in output

    def test_maximum_added(self, output):
        assert r"""warning [field_maximum_added] at 
./examples/breaking/datacontract-definitions-v2.yaml
        in models.my_table.fields.my_field.maximum
            added with value: `14`""" in output

    def test_maximum_exclusive_added(self, output):
        assert r"""warning [field_exclusive_maximum_added] at 
./examples/breaking/datacontract-definitions-v2.yaml
        in models.my_table.fields.my_field.exclusiveMaximum
            added with value: `8`""" in output

    def test_tags_added(self, output):
        assert """info    [field_tags_added] at 
./examples/breaking/datacontract-definitions-v2.yaml
        in models.my_table.fields.my_field.tags
            added with value: `['my_tags']`""" in output

    def test_enum_added(self, output):
        assert r"""warning [field_enum_added] at 
./examples/breaking/datacontract-definitions-v2.yaml
        in models.my_table.fields.my_field.enum
            added with value: `['my_enum']`""" in output


class TestDefinitionRemoved:

    @pytest.fixture(scope='class')
    def result(self):
        result = runner.invoke(app, ["changelog", "./examples/breaking/datacontract-definitions-v2.yaml",
                                     "./examples/breaking/datacontract-definitions-v1.yaml"])
        return result

    @pytest.fixture(scope='class')
    def output(self, result):
        return result.stdout

    def test_exit_code(self, result):
        assert result.exit_code == 0

    def test_headline(self, output):
        assert "15 changes: 3 error, 9 warning, 3 info\n" in output

    def test_ref_removed(self, output):
        assert r"""warning [field_ref_removed] at 
./examples/breaking/datacontract-definitions-v1.yaml
        in models.my_table.fields.my_field.$ref
            removed field property""" in output

    def test_type_removed(self, output):
        assert r"""warning [field_type_removed] at 
./examples/breaking/datacontract-definitions-v1.yaml
        in models.my_table.fields.my_field.type
            removed field property""" in output

    def test_description_removed(self, output):
        assert """info    [field_description_removed] at 
./examples/breaking/datacontract-definitions-v1.yaml
        in models.my_table.fields.my_field.description
            removed field property""" in output

    def test_format_removed(self, output):
        assert r"""warning [field_format_removed] at 
./examples/breaking/datacontract-definitions-v1.yaml
        in models.my_table.fields.my_field.format
            removed field property""" in output

    def test_pii_removed(self, output):
        assert r"""error   [field_pii_removed] at 
./examples/breaking/datacontract-definitions-v1.yaml
        in models.my_table.fields.my_field.pii
            removed field property""" in output

    def test_classification_removed(self, output):
        assert r"""error   [field_classification_removed] at 
./examples/breaking/datacontract-definitions-v1.yaml
        in models.my_table.fields.my_field.classification
            removed field property""" in output

    def test_pattern_removed(self, output):
        assert r"""error   [field_pattern_removed] at 
./examples/breaking/datacontract-definitions-v1.yaml
        in models.my_table.fields.my_field.pattern
            removed field property""" in output

    def test_min_length_removed(self, output):
        assert r"""warning [field_min_length_removed] at 
./examples/breaking/datacontract-definitions-v1.yaml
        in models.my_table.fields.my_field.minLength
            removed field property""" in output

    def test_max_length_removed(self, output):
        assert r"""warning [field_max_length_removed] at 
./examples/breaking/datacontract-definitions-v1.yaml
        in models.my_table.fields.my_field.maxLength
            removed field property""" in output

    def test_minimum_removed(self, output):
        assert r"""warning [field_minimum_removed] at 
./examples/breaking/datacontract-definitions-v1.yaml
        in models.my_table.fields.my_field.minimum
            removed field property""" in output

    def test_minimum_exclusive_removed(self, output):
        assert r"""warning [field_exclusive_minimum_removed] at 
./examples/breaking/datacontract-definitions-v1.yaml
        in models.my_table.fields.my_field.exclusiveMinimum
            removed field property""" in output

    def test_maximum_removed(self, output):
        assert r"""warning [field_maximum_removed] at 
./examples/breaking/datacontract-definitions-v1.yaml
        in models.my_table.fields.my_field.maximum
            removed field property""" in output

    def test_maximum_exclusive_removed(self, output):
        assert r"""warning [field_exclusive_maximum_removed] at 
./examples/breaking/datacontract-definitions-v1.yaml
        in models.my_table.fields.my_field.exclusiveMaximum
            removed field property""" in output

    def test_tags_removed(self, output):
        assert """info    [field_tags_removed] at 
./examples/breaking/datacontract-definitions-v1.yaml
        in models.my_table.fields.my_field.tags
            removed field property""" in output

    def test_enum_removed(self, output):
        assert """info    [field_enum_removed] at 
./examples/breaking/datacontract-definitions-v1.yaml
        in models.my_table.fields.my_field.enum
            removed field property""" in output


class TestDefinitionUpdated:

    @pytest.fixture(scope='class')
    def result(self):
        result = runner.invoke(app, ["changelog", "./examples/breaking/datacontract-definitions-v2.yaml",
                                     "./examples/breaking/datacontract-definitions-v3.yaml"])
        return result

    @pytest.fixture(scope='class')
    def output(self, result):
        return result.stdout

    def test_exit_code(self, result):
        assert result.exit_code == 0

    def test_headline(self, output):
        assert "15 changes: 12 error, 1 warning, 2 info\n" in output

    def test_ref_updated(self, output):
        assert r"""warning [field_ref_updated] at 
./examples/breaking/datacontract-definitions-v3.yaml
        in models.my_table.fields.my_field.$ref
            changed from `#/definitions/my_definition` to 
`#/definitions/my_definition_2`""" in output

    def test_type_updated(self, output):
        assert r"""error   [field_type_updated] at 
./examples/breaking/datacontract-definitions-v3.yaml
        in models.my_table.fields.my_field.type
            changed from `string` to `integer`""" in output

    def test_description_updated(self, output):
        assert """info    [field_description_updated] at 
./examples/breaking/datacontract-definitions-v3.yaml
        in models.my_table.fields.my_field.description
            changed from `My Description` to `My Description 2`""" in output

    def test_format_updated(self, output):
        assert r"""error   [field_format_updated] at 
./examples/breaking/datacontract-definitions-v3.yaml
        in models.my_table.fields.my_field.format
            changed from `uuid` to `url`""" in output

    def test_pii_updated(self, output):
        assert r"""error   [field_pii_updated] at 
./examples/breaking/datacontract-definitions-v3.yaml
        in models.my_table.fields.my_field.pii
            changed from `false` to `true`""" in output

    def test_classification_updated(self, output):
        assert r"""error   [field_classification_updated] at 
./examples/breaking/datacontract-definitions-v3.yaml
        in models.my_table.fields.my_field.classification
            changed from `internal` to `sensitive`""" in output

    def test_pattern_updated(self, output):
        assert r"""error   [field_pattern_updated] at 
./examples/breaking/datacontract-definitions-v3.yaml
        in models.my_table.fields.my_field.pattern
            changed from `.*` to `.*.*`""" in output

    def test_min_length_updated(self, output):
        assert r"""error   [field_min_length_updated] at 
./examples/breaking/datacontract-definitions-v3.yaml
        in models.my_table.fields.my_field.minLength
            changed from `8` to `10`""" in output

    def test_max_length_updated(self, output):
        assert r"""error   [field_max_length_updated] at 
./examples/breaking/datacontract-definitions-v3.yaml
        in models.my_table.fields.my_field.maxLength
            changed from `14` to `20`""" in output

    def test_minimum_updated(self, output):
        assert r"""error   [field_minimum_updated] at 
./examples/breaking/datacontract-definitions-v3.yaml
        in models.my_table.fields.my_field.minimum
            changed from `8` to `10`""" in output

    def test_minimum_exclusive_updated(self, output):
        assert r"""error   [field_exclusive_minimum_updated] at 
./examples/breaking/datacontract-definitions-v3.yaml
        in models.my_table.fields.my_field.exclusiveMinimum
            changed from `14` to `10`""" in output

    def test_maximum_updated(self, output):
        assert r"""error   [field_maximum_updated] at 
./examples/breaking/datacontract-definitions-v3.yaml
        in models.my_table.fields.my_field.maximum
            changed from `14` to `20`""" in output

    def test_maximum_exclusive_updated(self, output):
        assert r"""error   [field_exclusive_maximum_updated] at 
./examples/breaking/datacontract-definitions-v3.yaml
        in models.my_table.fields.my_field.exclusiveMaximum
            changed from `8` to `20`""" in output

    def test_tags_updated(self, output):
        assert """info    [field_tags_updated] at 
./examples/breaking/datacontract-definitions-v3.yaml
        in models.my_table.fields.my_field.tags
            changed from `['my_tags']` to `['my_tags_2']`""" in output

    def test_enum_updated(self, output):
        assert """error   [field_enum_updated] at 
./examples/breaking/datacontract-definitions-v3.yaml
        in models.my_table.fields.my_field.enum
            changed from `['my_enum']` to `['my_enum_2']`""" in output
