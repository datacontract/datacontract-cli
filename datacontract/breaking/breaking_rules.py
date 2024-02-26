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
    field_ref_removed = 'error'

    field_type_added = 'warning'
    field_type_removed = 'warning'
    field_type_updated = 'error'

    field_format_added = 'warning'
    field_format_removed = 'warning'
    field_format_updated = 'error'

    field_required_updated = 'error'

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

    field_minLength_added = 'warning'
    field_minLength_removed = 'warning'
    field_minLength_updated = 'error'

    field_maxLength_added = 'warning'
    field_maxLength_removed = 'warning'
    field_maxLength_updated = 'error'

    field_minimum_added = 'warning'
    field_minimum_removed = 'warning'
    field_minimum_updated = 'error'

    field_minimumExclusive_added = 'warning'
    field_minimumExclusive_removed = 'warning'
    field_minimumExclusive_updated = 'error'

    field_maximum_added = 'warning'
    field_maximum_removed = 'warning'
    field_maximum_updated = 'error'

    field_maximumExclusive_added = 'warning'
    field_maximumExclusive_removed = 'warning'
    field_maximumExclusive_updated = 'error'

    field_enum_added = 'warning'
    field_enum_removed = 'info'
    field_enum_updated = 'error'

    field_tags_added = 'info'
    field_tags_removed = 'info'
    field_tags_updated = 'info'
