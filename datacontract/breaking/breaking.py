from datacontract.breaking.breaking_rules import BreakingRules
from datacontract.model.breaking_change import BreakingChange, Location, Severity
from datacontract.model.data_contract_specification import Field, Model, Quality


def quality_breaking_changes(
    old_quality: Quality,
    new_quality: Quality,
    new_path: str,
    include_severities: [Severity],
) -> list[BreakingChange]:
    results = list[BreakingChange]()

    if not old_quality and new_quality:
        rule_name = "quality_added"
        severity = _get_rule(rule_name)
        description = "added quality"

        if severity in include_severities:
            results.append(
                BreakingChange(
                    description=description,
                    check_name=rule_name,
                    severity=severity,
                    location=Location(path=new_path, composition=["quality"]),
                )
            )
    elif old_quality and not new_quality:
        rule_name = "quality_removed"
        severity = _get_rule(rule_name)
        description = "removed quality"

        if severity in include_severities:
            results.append(
                BreakingChange(
                    description=description,
                    check_name=rule_name,
                    severity=severity,
                    location=Location(path=new_path, composition=["quality"]),
                )
            )

    elif old_quality and new_quality:
        if old_quality.type != new_quality.type:
            rule_name = "quality_type_updated"
            severity = _get_rule(rule_name)
            description = f"changed from `{old_quality.type}` to `{new_quality.type}`"

            if severity in include_severities:
                results.append(
                    BreakingChange(
                        description=description,
                        check_name=rule_name,
                        severity=severity,
                        location=Location(path=new_path, composition=["quality", "type"]),
                    )
                )

        if old_quality.specification != new_quality.specification:
            rule_name = "quality_specification_updated"
            severity = _get_rule(rule_name)
            description = f"changed from `{old_quality.specification}` to `{new_quality.specification}`"
            if severity in include_severities:
                results.append(
                    BreakingChange(
                        description=description,
                        check_name=rule_name,
                        severity=severity,
                        location=Location(path=new_path, composition=["quality", "specification"]),
                    )
                )

    return results


def models_breaking_changes(
    old_models: dict[str, Model],
    new_models: dict[str, Model],
    new_path: str,
    include_severities: [Severity],
) -> list[BreakingChange]:
    composition = ["models"]
    results = list[BreakingChange]()

    for model_name, new_model in new_models.items():
        if model_name not in old_models.keys():
            rule_name = "model_added"
            severity = _get_rule(rule_name)
            if severity in include_severities:
                results.append(
                    BreakingChange(
                        description="added the model",
                        check_name=rule_name,
                        severity=severity,
                        location=Location(path=new_path, composition=composition + [model_name]),
                    )
                )

    for model_name, old_model in old_models.items():
        if model_name not in new_models.keys():
            rule_name = "model_removed"
            severity = _get_rule(rule_name)
            if severity in include_severities:
                results.append(
                    BreakingChange(
                        description="removed the model",
                        check_name=rule_name,
                        severity=severity,
                        location=Location(path=new_path, composition=composition + [model_name]),
                    )
                )
            continue

        results.extend(
            model_breaking_changes(
                old_model=old_model,
                new_model=new_models[model_name],
                new_path=new_path,
                composition=composition + [model_name],
                include_severities=include_severities,
            )
        )

    return results


def model_breaking_changes(
    old_model: Model, new_model: Model, new_path: str, composition: list[str], include_severities: [Severity]
) -> list[BreakingChange]:
    results = list[BreakingChange]()

    model_definition_fields = vars(new_model)

    for model_definition_field in model_definition_fields.keys():
        if model_definition_field == "fields":
            continue

        old_value = getattr(old_model, model_definition_field)
        new_value = getattr(new_model, model_definition_field)

        rule_name = None
        description = None

        if old_value is None and new_value is not None:
            rule_name = f"model_{model_definition_field}_added"
            description = f"added with value: `{new_value}`"

        elif old_value is not None and new_value is None:
            rule_name = f"model_{model_definition_field}_removed"
            description = "removed model property"

        elif old_value != new_value:
            rule_name = f"model_{model_definition_field}_updated"
            description = f"changed from `{old_value}` to `{new_value}`"

        if rule_name is not None:
            severity = _get_rule(rule_name)
            if severity in include_severities:
                results.append(
                    BreakingChange(
                        description=description,
                        check_name=rule_name,
                        severity=severity,
                        location=Location(path=new_path, composition=composition + [model_definition_field]),
                    )
                )

    results.extend(
        fields_breaking_changes(
            old_fields=old_model.fields,
            new_fields=new_model.fields,
            new_path=new_path,
            composition=composition + ["fields"],
            include_severities=include_severities,
        )
    )

    return results


def fields_breaking_changes(
    old_fields: dict[str, Field],
    new_fields: dict[str, Field],
    new_path: str,
    composition: list[str],
    include_severities: [Severity],
) -> list[BreakingChange]:
    results = list[BreakingChange]()

    for field_name, new_field in new_fields.items():
        if field_name not in old_fields.keys():
            rule_name = "field_added"
            severity = _get_rule(rule_name)
            if severity in include_severities:
                results.append(
                    BreakingChange(
                        description="added the field",
                        check_name=rule_name,
                        severity=severity,
                        location=Location(path=new_path, composition=composition + [field_name]),
                    )
                )

    for field_name, old_field in old_fields.items():
        if field_name not in new_fields.keys():
            rule_name = "field_removed"
            severity = _get_rule(rule_name)
            if severity in include_severities:
                results.append(
                    BreakingChange(
                        description="removed the field",
                        check_name=rule_name,
                        severity=severity,
                        location=Location(path=new_path, composition=composition + [field_name]),
                    )
                )
            continue

        results.extend(
            field_breaking_changes(
                old_field=old_field,
                new_field=new_fields[field_name],
                composition=composition + [field_name],
                new_path=new_path,
                include_severities=include_severities,
            )
        )
    return results


def field_breaking_changes(
    old_field: Field,
    new_field: Field,
    composition: list[str],
    new_path: str,
    include_severities: [Severity],
) -> list[BreakingChange]:
    results = list[BreakingChange]()

    field_definition_fields = vars(new_field)
    for field_definition_field in field_definition_fields.keys():
        if field_definition_field == "ref_obj":
            continue

        old_value = getattr(old_field, field_definition_field)
        new_value = getattr(new_field, field_definition_field)

        if field_definition_field == "fields":
            results.extend(
                fields_breaking_changes(
                    old_fields=old_field.fields,
                    new_fields=new_field.fields,
                    new_path=new_path,
                    composition=composition + [field_definition_field],
                    include_severities=include_severities,
                )
            )
            continue

        if field_definition_field == "items" and old_field.type == "array" and new_field.type == "array":
            results.extend(
                field_breaking_changes(
                    old_field=old_value,
                    new_field=new_value,
                    composition=composition + ["items"],
                    new_path=new_path,
                    include_severities=include_severities,
                )
            )
            continue

        rule_name = None
        description = None

        # logic for enum, tags and other arrays
        if isinstance(old_value, list) and isinstance(new_value, list):
            if not old_value and new_value:
                rule_name = f"field_{_camel_to_snake(field_definition_field)}_added"
                description = f"added with value: `{new_value}`"
            elif old_value and not new_value:
                rule_name = f"field_{_camel_to_snake(field_definition_field)}_removed"
                description = "removed field property"
            elif sorted(old_value) != sorted(new_value):
                rule_name = f"field_{_camel_to_snake(field_definition_field)}_updated"
                description = f"changed from `{old_value}` to `{new_value}`"

        # logic for normal fields
        elif old_value is None and new_value is not None:
            rule_name = f"field_{_camel_to_snake(field_definition_field)}_added"
            description = f"added with value: `{str(new_value).lower() if isinstance(new_value, bool) else new_value}`"

        elif old_value is not None and new_value is None:
            rule_name = f"field_{_camel_to_snake(field_definition_field)}_removed"
            description = "removed field property"

        elif old_value != new_value:
            rule_name = f"field_{_camel_to_snake(field_definition_field)}_updated"
            description = (
                f"changed from `{str(old_value).lower() if isinstance(old_value, bool) else old_value}` "
                f"to `{str(new_value).lower() if isinstance(new_value, bool) else new_value}`"
            )

        if rule_name is not None:
            severity = _get_rule(rule_name)
            field_schema_name = "$ref" if field_definition_field == "ref" else field_definition_field
            if severity in include_severities:
                results.append(
                    BreakingChange(
                        description=description,
                        check_name=rule_name,
                        severity=severity,
                        location=Location(path=new_path, composition=composition + [field_schema_name]),
                    )
                )

    return results


def _get_rule(rule_name) -> Severity:
    try:
        return getattr(BreakingRules, rule_name)
    except AttributeError:
        print(f"WARNING: Breaking Rule not found for {rule_name}!")
        return Severity.ERROR


def _camel_to_snake(s):
    return "".join(["_" + c.lower() if c.isupper() else c for c in s]).lstrip("_")
