from datacontract.breaking.breaking_rules import BreakingRules
from datacontract.model.breaking_change import BreakingChanges, BreakingChange, Location
from datacontract.model.data_contract_specification import Field, Model


def models_breaking_changes(
    old_models: dict[str, Model],
    new_models: dict[str, Model],
    new_path: str
) -> BreakingChanges:
    composition = ["models"]
    results = list[BreakingChange]()

    for model_name, new_model in new_models.items():
        if model_name not in old_models.keys():
            rule_name = "model_added"
            severity = _get_rule(rule_name)
            if severity != "info":
                results.append(
                    BreakingChange(
                        description="added the model",
                        check_name=rule_name,
                        severity=severity,
                        location=Location(
                            path=new_path,
                            composition=composition + [model_name]
                        )))

    for model_name, old_model in old_models.items():
        if model_name not in new_models.keys():
            rule_name = "model_removed"
            severity = _get_rule(rule_name)
            if severity != "info":
                results.append(
                    BreakingChange(
                        description="removed the model",
                        check_name=rule_name,
                        severity=severity,
                        location=Location(
                            path=new_path,
                            composition=composition + [model_name]
                        )))
            continue

        results.extend(
            model_breaking_changes(
                old_model=old_model,
                new_model=new_models[model_name],
                new_path=new_path,
                composition=composition + [model_name]
            ))

    return BreakingChanges(breaking_changes=results)


def model_breaking_changes(
    old_model: Model,
    new_model: Model,
    new_path: str,
    composition: list[str]
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
            if severity != "info":
                results.append(
                    BreakingChange(
                        description=description,
                        check_name=rule_name,
                        severity=severity,
                        location=Location(
                            path=new_path,
                            composition=composition + [model_definition_field]
                        )))

    results.extend(
        fields_breaking_changes(
            old_fields=old_model.fields,
            new_fields=new_model.fields,
            new_path=new_path,
            composition=composition
        ))

    return results


def fields_breaking_changes(
    old_fields: dict[str, Field],
    new_fields: dict[str, Field],
    new_path: str,
    composition: list[str]
) -> list[BreakingChange]:
    results = list[BreakingChange]()

    for field_name, new_field in new_fields.items():
        if field_name not in old_fields.keys():
            rule_name = "field_added"
            severity = _get_rule(rule_name)
            if severity != "info":
                results.append(
                    BreakingChange(
                        description="added the field",
                        check_name=rule_name,
                        severity=severity,
                        location=Location(
                            path=new_path,
                            composition=composition + [field_name]
                        )))

    for field_name, old_field in old_fields.items():
        if field_name not in new_fields.keys():
            rule_name = "field_removed"
            severity = _get_rule(rule_name)
            if severity != "info":
                results.append(
                    BreakingChange(
                        description='removed the field',
                        check_name=rule_name,
                        severity=severity,
                        location=Location(
                            path=new_path,
                            composition=composition + [field_name]
                        )))
            continue

        results.extend(
            field_breaking_changes(
                old_field=old_field,
                new_field=new_fields[field_name],
                composition=composition + [field_name],
                new_path=new_path,
            ))
    return results


def field_breaking_changes(
    old_field: Field,
    new_field: Field,
    composition: list[str],
    new_path: str,
) -> list[BreakingChange]:
    results = list[BreakingChange]()

    field_definition_fields = vars(new_field)
    for field_definition_field in field_definition_fields.keys():

        # TODO(torbenkeller): handle ref case
        if field_definition_field == "ref":
            continue

        old_value = getattr(old_field, field_definition_field)
        new_value = getattr(new_field, field_definition_field)

        if field_definition_field == "fields":
            results.extend(
                fields_breaking_changes(
                    old_fields=old_field.fields,
                    new_fields=new_field.fields,
                    new_path=new_path,
                    composition=composition + [field_definition_field]
                )
            )
            continue

        rule_name = None
        description = None

        # logic for enum, tags and other arrays
        if type(old_value) is list and type(new_value) is list:
            if not old_value and new_value:
                rule_name = f"field_{field_definition_field}_added"
                description = f"added with value: `{new_value}`"
            elif old_value and not new_value:
                rule_name = f"field_{field_definition_field}_removed"
                description = "removed field property"
            elif sorted(old_value) != sorted(new_value):
                rule_name = f"field_{field_definition_field}_updated"
                description = f"changed from `{old_value}` to `{new_value}`"

        # logic for normal fields
        elif old_value is None and new_value is not None:
            rule_name = f"field_{field_definition_field}_added"
            description = f"added with value: `{str(new_value).lower() if type(new_value) is bool else new_value}`"

        elif old_value is not None and new_value is None:
            rule_name = f"field_{field_definition_field}_removed"
            description = "removed field property"

        elif old_value != new_value:
            rule_name = f"field_{field_definition_field}_updated"
            description = (f"changed from `{str(old_value).lower() if type(old_value) is bool else old_value}` "
                           f"to `{str(new_value).lower() if type(new_value) is bool else new_value}`")

        if rule_name is not None:
            severity = _get_rule(rule_name)
            if severity != "info":
                results.append(
                    BreakingChange(
                        description=description,
                        check_name=rule_name,
                        severity=severity,
                        location=Location(
                            path=new_path,
                            composition=composition + [field_definition_field]
                        )))

    return results


def _get_rule(rule_name):
    try:
        return getattr(BreakingRules, rule_name)
    except AttributeError:
        print(f'WARNING: Breaking Rule not found for {rule_name}!')
        return 'error'
