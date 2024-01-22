import yaml

from datacontract.model.data_contract_specification import \
    DataContractSpecification


def to_sodacl(data_contract_spec: DataContractSpecification, check_types: bool = True) -> str:
    try:
        sodacl = {}
        for model_key, model_value in data_contract_spec.models.items():
            k, v = to_checks(model_key, model_value, check_types)
            sodacl[k] = v
        add_quality_checks(sodacl, data_contract_spec)
        sodacl_yaml_str = yaml.dump(sodacl, default_flow_style=False)
        return sodacl_yaml_str
    except Exception as e:
        return f"Error: {e}"


def to_checks(model_key, model_value, check_types: bool):
    checks = []
    fields = model_value.fields
    for field_name, field in fields.items():
        checks.append(check_field_is_present(field_name))
        if check_types and field.type is not None:
            checks.append(check_field_type(field_name, field.type))
        if field.required:
            checks.append(check_field_required(field_name))
        if field.unique:
            checks.append(check_field_unique(field_name))

    return f"checks for {model_key}", checks


def check_field_is_present(field_name):
    return {
        "schema": {
            "name": f"Check that field {field_name} is present",
            "fail": {
                "when required column missing": [
                    field_name
                ],
            }
        }
    }


def check_field_type(field_name: str, type: str):
    return {
        "schema": {
            "name": f"Check that field {field_name} has type {type}",
            "fail": {
                "when wrong column type": {
                    field_name: type
                }
            }
        }
    }


def check_field_required(field_name):
    return {
        f"missing_count(\"{field_name}\") = 0": {
            "name": f"Check that required field {field_name} has no null values"
        }
    }


def check_field_unique(field_name):
    return {
        f'duplicate_count(\"{field_name}\") = 0': {
            "name": f"Check that unique field {field_name} has no duplicate values"
        }
    }


def add_quality_checks(sodacl, data_contract_spec):
    if data_contract_spec.quality is None:
        return
    if data_contract_spec.quality.type is None:
        return
    if data_contract_spec.quality.type.lower() != "sodacl":
        return
    if isinstance(data_contract_spec.quality.specification, str):
        quality_specification = yaml.safe_load(data_contract_spec.quality.specification)
    else:
        quality_specification = data_contract_spec.quality.specification
    for key, checks in quality_specification.items():
        if key in sodacl:
            for check in checks:
                sodacl[key].append(check)
        else:
            sodacl[key] = checks
