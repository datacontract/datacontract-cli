from datacontract.model.breaking_result import BreakingResults, BreakingResult, Location
from datacontract.model.data_contract_specification import Field, Model


def models_breaking_changes(old_models: dict[str, Model],
                            new_models: dict[str, Model],
                            new_path: str
                            ) -> BreakingResults:
    composition = ["models"]
    results = list[BreakingResult]()

    for model_name, old_model in old_models.items():
        if model_name not in new_models.keys():
            results.append(
                BreakingResult(
                    description=f"removed the model `{model_name}`",
                    check_name="model-removed",
                    severity="error",
                    location=Location(
                        path=new_path,
                        composition=composition
                    )))
            continue

        results.extend(
            fields_breaking_changes(
                old_fields=old_model.fields,
                new_fields=new_models[model_name].fields,
                new_path=new_path,
                composition=composition + [model_name]
            ))

    return BreakingResults(breaking_results=results)


def fields_breaking_changes(old_fields: dict[str, Field],
                            new_fields: dict[str, Field],
                            new_path: str,
                            composition: list[str]
                            ) -> list[BreakingResult]:
    results = list[BreakingResult]()

    for field_name, old_field in old_fields.items():
        if field_name not in new_fields.keys():
            results.append(
                BreakingResult(
                    description=f"removed the field `{field_name}`",
                    check_name="field-removed",
                    severity="error",
                    location=Location(
                        path=new_path,
                        composition=composition
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
) -> list[BreakingResult]:
    results = list[BreakingResult]()

    if old_field.type is not None and old_field.type != new_field.type:
        results.append(BreakingResult(
            description=f"changed the type from `{old_field.type}` to `{new_field.type}`",
            check_name="field-type-changed",
            severity="error",
            location=Location(
                path=new_path,
                composition=composition
            )))

    if old_field.format is not None and old_field.format != new_field.format:
        results.append(BreakingResult(
            description=f"changed the format from `{old_field.format}` to `{new_field.format}`",
            check_name="field-format-changed",
            severity="error",
            location=Location(
                path=new_path,
                composition=composition
            )))

    if old_field.description is not None and old_field.description != new_field.description:
        results.append(BreakingResult(
            description="changed the description",
            check_name="field-description-changed",
            severity="warning",
            location=Location(
                path=new_path,
                composition=composition
            )))

    return results
