from typing import List
from venv import logger

import yaml

from datacontract.export.exporter import Exporter
from datacontract.export.sql_type_converter import convert_to_sql_type
from datacontract.model.data_contract_specification import DataContractSpecification, Quality


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
    model_name = to_model_name(model_key, model_value, server_type)
    fields = model_value.fields

    quote_field_name = server_type in ["postgres", "sqlserver"]

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
        if field.quality is not None and len(field.quality) > 0:
            quality_list = check_quality_list(model_name, field_name, field.quality)
            if (quality_list is not None) and len(quality_list) > 0:
                checks.append(quality_list)
        # TODO references: str = None
        # TODO format

    if model_value.quality is not None and len(model_value.quality) > 0:
        quality_list = check_quality_list(model_name, None, model_value.quality)
        if (quality_list is not None) and len(quality_list) > 0:
            checks.append(quality_list)

    checks_for_model_key = f"checks for {model_name}"

    if quote_field_name:
        checks_for_model_key = f'checks for "{model_name}"'

    return checks_for_model_key, checks


def to_model_name(model_key, model_value, server_type):
    if server_type == "databricks":
        if model_value.config is not None and "databricksTable" in model_value.config:
            return model_value.config["databricksTable"]
    if server_type == "snowflake":
        if model_value.config is not None and "snowflakeTable" in model_value.config:
            return model_value.config["snowflakeTable"]
    if server_type == "sqlserver":
        if model_value.config is not None and "sqlserverTable" in model_value.config:
            return model_value.config["sqlserverTable"]
    if server_type == "postgres" or server_type == "postgresql":
        if model_value.config is not None and "postgresTable" in model_value.config:
            return model_value.config["postgresTable"]
    return model_key


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


def check_quality_list(model_name, field_name, quality_list: List[Quality]):
    checks = {}

    count = 0
    for quality in quality_list:
        if quality.type == "sql":
            if field_name is None:
                metric_name = f"{model_name}_quality_sql_{count}"
            else:
                metric_name = f"{model_name}_{field_name}_quality_sql_{count}"
            threshold = to_sodacl_threshold(quality)
            query = prepare_query(quality, model_name, field_name)
            if query is None:
                logger.warning(f"Quality check {metric_name} has no query")
                continue
            if threshold is None:
                logger.warning(f"Quality check {metric_name} has no valid threshold")
                continue
            checks[f"{metric_name} {threshold}"] = {f"{metric_name} query": query}
        count += 1

    return checks


def prepare_query(quality: Quality, model_name: str, field_name: str = None) -> str | None:
    if quality.query is None:
        return None
    if quality.query == "":
        return None

    query = quality.query

    query = query.replace("{model}", model_name)
    query = query.replace("{table}", model_name)

    if field_name is not None:
        query = query.replace("{field}", field_name)
        query = query.replace("{column}", field_name)

    return query


def to_sodacl_threshold(quality: Quality) -> str | None:
    if quality.mustBe is not None:
        return f"= {quality.mustBe}"
    if quality.mustNotBe is not None:
        return f"!= {quality.mustNotBe}"
    if quality.mustBeGreaterThan is not None:
        return f"> {quality.mustBeGreaterThan}"
    if quality.mustBeGreaterThanOrEqualTo is not None:
        return f">= {quality.mustBeGreaterThanOrEqualTo}"
    if quality.mustBeLessThan is not None:
        return f"< {quality.mustBeLessThan}"
    if quality.mustBeLessThanOrEqualTo is not None:
        return f"<= {quality.mustBeLessThanOrEqualTo}"
    if quality.mustBeBetween is not None:
        if len(quality.mustBeBetween) != 2:
            logger.warning(
                f"Quality check has invalid mustBeBetween, must have exactly 2 integers in an array: {quality.mustBeBetween}"
            )
            return None
        return f"between {quality.mustBeBetween[0]} and {quality.mustBeBetween[1]}"
    if quality.mustNotBeBetween is not None:
        if len(quality.mustNotBeBetween) != 2:
            logger.warning(
                f"Quality check has invalid mustNotBeBetween, must have exactly 2 integers in an array: {quality.mustNotBeBetween}"
            )
            return None
        return f"not between {quality.mustNotBeBetween[0]} and {quality.mustNotBeBetween[1]}"
    return None


# These are deprecated root-level quality specifications, use the model-level and field-level quality fields instead
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
