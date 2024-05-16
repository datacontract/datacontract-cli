from datacontract.model.breaking_change import Severity


class BreakingRules:
    # model rules
    model_added = Severity.INFO
    model_removed = Severity.ERROR

    model_description_added = Severity.INFO
    model_description_removed = Severity.INFO
    model_description_updated = Severity.INFO

    model_type_updated = Severity.ERROR

    # field rules
    field_added = Severity.INFO
    field_removed = Severity.ERROR

    field_ref_added = Severity.WARNING
    field_ref_removed = Severity.WARNING
    field_ref_updated = Severity.WARNING

    field_title_added = Severity.INFO
    field_title_removed = Severity.INFO
    field_title_updated = Severity.INFO

    field_type_added = Severity.WARNING
    field_type_removed = Severity.WARNING
    field_type_updated = Severity.ERROR

    field_format_added = Severity.WARNING
    field_format_removed = Severity.WARNING
    field_format_updated = Severity.ERROR

    field_required_updated = Severity.ERROR

    field_primary_updated = Severity.WARNING

    field_references_added = Severity.WARNING
    field_references_removed = Severity.WARNING
    field_references_updated = Severity.WARNING

    field_unique_updated = Severity.ERROR

    field_description_added = Severity.INFO
    field_description_removed = Severity.INFO
    field_description_updated = Severity.INFO

    field_pii_added = Severity.WARNING
    field_pii_removed = Severity.ERROR
    field_pii_updated = Severity.ERROR

    field_classification_added = Severity.WARNING
    field_classification_removed = Severity.ERROR
    field_classification_updated = Severity.ERROR

    field_pattern_added = Severity.WARNING
    field_pattern_removed = Severity.ERROR
    field_pattern_updated = Severity.ERROR

    field_min_length_added = Severity.WARNING
    field_min_length_removed = Severity.WARNING
    field_min_length_updated = Severity.ERROR

    field_max_length_added = Severity.WARNING
    field_max_length_removed = Severity.WARNING
    field_max_length_updated = Severity.ERROR

    field_minimum_added = Severity.WARNING
    field_minimum_removed = Severity.WARNING
    field_minimum_updated = Severity.ERROR

    field_exclusive_minimum_added = Severity.WARNING
    field_exclusive_minimum_removed = Severity.WARNING
    field_exclusive_minimum_updated = Severity.ERROR

    field_maximum_added = Severity.WARNING
    field_maximum_removed = Severity.WARNING
    field_maximum_updated = Severity.ERROR

    field_exclusive_maximum_added = Severity.WARNING
    field_exclusive_maximum_removed = Severity.WARNING
    field_exclusive_maximum_updated = Severity.ERROR

    field_enum_added = Severity.WARNING
    field_enum_removed = Severity.INFO
    field_enum_updated = Severity.ERROR

    field_tags_added = Severity.INFO
    field_tags_removed = Severity.INFO
    field_tags_updated = Severity.INFO

    field_example_added = Severity.INFO
    field_example_updated = Severity.INFO
    field_example_removed = Severity.INFO

    # quality Rules
    quality_added = Severity.INFO
    quality_removed = Severity.WARNING

    quality_type_updated = Severity.WARNING
    quality_specification_updated = Severity.WARNING
