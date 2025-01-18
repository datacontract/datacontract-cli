from typer.testing import CliRunner

from datacontract.cli import app

runner = CliRunner()

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_no_changes():
    result = runner.invoke(
        app,
        [
            "changelog",
            "./fixtures/breaking/datacontract-fields-v2.yaml",
            "./fixtures/breaking/datacontract-fields-v2.yaml",
        ],
    )
    assert result.exit_code == 0
    assert "0 changes: 0 error, 0 warning, 0 info\n" in result.stdout


def test_quality_added():
    result = runner.invoke(
        app,
        [
            "changelog",
            "./fixtures/breaking/datacontract-quality-v1.yaml",
            "./fixtures/breaking/datacontract-quality-v2.yaml",
        ],
    )
    output = result.stdout
    assert result.exit_code == 0
    assert "1 changes: 0 error, 0 warning, 1 info\n" in output
    assert (
        r"""info    [quality_added] at ./fixtures/breaking/datacontract-quality-v2.yaml
        in quality
            added quality"""
        in output
    )


def test_quality_removed():
    result = runner.invoke(
        app,
        [
            "changelog",
            "./fixtures/breaking/datacontract-quality-v2.yaml",
            "./fixtures/breaking/datacontract-quality-v1.yaml",
        ],
    )
    output = result.stdout
    assert result.exit_code == 0
    assert "1 changes: 0 error, 1 warning, 0 info\n" in output
    assert (
        r"""warning [quality_removed] at ./fixtures/breaking/datacontract-quality-v1.yaml
        in quality
            removed quality"""
        in output
    )


def test_quality_updated():
    result = runner.invoke(
        app,
        [
            "changelog",
            "./fixtures/breaking/datacontract-quality-v2.yaml",
            "./fixtures/breaking/datacontract-quality-v3.yaml",
        ],
    )
    output = result.stdout
    assert result.exit_code == 0
    assert "2 changes: 0 error, 2 warning, 0 info\n" in output
    assert (
        r"""warning [quality_type_updated] at 
./fixtures/breaking/datacontract-quality-v3.yaml
        in quality.type
            changed from `SodaCL` to `custom`"""
        in output
    )
    assert (
        r"""warning [quality_specification_updated] at 
./fixtures/breaking/datacontract-quality-v3.yaml
        in quality.specification
            changed from `checks for orders:
  - freshness(column_1) < 1d` to `checks for orders:
  - freshness(column_1) < 2d`"""
        in output
    )


def test_models_added():
    result = runner.invoke(
        app,
        [
            "changelog",
            "./fixtures/breaking/datacontract-models-v1.yaml",
            "./fixtures/breaking/datacontract-models-v2.yaml",
        ],
    )
    output = result.stdout
    assert result.exit_code == 0
    assert "4 changes: 0 error, 0 warning, 4 info\n" in output
    assert (
        """info    [model_added] at ./fixtures/breaking/datacontract-models-v2.yaml
        in models.my_table_2
            added the model"""
        in output
    )
    assert (
        """info    [model_description_added] at 
./fixtures/breaking/datacontract-models-v2.yaml
        in models.my_table.description
            added with value: `My Model Description`"""
        in output
    )

    assert (
        """info    [model_another-key_added] at 
./fixtures/breaking/datacontract-models-v2.yaml
        in models.my_table.another-key
            added with value: `original value`"""
        in output
    )


def test_models_removed():
    result = runner.invoke(
        app,
        [
            "changelog",
            "./fixtures/breaking/datacontract-models-v2.yaml",
            "./fixtures/breaking/datacontract-models-v1.yaml",
        ],
    )
    output = result.stdout
    assert result.exit_code == 0
    assert "4 changes: 1 error, 0 warning, 3 info\n" in output
    assert (
        r"""error   [model_removed] at ./fixtures/breaking/datacontract-models-v1.yaml
        in models.my_table_2
            removed the model"""
        in output
    )
    assert (
        """info    [model_description_removed] at 
./fixtures/breaking/datacontract-models-v1.yaml
        in models.my_table.description
            removed model property"""
        in output
    )
    assert (
        """info    [model_another-key_removed] at 
./fixtures/breaking/datacontract-models-v1.yaml
        in models.my_table.another-key
            removed model property"""
        in output
    )


def test_models_updated():
    result = runner.invoke(
        app,
        [
            "changelog",
            "./fixtures/breaking/datacontract-models-v2.yaml",
            "./fixtures/breaking/datacontract-models-v3.yaml",
        ],
    )
    output = result.stdout
    assert result.exit_code == 0
    assert "4 changes: 1 error, 0 warning, 3 info\n" in output
    assert (
        r"""error   [model_type_updated] at ./fixtures/breaking/datacontract-models-v3.yaml
        in models.my_table.type
            changed from `table` to `object`"""
        in output
    )
    assert (
        """info    [model_description_updated] at 
./fixtures/breaking/datacontract-models-v3.yaml
        in models.my_table.description
            changed from `My Model Description` to `My Updated Model 
Description`"""
        in output
    )

    assert (
        """info    [model_another-key_updated] at 
./fixtures/breaking/datacontract-models-v3.yaml
        in models.my_table.another-key
            changed from `original value` to `updated value`"""
        in output
    )

    assert (
        """info    [model_some-other-key_removed] at 
./fixtures/breaking/datacontract-models-v3.yaml
        in models.my_table_2.some-other-key
            removed model property"""
        in output
    )


def test_fields_added():
    result = runner.invoke(
        app,
        [
            "changelog",
            "./fixtures/breaking/datacontract-fields-v1.yaml",
            "./fixtures/breaking/datacontract-fields-v2.yaml",
        ],
    )
    assert result.exit_code == 0
    output = result.stdout
    assert "22 changes: 0 error, 15 warning, 7 info\n" in output
    assert (
        """info    [field_added] at ./fixtures/breaking/datacontract-fields-v2.yaml
        in models.my_table.fields.new_field
            added the field"""
        in output
    )
    assert (
        """warning [field_references_added] at 
./fixtures/breaking/datacontract-fields-v2.yaml
        in models.my_table.fields.field_references.references
            added with value: `my_table.field_type`"""
        in output
    )
    assert (
        r"""warning [field_type_added] at ./fixtures/breaking/datacontract-fields-v2.yaml
        in models.my_table.fields.field_type.type
            added with value: `string`"""
        in output
    )
    assert (
        r"""warning [field_format_added] at ./fixtures/breaking/datacontract-fields-v2.yaml
        in models.my_table.fields.field_format.format
            added with value: `email`"""
        in output
    )
    assert (
        """info    [field_description_added] at 
./fixtures/breaking/datacontract-fields-v2.yaml
        in models.my_table.fields.field_description.description
            added with value: `My Description`"""
        in output
    )
    assert (
        r"""warning [field_pii_added] at ./fixtures/breaking/datacontract-fields-v2.yaml
        in models.my_table.fields.field_pii.pii
            added with value: `true`"""
        in output
    )
    assert (
        r"""warning [field_classification_added] at 
./fixtures/breaking/datacontract-fields-v2.yaml
        in models.my_table.fields.field_classification.classification
            added with value: `sensitive`"""
        in output
    )
    assert (
        r"""warning [field_pattern_added] at ./fixtures/breaking/datacontract-fields-v2.yaml
        in models.my_table.fields.field_pattern.pattern
            added with value: `^[A-Za-z0-9]{8,14}$`"""
        in output
    )
    assert (
        r"""warning [field_min_length_added] at 
./fixtures/breaking/datacontract-fields-v2.yaml
        in models.my_table.fields.field_minLength.minLength
            added with value: `8`"""
        in output
    )
    assert (
        r"""warning [field_max_length_added] at 
./fixtures/breaking/datacontract-fields-v2.yaml
        in models.my_table.fields.field_maxLength.maxLength
            added with value: `14`"""
        in output
    )
    assert (
        r"""warning [field_minimum_added] at ./fixtures/breaking/datacontract-fields-v2.yaml
        in models.my_table.fields.field_minimum.minimum
            added with value: `8`"""
        in output
    )
    assert (
        r"""warning [field_exclusive_minimum_added] at 
./fixtures/breaking/datacontract-fields-v2.yaml
        in models.my_table.fields.field_exclusiveMinimum.exclusiveMinimum
            added with value: `8`"""
        in output
    )
    assert (
        r"""warning [field_maximum_added] at ./fixtures/breaking/datacontract-fields-v2.yaml
        in models.my_table.fields.field_maximum.maximum
            added with value: `14`"""
        in output
    )
    assert (
        r"""warning [field_exclusive_maximum_added] at 
./fixtures/breaking/datacontract-fields-v2.yaml
        in models.my_table.fields.field_exclusiveMaximum.exclusiveMaximum
            added with value: `14`"""
        in output
    )
    assert (
        r"""warning [field_enum_added] at ./fixtures/breaking/datacontract-fields-v2.yaml
        in models.my_table.fields.field_enum.enum
            added with value: `['one']`"""
        in output
    )
    assert (
        """info    [field_tags_added] at ./fixtures/breaking/datacontract-fields-v2.yaml
        in models.my_table.fields.field_tags.tags
            added with value: `['one']`"""
        in output
    )

    assert (
        r"""warning [field_ref_added] at ./fixtures/breaking/datacontract-fields-v2.yaml
        in models.my_table.fields.field_ref.$ref
            added with value: `#/definitions/my_definition`"""
        in output
    )

    assert (
        """info    [field_added] at ./fixtures/breaking/datacontract-fields-v2.yaml
        in models.my_table.fields.field_fields.fields.new_nested_field
            added the field"""
        in output
    )

    assert (
        """info    [field_custom_key_added] at 
./fixtures/breaking/datacontract-fields-v2.yaml
        in models.my_table.fields.field_custom_key.custom-key
            added with value: `some value`"""
        in output
    )


def test_fields_removed():
    result = runner.invoke(
        app,
        [
            "changelog",
            "./fixtures/breaking/datacontract-fields-v2.yaml",
            "./fixtures/breaking/datacontract-fields-v1.yaml",
        ],
    )
    output = result.stdout
    assert result.exit_code == 0
    assert "22 changes: 5 error, 11 warning, 6 info\n" in output
    assert (
        r"""warning [field_type_removed] at ./fixtures/breaking/datacontract-fields-v1.yaml
        in models.my_table.fields.field_type.type
            removed field property"""
        in output
    )
    assert (
        r"""warning [field_format_removed] at 
./fixtures/breaking/datacontract-fields-v1.yaml
        in models.my_table.fields.field_format.format
            removed field property"""
        in output
    )
    assert (
        """warning [field_references_removed] at 
./fixtures/breaking/datacontract-fields-v1.yaml
        in models.my_table.fields.field_references.references
            removed field property"""
        in output
    )
    assert (
        """info    [field_description_removed] at 
./fixtures/breaking/datacontract-fields-v1.yaml
        in models.my_table.fields.field_description.description
            removed field property"""
        in output
    )
    assert (
        r"""error   [field_pii_removed] at ./fixtures/breaking/datacontract-fields-v1.yaml
        in models.my_table.fields.field_pii.pii
            removed field property"""
        in output
    )
    assert (
        r"""error   [field_classification_removed] at 
./fixtures/breaking/datacontract-fields-v1.yaml
        in models.my_table.fields.field_classification.classification
            removed field property"""
        in output
    )
    assert (
        r"""error   [field_pattern_removed] at 
./fixtures/breaking/datacontract-fields-v1.yaml
        in models.my_table.fields.field_pattern.pattern
            removed field property"""
        in output
    )
    assert (
        r"""warning [field_min_length_removed] at 
./fixtures/breaking/datacontract-fields-v1.yaml
        in models.my_table.fields.field_minLength.minLength
            removed field property"""
        in output
    )
    assert (
        r"""warning [field_max_length_removed] at 
./fixtures/breaking/datacontract-fields-v1.yaml
        in models.my_table.fields.field_maxLength.maxLength
            removed field property"""
        in output
    )
    assert (
        r"""warning [field_minimum_removed] at 
./fixtures/breaking/datacontract-fields-v1.yaml
        in models.my_table.fields.field_minimum.minimum
            removed field property"""
        in output
    )
    assert (
        r"""warning [field_exclusive_minimum_removed] at 
./fixtures/breaking/datacontract-fields-v1.yaml
        in models.my_table.fields.field_exclusiveMinimum.exclusiveMinimum
            removed field property"""
        in output
    )
    assert (
        r"""warning [field_maximum_removed] at 
./fixtures/breaking/datacontract-fields-v1.yaml
        in models.my_table.fields.field_maximum.maximum
            removed field property"""
        in output
    )
    assert (
        r"""warning [field_exclusive_maximum_removed] at 
./fixtures/breaking/datacontract-fields-v1.yaml
        in models.my_table.fields.field_exclusiveMaximum.exclusiveMaximum
            removed field property"""
        in output
    )
    assert (
        r"""warning [field_ref_removed] at ./fixtures/breaking/datacontract-fields-v1.yaml
        in models.my_table.fields.field_ref.$ref
            removed field property"""
        in output
    )
    assert (
        """info    [field_enum_removed] at ./fixtures/breaking/datacontract-fields-v1.yaml
        in models.my_table.fields.field_enum.enum
            removed field property"""
        in output
    )
    assert (
        """info    [field_tags_removed] at ./fixtures/breaking/datacontract-fields-v1.yaml
        in models.my_table.fields.field_tags.tags
            removed field property"""
        in output
    )
    assert (
        r"""error   [field_removed] at ./fixtures/breaking/datacontract-fields-v1.yaml
        in models.my_table.fields.field_fields.fields.new_nested_field
            removed the field"""
        in output
    )
    assert (
        r"""error   [field_removed] at ./fixtures/breaking/datacontract-fields-v1.yaml
        in models.my_table.fields.new_field
            removed the field"""
        in output
    )

    assert (
        """info    [field_custom_key_removed] at 
./fixtures/breaking/datacontract-fields-v1.yaml
        in models.my_table.fields.field_custom_key.custom-key
            removed field property"""
        in output
    )


def test_fields_updated():
    result = runner.invoke(
        app,
        [
            "changelog",
            "./fixtures/breaking/datacontract-fields-v2.yaml",
            "./fixtures/breaking/datacontract-fields-v3.yaml",
        ],
    )
    output = result.stdout
    assert result.exit_code == 0
    assert "21 changes: 15 error, 3 warning, 3 info\n" in output
    assert (
        r"""error   [field_type_updated] at ./fixtures/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_type.type
            changed from `string` to `integer`"""
        in output
    )
    assert (
        """error   [field_format_updated] at 
./fixtures/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_format.format
            changed from `email` to `url`"""
        in output
    )
    assert (
        """error   [field_required_updated] at 
./fixtures/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_required.required
            changed from `false` to `true`"""
        in output
    )
    assert (
        """warning [field_primary_key_updated] at 
./fixtures/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_primaryKey.primaryKey
            changed from `false` to `true`"""
        in output
    )
    assert (
        """warning [field_references_updated] at 
./fixtures/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_references.references
            changed from `my_table.field_type` to `my_table.field_format`"""
        in output
    )
    assert (
        r"""error   [field_unique_updated] at 
./fixtures/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_unique.unique
            changed from `false` to `true`"""
        in output
    )
    assert (
        """info    [field_description_updated] at 
./fixtures/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_description.description
            changed from `My Description` to `My updated Description`"""
        in output
    )
    assert (
        r"""error   [field_pii_updated] at ./fixtures/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_pii.pii
            changed from `true` to `false`"""
        in output
    )
    assert (
        r"""error   [field_classification_updated] at 
./fixtures/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_classification.classification
            changed from `sensitive` to `restricted`"""
        in output
    )
    assert (
        r"""error   [field_pattern_updated] at 
./fixtures/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_pattern.pattern
            changed from `^[A-Za-z0-9]{8,14}$` to `^[A-Za-z0-9]$`"""
        in output
    )
    assert (
        r"""error   [field_min_length_updated] at 
./fixtures/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_minLength.minLength
            changed from `8` to `10`"""
        in output
    )
    assert (
        r"""error   [field_max_length_updated] at 
./fixtures/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_maxLength.maxLength
            changed from `14` to `20`"""
        in output
    )
    assert (
        r"""error   [field_minimum_updated] at 
./fixtures/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_minimum.minimum
            changed from `8` to `10`"""
        in output
    )
    assert (
        r"""error   [field_exclusive_minimum_updated] at 
./fixtures/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_exclusiveMinimum.exclusiveMinimum
            changed from `8` to `10`"""
        in output
    )
    assert (
        r"""error   [field_maximum_updated] at 
./fixtures/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_maximum.maximum
            changed from `14` to `20`"""
        in output
    )
    assert (
        r"""error   [field_exclusive_maximum_updated] at 
./fixtures/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_exclusiveMaximum.exclusiveMaximum
            changed from `14` to `20`"""
        in output
    )
    assert (
        r"""error   [field_enum_updated] at ./fixtures/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_enum.enum
            changed from `['one']` to `['one', 'two']`"""
        in output
    )
    assert (
        r"""warning [field_ref_updated] at ./fixtures/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_ref.$ref
            changed from `#/definitions/my_definition` to 
`#/definitions/my_definition_2`"""
        in output
    )
    assert (
        """info    [field_tags_updated] at ./fixtures/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_tags.tags
            changed from `['one']` to `['one', 'two']`"""
        in output
    )
    assert (
        r"""error   [field_type_updated] at ./fixtures/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_fields.fields.nested_field_1.type
            changed from `string` to `integer`"""
        in output
    )
    assert (
        r"""info    [field_custom_key_updated] at 
./fixtures/breaking/datacontract-fields-v3.yaml
        in models.my_table.fields.field_custom_key.custom-key
            changed from `some value` to `some other value`"""
        in output
    )


def test_definition_added():
    result = runner.invoke(
        app,
        [
            "changelog",
            "./fixtures/breaking/datacontract-definitions-v1.yaml",
            "./fixtures/breaking/datacontract-definitions-v2.yaml",
        ],
    )
    output = result.stdout

    assert result.exit_code == 0
    assert "18 changes: 0 error, 13 warning, 5 info\n" in output
    assert (
        r"""warning [field_ref_added] at 
./fixtures/breaking/datacontract-definitions-v2.yaml
        in models.my_table.fields.my_field.$ref
            added with value: `#/definitions/my_definition`"""
        in output
    )
    assert (
        r"""warning [field_type_added] at 
./fixtures/breaking/datacontract-definitions-v2.yaml
        in models.my_table.fields.my_field.type
            added with value: `string`"""
        in output
    )
    assert (
        """info    [field_description_added] at 
./fixtures/breaking/datacontract-definitions-v2.yaml
        in models.my_table.fields.my_field.description
            added with value: `My Description`"""
        in output
    )
    assert (
        r"""warning [field_format_added] at 
./fixtures/breaking/datacontract-definitions-v2.yaml
        in models.my_table.fields.my_field.format
            added with value: `uuid`"""
        in output
    )
    assert (
        r"""warning [field_pii_added] at 
./fixtures/breaking/datacontract-definitions-v2.yaml
        in models.my_table.fields.my_field.pii
            added with value: `false`"""
        in output
    )
    assert (
        r"""warning [field_classification_added] at 
./fixtures/breaking/datacontract-definitions-v2.yaml
        in models.my_table.fields.my_field.classification
            added with value: `internal`"""
        in output
    )
    assert (
        r"""warning [field_pattern_added] at 
./fixtures/breaking/datacontract-definitions-v2.yaml
        in models.my_table.fields.my_field.pattern
            added with value: `.*`"""
        in output
    )
    assert (
        r"""warning [field_min_length_added] at 
./fixtures/breaking/datacontract-definitions-v2.yaml
        in models.my_table.fields.my_field.minLength
            added with value: `8`"""
        in output
    )
    assert (
        r"""warning [field_max_length_added] at 
./fixtures/breaking/datacontract-definitions-v2.yaml
        in models.my_table.fields.my_field.maxLength
            added with value: `14`"""
        in output
    )
    assert (
        r"""warning [field_minimum_added] at 
./fixtures/breaking/datacontract-definitions-v2.yaml
        in models.my_table.fields.my_field.minimum
            added with value: `8`"""
        in output
    )
    assert (
        r"""warning [field_exclusive_minimum_added] at 
./fixtures/breaking/datacontract-definitions-v2.yaml
        in models.my_table.fields.my_field.exclusiveMinimum
            added with value: `14`"""
        in output
    )
    assert (
        r"""warning [field_maximum_added] at 
./fixtures/breaking/datacontract-definitions-v2.yaml
        in models.my_table.fields.my_field.maximum
            added with value: `14`"""
        in output
    )
    assert (
        r"""warning [field_exclusive_maximum_added] at 
./fixtures/breaking/datacontract-definitions-v2.yaml
        in models.my_table.fields.my_field.exclusiveMaximum
            added with value: `8`"""
        in output
    )
    assert (
        """info    [field_tags_added] at 
./fixtures/breaking/datacontract-definitions-v2.yaml
        in models.my_table.fields.my_field.tags
            added with value: `['my_tags']`"""
        in output
    )
    assert (
        r"""warning [field_enum_added] at 
./fixtures/breaking/datacontract-definitions-v2.yaml
        in models.my_table.fields.my_field.enum
            added with value: `['my_enum']`"""
        in output
    )
    assert (
        """info    [field_example_added] at 
./fixtures/breaking/datacontract-definitions-v2.yaml
        in models.my_table.fields.my_field.example
            added with value: `my_example`"""
        in output
    )


def test_definition_removed():
    result = runner.invoke(
        app,
        [
            "changelog",
            "./fixtures/breaking/datacontract-definitions-v2.yaml",
            "./fixtures/breaking/datacontract-definitions-v1.yaml",
        ],
    )
    output = result.stdout

    assert result.exit_code == 0
    assert "18 changes: 3 error, 9 warning, 6 info\n" in output
    assert (
        r"""warning [field_ref_removed] at 
./fixtures/breaking/datacontract-definitions-v1.yaml
        in models.my_table.fields.my_field.$ref
            removed field property"""
        in output
    )
    assert (
        r"""warning [field_type_removed] at 
./fixtures/breaking/datacontract-definitions-v1.yaml
        in models.my_table.fields.my_field.type
            removed field property"""
        in output
    )
    assert (
        """info    [field_description_removed] at 
./fixtures/breaking/datacontract-definitions-v1.yaml
        in models.my_table.fields.my_field.description
            removed field property"""
        in output
    )
    assert (
        r"""warning [field_format_removed] at 
./fixtures/breaking/datacontract-definitions-v1.yaml
        in models.my_table.fields.my_field.format
            removed field property"""
        in output
    )
    assert (
        r"""error   [field_pii_removed] at 
./fixtures/breaking/datacontract-definitions-v1.yaml
        in models.my_table.fields.my_field.pii
            removed field property"""
        in output
    )
    assert (
        r"""error   [field_classification_removed] at 
./fixtures/breaking/datacontract-definitions-v1.yaml
        in models.my_table.fields.my_field.classification
            removed field property"""
        in output
    )
    assert (
        r"""error   [field_pattern_removed] at 
./fixtures/breaking/datacontract-definitions-v1.yaml
        in models.my_table.fields.my_field.pattern
            removed field property"""
        in output
    )
    assert (
        r"""warning [field_min_length_removed] at 
./fixtures/breaking/datacontract-definitions-v1.yaml
        in models.my_table.fields.my_field.minLength
            removed field property"""
        in output
    )
    assert (
        r"""warning [field_max_length_removed] at 
./fixtures/breaking/datacontract-definitions-v1.yaml
        in models.my_table.fields.my_field.maxLength
            removed field property"""
        in output
    )
    assert (
        r"""warning [field_minimum_removed] at 
./fixtures/breaking/datacontract-definitions-v1.yaml
        in models.my_table.fields.my_field.minimum
            removed field property"""
        in output
    )
    assert (
        r"""warning [field_exclusive_minimum_removed] at 
./fixtures/breaking/datacontract-definitions-v1.yaml
        in models.my_table.fields.my_field.exclusiveMinimum
            removed field property"""
        in output
    )
    assert (
        r"""warning [field_maximum_removed] at 
./fixtures/breaking/datacontract-definitions-v1.yaml
        in models.my_table.fields.my_field.maximum
            removed field property"""
        in output
    )
    assert (
        r"""warning [field_exclusive_maximum_removed] at 
./fixtures/breaking/datacontract-definitions-v1.yaml
        in models.my_table.fields.my_field.exclusiveMaximum
            removed field property"""
        in output
    )
    assert (
        """info    [field_tags_removed] at 
./fixtures/breaking/datacontract-definitions-v1.yaml
        in models.my_table.fields.my_field.tags
            removed field property"""
        in output
    )
    assert (
        """info    [field_enum_removed] at 
./fixtures/breaking/datacontract-definitions-v1.yaml
        in models.my_table.fields.my_field.enum
            removed field property"""
        in output
    )
    assert (
        """info    [field_example_removed] at 
./fixtures/breaking/datacontract-definitions-v1.yaml
        in models.my_table.fields.my_field.example
            removed field property"""
        in output
    )


def test_definition_updated():
    result = runner.invoke(
        app,
        [
            "changelog",
            "./fixtures/breaking/datacontract-definitions-v2.yaml",
            "./fixtures/breaking/datacontract-definitions-v3.yaml",
        ],
    )
    output = result.stdout

    assert result.exit_code == 0
    assert "17 changes: 12 error, 1 warning, 4 info\n" in output
    assert (
        r"""warning [field_ref_updated] at 
./fixtures/breaking/datacontract-definitions-v3.yaml
        in models.my_table.fields.my_field.$ref
            changed from `#/definitions/my_definition` to 
`#/definitions/my_definition_2`"""
        in output
    )
    assert (
        r"""error   [field_type_updated] at 
./fixtures/breaking/datacontract-definitions-v3.yaml
        in models.my_table.fields.my_field.type
            changed from `string` to `integer`"""
        in output
    )
    assert (
        """info    [field_description_updated] at 
./fixtures/breaking/datacontract-definitions-v3.yaml
        in models.my_table.fields.my_field.description
            changed from `My Description` to `My Description 2`"""
        in output
    )
    assert (
        r"""error   [field_format_updated] at 
./fixtures/breaking/datacontract-definitions-v3.yaml
        in models.my_table.fields.my_field.format
            changed from `uuid` to `url`"""
        in output
    )
    assert (
        r"""error   [field_pii_updated] at 
./fixtures/breaking/datacontract-definitions-v3.yaml
        in models.my_table.fields.my_field.pii
            changed from `false` to `true`"""
        in output
    )
    assert (
        r"""error   [field_classification_updated] at 
./fixtures/breaking/datacontract-definitions-v3.yaml
        in models.my_table.fields.my_field.classification
            changed from `internal` to `sensitive`"""
        in output
    )
    assert (
        r"""error   [field_pattern_updated] at 
./fixtures/breaking/datacontract-definitions-v3.yaml
        in models.my_table.fields.my_field.pattern
            changed from `.*` to `.*.*`"""
        in output
    )
    assert (
        r"""error   [field_min_length_updated] at 
./fixtures/breaking/datacontract-definitions-v3.yaml
        in models.my_table.fields.my_field.minLength
            changed from `8` to `10`"""
        in output
    )
    assert (
        r"""error   [field_max_length_updated] at 
./fixtures/breaking/datacontract-definitions-v3.yaml
        in models.my_table.fields.my_field.maxLength
            changed from `14` to `20`"""
        in output
    )
    assert (
        r"""error   [field_minimum_updated] at 
./fixtures/breaking/datacontract-definitions-v3.yaml
        in models.my_table.fields.my_field.minimum
            changed from `8` to `10`"""
        in output
    )
    assert (
        r"""error   [field_exclusive_minimum_updated] at 
./fixtures/breaking/datacontract-definitions-v3.yaml
        in models.my_table.fields.my_field.exclusiveMinimum
            changed from `14` to `10`"""
        in output
    )
    assert (
        r"""error   [field_maximum_updated] at 
./fixtures/breaking/datacontract-definitions-v3.yaml
        in models.my_table.fields.my_field.maximum
            changed from `14` to `20`"""
        in output
    )
    assert (
        r"""error   [field_exclusive_maximum_updated] at 
./fixtures/breaking/datacontract-definitions-v3.yaml
        in models.my_table.fields.my_field.exclusiveMaximum
            changed from `8` to `20`"""
        in output
    )
    assert (
        """info    [field_tags_updated] at 
./fixtures/breaking/datacontract-definitions-v3.yaml
        in models.my_table.fields.my_field.tags
            changed from `['my_tags']` to `['my_tags_2']`"""
        in output
    )
    assert (
        """error   [field_enum_updated] at 
./fixtures/breaking/datacontract-definitions-v3.yaml
        in models.my_table.fields.my_field.enum
            changed from `['my_enum']` to `['my_enum_2']`"""
        in output
    )
    assert (
        """info    [field_example_updated] at 
./fixtures/breaking/datacontract-definitions-v3.yaml
        in models.my_table.fields.my_field.example
            changed from `my_example` to `my_example_2`"""
        in output
    )


def test_info_added():
    result = runner.invoke(
        app,
        [
            "changelog",
            "./fixtures/breaking/datacontract-info-v1.yaml",
            "./fixtures/breaking/datacontract-info-v2.yaml",
        ],
    )
    output = result.stdout
    assert result.exit_code == 0
    assert "3 changes: 0 error, 0 warning, 3 info\n" in output

    assert (
        """info    [info_owner_added] at ./fixtures/breaking/datacontract-info-v2.yaml
        in info.owner
            added with value: `Data Team`"""
        in output
    )
    assert (
        """info    [info_some_other_key_added] at 
./fixtures/breaking/datacontract-info-v2.yaml
        in info.some-other-key
            added with value: `some information`"""
        in output
    )
    assert (
        """info    [contact_added] at ./fixtures/breaking/datacontract-info-v2.yaml
        in info.contact
            added contact"""
        in output
    )


def test_info_removed():
    result = runner.invoke(
        app,
        [
            "changelog",
            "./fixtures/breaking/datacontract-info-v2.yaml",
            "./fixtures/breaking/datacontract-info-v1.yaml",
        ],
    )
    output = result.stdout
    assert result.exit_code == 0
    assert "3 changes: 0 error, 0 warning, 3 info\n" in output
    assert (
        """info    [info_owner_removed] at ./fixtures/breaking/datacontract-info-v1.yaml
        in info.owner
            removed info property"""
        in output
    )
    assert (
        """info    [info_some_other_key_removed] at 
./fixtures/breaking/datacontract-info-v1.yaml
        in info.some-other-key
            removed info property"""
        in output
    )
    assert (
        """info    [contact_removed] at ./fixtures/breaking/datacontract-info-v1.yaml
        in info.contact
            removed contact"""
        in output
    )


def test_info_updated():
    result = runner.invoke(
        app,
        [
            "changelog",
            "./fixtures/breaking/datacontract-info-v2.yaml",
            "./fixtures/breaking/datacontract-info-v3.yaml",
        ],
    )
    output = result.stdout
    assert result.exit_code == 0
    assert "3 changes: 0 error, 0 warning, 3 info\n" in output

    assert (
        """info    [info_owner_updated] at ./fixtures/breaking/datacontract-info-v3.yaml
        in info.owner
            changed from `Data Team` to `Another Team`"""
        in output
    )
    assert (
        """info    [info_some_other_key_updated] at 
./fixtures/breaking/datacontract-info-v3.yaml
        in info.some-other-key
            changed from `some information` to `new information`"""
        in output
    )
    assert (
        """info    [contact_email_updated] at ./fixtures/breaking/datacontract-info-v3.yaml
        in info.contact.email
            changed from `datateam@work.com` to `anotherteam@work.com`"""
        in output
    )


def test_terms_added():
    result = runner.invoke(
        app,
        [
            "changelog",
            "./fixtures/breaking/datacontract-terms-v1.yaml",
            "./fixtures/breaking/datacontract-terms-v2.yaml",
        ],
    )
    output = result.stdout
    assert result.exit_code == 0
    assert "1 changes: 0 error, 0 warning, 1 info\n" in output

    assert (
        """info    [terms_added] at ./fixtures/breaking/datacontract-terms-v2.yaml
        in terms
            added terms"""
        in output
    )


def test_terms_removed():
    result = runner.invoke(
        app,
        [
            "changelog",
            "./fixtures/breaking/datacontract-terms-v2.yaml",
            "./fixtures/breaking/datacontract-terms-v1.yaml",
        ],
    )
    output = result.stdout
    assert result.exit_code == 0
    assert "1 changes: 0 error, 0 warning, 1 info\n" in output

    assert (
        """info    [terms_removed] at ./fixtures/breaking/datacontract-terms-v1.yaml
        in terms
            removed terms"""
        in output
    )


def test_terms_updated():
    result = runner.invoke(
        app,
        [
            "changelog",
            "./fixtures/breaking/datacontract-terms-v2.yaml",
            "./fixtures/breaking/datacontract-terms-v3.yaml",
        ],
    )
    output = result.stdout
    assert result.exit_code == 0
    assert "5 changes: 0 error, 0 warning, 5 info\n" in output

    assert (
        """info    [terms_usage_updated] at ./fixtures/breaking/datacontract-terms-v3.yaml
        in terms.usage
            changed from `Data can be used for reports, analytics and machine 
learning use cases.
Order may be linked and joined by other tables
` to `Data can be used for anything`"""
        in output
    )
    assert (
        """info    [terms_limitations_removed] at 
./fixtures/breaking/datacontract-terms-v3.yaml
        in terms.limitations
            removed info property"""
        in output
    )
    assert (
        """info    [terms_billing_updated] at 
./fixtures/breaking/datacontract-terms-v3.yaml
        in terms.billing
            changed from `5000 USD per month` to `1000000 GBP per month`"""
        in output
    )
    assert (
        """info    [terms_notice_period_updated] at 
./fixtures/breaking/datacontract-terms-v3.yaml
        in terms.noticePeriod
            changed from `P3M` to `P1Y`"""
        in output
    )
    assert (
        """info    [terms_some_other_terms_added] at 
./fixtures/breaking/datacontract-terms-v3.yaml
        in terms.someOtherTerms
            added with value: `must abide by policies`"""
        in output
    )
