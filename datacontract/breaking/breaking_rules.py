class BreakingRules:
    # model rules
    model_added = 'info'
    model_removed = 'error'

    model_description_added = 'info'
    model_description_removed = 'info'
    model_description_updated = 'info'

    model_type_updated = 'error'

    # field rules
    field_added = 'info'
    field_removed = 'error'

    field_ref_added = 'warning'
    field_ref_removed = 'warning'
    field_ref_updated = 'warning'

    field_type_added = 'warning'
    field_type_removed = 'warning'
    field_type_updated = 'error'

    field_format_added = 'warning'
    field_format_removed = 'warning'
    field_format_updated = 'error'

    field_required_updated = 'error'

    field_primary_updated = 'warning'

    field_references_added = 'warning'
    field_references_removed = 'warning'
    field_references_updated = 'warning'

    field_unique_updated = 'error'

    field_description_added = 'info'
    field_description_removed = 'info'
    field_description_updated = 'info'

    field_pii_added = 'warning'
    field_pii_removed = 'error'
    field_pii_updated = 'error'

    field_classification_added = 'warning'
    field_classification_removed = 'error'
    field_classification_updated = 'error'

    field_pattern_added = 'warning'
    field_pattern_removed = 'error'
    field_pattern_updated = 'error'

    field_min_length_added = 'warning'
    field_min_length_removed = 'warning'
    field_min_length_updated = 'error'

    field_max_length_added = 'warning'
    field_max_length_removed = 'warning'
    field_max_length_updated = 'error'

    field_minimum_added = 'warning'
    field_minimum_removed = 'warning'
    field_minimum_updated = 'error'

    field_exclusive_minimum_added = 'warning'
    field_exclusive_minimum_removed = 'warning'
    field_exclusive_minimum_updated = 'error'

    field_maximum_added = 'warning'
    field_maximum_removed = 'warning'
    field_maximum_updated = 'error'

    field_exclusive_maximum_added = 'warning'
    field_exclusive_maximum_removed = 'warning'
    field_exclusive_maximum_updated = 'error'

    field_enum_added = 'warning'
    field_enum_removed = 'info'
    field_enum_updated = 'error'

    field_tags_added = 'info'
    field_tags_removed = 'info'
    field_tags_updated = 'info'

    # quality Rules
    quality_added = 'info'
    quality_removed = 'warning'

    quality_type_updated = 'warning'
    quality_specification_updated = 'warning'
