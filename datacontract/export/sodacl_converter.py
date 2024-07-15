import yaml

from datacontract.export.sql_type_converter import convert_to_sql_type
from datacontract.model.data_contract_specification import DataContractSpecification
from datacontract.export.exporter import Exporter


class SodaExporter(Exporter):
    def export(self, data_contract, model, server, sql_server_type, export_args) -> dict:
        return to_sodacl_yaml(data_contract)


def to_sodacl_yaml(
    data_contract_spec: DataContractSpecification, server_type: str = None, check_types: bool = True
) -> str:
    try:
        sodacl = {}
        for model_key, model_value in data_contract_spec.models.items():
            k, v = to_checks(model_key, model_value, server_type, check_types)
            sodacl[k] = v
        add_quality_checks(sodacl, data_contract_spec)
        sodacl_yaml_str = yaml.dump(sodacl, default_flow_style=False, sort_keys=False)
        return sodacl_yaml_str
    except Exception as e:
        return f"Error: {e}"


def to_checks(model_key, model_value, server_type: str, check_types: bool):
    checks = []
    fields = model_value.fields

    quote_field_name = server_type in ["postgres"]

    for field_name, field in fields.items():
        checks.append(check_field_is_present(field_name))
        if check_types and field.type is not None:
            sql_type = convert_to_sql_type(field, server_type)
            checks.append(check_field_type(field_name, sql_type))
        if field.required:
            checks.append(check_field_required(field_name, quote_field_name))
        if field.unique:
            checks.append(check_field_unique(field_name, quote_field_name))
        if field.minLength is not None:
            checks.append(check_field_min_length(field_name, field.minLength, quote_field_name))
        if field.maxLength is not None:
            checks.append(check_field_max_length(field_name, field.maxLength, quote_field_name))
        if field.minimum is not None:
            checks.append(check_field_minimum(field_name, field.minimum, quote_field_name))
        if field.maximum is not None:
            checks.append(check_field_maximum(field_name, field.maximum, quote_field_name))
        if field.exclusiveMinimum is not None:
            checks.append(check_field_minimum(field_name, field.exclusiveMinimum, quote_field_name))
            checks.append(check_field_not_equal(field_name, field.exclusiveMinimum, quote_field_name))
        if field.exclusiveMaximum is not None:
            checks.append(check_field_maximum(field_name, field.exclusiveMaximum, quote_field_name))
            checks.append(check_field_not_equal(field_name, field.exclusiveMaximum, quote_field_name))
        if field.pattern is not None:
            checks.append(check_field_regex(field_name, field.pattern, quote_field_name))
        if field.enum is not None and len(field.enum) > 0:
            checks.append(check_field_enum(field_name, field.enum, quote_field_name))
        # TODO references: str = None
        # TODO format

    checks_for_model_key = f"checks for {model_key}"

    if quote_field_name:
        checks_for_model_key = f'checks for "{model_key}"'

    return checks_for_model_key, checks


def check_field_is_present(field_name):
    return {
        "schema": {
            "name": f"Check that field {field_name} is present",
            "fail": {
                "when required column missing": [field_name],
            },
        }
    }


def check_field_type(field_name: str, type: str):
    return {
        "schema": {
            "name": f"Check that field {field_name} has type {type}",
            "fail": {"when wrong column type": {field_name: type}},
        }
    }


def check_field_required(field_name: str, quote_field_name: bool = False):
    if quote_field_name:
        field_name = f'"{field_name}"'

    return {f"missing_count({field_name}) = 0": {"name": f"Check that required field {field_name} has no null values"}}


def check_field_unique(field_name, quote_field_name: bool = False):
    if quote_field_name:
        field_name = f'"{field_name}"'
    return {
        f"duplicate_count({field_name}) = 0": {"name": f"Check that unique field {field_name} has no duplicate values"}
    }


def check_field_min_length(field_name, min_length, quote_field_name: bool = False):
    if quote_field_name:
        field_name = f'"{field_name}"'
    return {
        f"invalid_count({field_name}) = 0": {
            "name": f"Check that field {field_name} has a min length of {min_length}",
            "valid min length": min_length,
        }
    }


def check_field_max_length(field_name, max_length, quote_field_name: bool = False):
    if quote_field_name:
        field_name = f'"{field_name}"'
    return {
        f"invalid_count({field_name}) = 0": {
            "name": f"Check that field {field_name} has a max length of {max_length}",
            "valid max length": max_length,
        }
    }


def check_field_minimum(field_name, minimum, quote_field_name: bool = False):
    if quote_field_name:
        field_name = f'"{field_name}"'
    return {
        f"invalid_count({field_name}) = 0": {
            "name": f"Check that field {field_name} has a minimum of {minimum}",
            "valid min": minimum,
        }
    }


def check_field_maximum(field_name, maximum, quote_field_name: bool = False):
    if quote_field_name:
        field_name = f'"{field_name}"'
    return {
        f"invalid_count({field_name}) = 0": {
            "name": f"Check that field {field_name} has a maximum of {maximum}",
            "valid max": maximum,
        }
    }


def check_field_not_equal(field_name, value, quote_field_name: bool = False):
    if quote_field_name:
        field_name = f'"{field_name}"'
    return {
        f"invalid_count({field_name}) = 0": {
            "name": f"Check that field {field_name} is not equal to {value}",
            "invalid values": [value],
        }
    }


def check_field_enum(field_name, enum, quote_field_name: bool = False):
    if quote_field_name:
        field_name = f'"{field_name}"'
    return {
        f"invalid_count({field_name}) = 0": {
            "name": f"Check that field {field_name} only contains enum values {enum}",
            "valid values": enum,
        }
    }


def check_field_regex(field_name, pattern, quote_field_name: bool = False):
    if quote_field_name:
        field_name = f'"{field_name}"'
    return {
        f"invalid_count({field_name}) = 0": {
            "name": f"Check that field {field_name} matches regex pattern {pattern}",
            "valid regex": pattern,
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
