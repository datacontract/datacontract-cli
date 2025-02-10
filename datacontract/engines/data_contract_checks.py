import uuid
from typing import List
from venv import logger

import yaml

from datacontract.export.sql_type_converter import convert_to_sql_type
from datacontract.model.data_contract_specification import DataContractSpecification, Quality, Server
from datacontract.model.run import Check


def create_checks(data_contract_spec: DataContractSpecification, server: Server) -> List[Check]:
    checks: List[Check] = []
    for model_key, model_value in data_contract_spec.models.items():
        model_checks = to_model_checks(model_key, model_value, server)
        checks.extend(model_checks)
    checks.extend(to_servicelevel_checks(data_contract_spec))
    checks.append(to_quality_check(data_contract_spec))
    return [check for check in checks if check is not None]


def to_model_checks(model_key, model_value, server: Server) -> List[Check]:
    checks: List[Check] = []
    server_type = server.type if server and server.type else None
    model_name = to_model_name(model_key, model_value, server_type)
    fields = model_value.fields

    check_types = is_check_types(server)
    quote_field_name = server_type in ["postgres", "sqlserver"]

    for field_name, field in fields.items():
        checks.append(check_field_is_present(model_name, field_name, quote_field_name))
        if check_types and field.type is not None:
            sql_type = convert_to_sql_type(field, server_type)
            checks.append(check_field_type(model_name, field_name, sql_type, quote_field_name))
        if field.required:
            checks.append(check_field_required(model_name, field_name, quote_field_name))
        if field.unique:
            checks.append(check_field_unique(model_name, field_name, quote_field_name))
        if field.minLength is not None:
            checks.append(check_field_min_length(model_name, field_name, field.minLength, quote_field_name))
        if field.maxLength is not None:
            checks.append(check_field_max_length(model_name, field_name, field.maxLength, quote_field_name))
        if field.minimum is not None:
            checks.append(check_field_minimum(model_name, field_name, field.minimum, quote_field_name))
        if field.maximum is not None:
            checks.append(check_field_maximum(model_name, field_name, field.maximum, quote_field_name))
        if field.exclusiveMinimum is not None:
            checks.append(check_field_minimum(model_name, field_name, field.exclusiveMinimum, quote_field_name))
            checks.append(check_field_not_equal(model_name, field_name, field.exclusiveMinimum, quote_field_name))
        if field.exclusiveMaximum is not None:
            checks.append(check_field_maximum(model_name, field_name, field.exclusiveMaximum, quote_field_name))
            checks.append(check_field_not_equal(model_name, field_name, field.exclusiveMaximum, quote_field_name))
        if field.pattern is not None:
            checks.append(check_field_regex(model_name, field_name, field.pattern, quote_field_name))
        if field.enum is not None and len(field.enum) > 0:
            checks.append(check_field_enum(model_name, field_name, field.enum, quote_field_name))
        if field.quality is not None and len(field.quality) > 0:
            quality_list = check_quality_list(model_name, field_name, field.quality)
            if (quality_list is not None) and len(quality_list) > 0:
                checks.extend(quality_list)
        # TODO references: str = None
        # TODO format

    if model_value.quality is not None and len(model_value.quality) > 0:
        quality_list = check_quality_list(model_name, None, model_value.quality)
        if (quality_list is not None) and len(quality_list) > 0:
            checks.extend(quality_list)

    return checks


def checks_for(model_name, quote_field_name):
    if quote_field_name:
        return f'checks for "{model_name}"'
    return f"checks for {model_name}"


def is_check_types(server: Server) -> bool:
    if server is None:
        return True
    return server.format != "json" and server.format != "csv" and server.format != "avro"


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


def check_field_is_present(model_name, field_name, quote_field_name: bool) -> Check:
    check_type = "field_is_present"
    check_key = f"{model_name}__{field_name}__{check_type}"
    sodacl_check_dict = {
        checks_for(model_name, quote_field_name): [
            {
                "schema": {
                    "name": check_key,
                    "fail": {
                        "when required column missing": [field_name],
                    },
                }
            }
        ]
    }
    return Check(
        id=str(uuid.uuid4()),
        key=check_key,
        category="schema",
        type=check_type,
        name=f"Check that field '{field_name}' is present",
        model=model_name,
        field=field_name,
        engine="soda",
        language="sodacl",
        implementation=yaml.dump(sodacl_check_dict),
    )


def check_field_type(model_name: str, field_name: str, expected_type: str, quote_field_name: bool = False):
    check_type = "field_type"
    check_key = f"{model_name}__{field_name}__{check_type}"
    sodacl_check_dict = {
        checks_for(model_name, quote_field_name): [
            {
                "schema": {
                    "name": check_key,
                    "fail": {
                        "when wrong column type": {
                            field_name: expected_type,
                        },
                    },
                }
            }
        ]
    }
    return Check(
        id=str(uuid.uuid4()),
        key=check_key,
        category="schema",
        type=check_type,
        name=f"Check that field {field_name} has type {expected_type}",
        model=model_name,
        field=field_name,
        engine="soda",
        language="sodacl",
        implementation=yaml.dump(sodacl_check_dict),
    )


def check_field_required(model_name: str, field_name: str, quote_field_name: bool = False):
    if quote_field_name:
        field_name_for_soda = f'"{field_name}"'
    else:
        field_name_for_soda = field_name

    check_type = "field_required"
    check_key = f"{model_name}__{field_name}__{check_type}"
    sodacl_check_dict = {
        checks_for(model_name, quote_field_name): [
            {
                f"missing_count({field_name_for_soda}) = 0": {
                    "name": check_key,
                },
            }
        ],
    }
    return Check(
        id=str(uuid.uuid4()),
        key=check_key,
        category="schema",
        type=check_type,
        name=f"Check that field {field_name} has no missing values",
        model=model_name,
        field=field_name,
        engine="soda",
        language="sodacl",
        implementation=yaml.dump(sodacl_check_dict),
    )


def check_field_unique(model_name: str, field_name: str, quote_field_name: bool = False):
    if quote_field_name:
        field_name_for_soda = f'"{field_name}"'
    else:
        field_name_for_soda = field_name

    check_type = "field_unique"
    check_key = f"{model_name}__{field_name}__{check_type}"
    sodacl_check_dict = {
        checks_for(model_name, quote_field_name): [
            {
                f"duplicate_count({field_name_for_soda}) = 0": {
                    "name": check_key,
                },
            }
        ],
    }
    return Check(
        id=str(uuid.uuid4()),
        key=check_key,
        category="schema",
        type=check_type,
        name=f"Check that unique field {field_name} has no duplicate values",
        model=model_name,
        field=field_name,
        engine="soda",
        language="sodacl",
        implementation=yaml.dump(sodacl_check_dict),
    )


def check_field_min_length(model_name: str, field_name: str, min_length: int, quote_field_name: bool = False):
    if quote_field_name:
        field_name_for_soda = f'"{field_name}"'
    else:
        field_name_for_soda = field_name

    check_type = "field_min_length"
    check_key = f"{model_name}__{field_name}__{check_type}"
    sodacl_check_dict = {
        checks_for(model_name, quote_field_name): [
            {
                f"invalid_count({field_name_for_soda}) = 0": {
                    "name": check_key,
                    "valid min length": min_length,
                },
            }
        ]
    }
    return Check(
        id=str(uuid.uuid4()),
        key=check_key,
        category="schema",
        type=check_type,
        name=f"Check that field {field_name} has a min length of {min_length}",
        model=model_name,
        field=field_name,
        engine="soda",
        language="sodacl",
        implementation=yaml.dump(sodacl_check_dict),
    )


def check_field_max_length(model_name: str, field_name: str, max_length: int, quote_field_name: bool = False):
    if quote_field_name:
        field_name_for_soda = f'"{field_name}"'
    else:
        field_name_for_soda = field_name

    check_type = "field_max_length"
    check_key = f"{model_name}__{field_name}__{check_type}"
    sodacl_check_dict = {
        checks_for(model_name, quote_field_name): [
            {
                f"invalid_count({field_name_for_soda}) = 0": {
                    "name": check_key,
                    "valid max length": max_length,
                },
            }
        ],
    }
    return Check(
        id=str(uuid.uuid4()),
        key=check_key,
        category="schema",
        type=check_type,
        name=f"Check that field {field_name} has a max length of {max_length}",
        model=model_name,
        field=field_name,
        engine="soda",
        language="sodacl",
        implementation=yaml.dump(sodacl_check_dict),
    )


def check_field_minimum(model_name: str, field_name: str, minimum: int, quote_field_name: bool = False):
    if quote_field_name:
        field_name_for_soda = f'"{field_name}"'
    else:
        field_name_for_soda = field_name

    check_type = "field_minimum"
    check_key = f"{model_name}__{field_name}__{check_type}"
    sodacl_check_dict = {
        checks_for(model_name, quote_field_name): [
            {
                f"invalid_count({field_name_for_soda}) = 0": {
                    "name": check_key,
                    "valid min": minimum,
                },
            }
        ],
    }
    return Check(
        id=str(uuid.uuid4()),
        key=check_key,
        category="schema",
        type=check_type,
        name=f"Check that field {field_name} has a minimum of {minimum}",
        model=model_name,
        field=field_name,
        engine="soda",
        language="sodacl",
        implementation=yaml.dump(sodacl_check_dict),
    )


def check_field_maximum(model_name: str, field_name: str, maximum: int, quote_field_name: bool = False):
    if quote_field_name:
        field_name_for_soda = f'"{field_name}"'
    else:
        field_name_for_soda = field_name

    check_type = "field_maximum"
    check_key = f"{model_name}__{field_name}__{check_type}"
    sodacl_check_dict = {
        checks_for(model_name, quote_field_name): [
            {
                f"invalid_count({field_name_for_soda}) = 0": {
                    "name": check_key,
                    "valid max": maximum,
                },
            }
        ],
    }
    return Check(
        id=str(uuid.uuid4()),
        key=check_key,
        category="schema",
        type=check_type,
        name=f"Check that field {field_name} has a maximum of {maximum}",
        model=model_name,
        field=field_name,
        engine="soda",
        language="sodacl",
        implementation=yaml.dump(sodacl_check_dict),
    )


def check_field_not_equal(model_name: str, field_name: str, value: int, quote_field_name: bool = False):
    if quote_field_name:
        field_name_for_soda = f'"{field_name}"'
    else:
        field_name_for_soda = field_name

    check_type = "field_not_equal"
    check_key = f"{model_name}__{field_name}__{check_type}"
    sodacl_check_dict = {
        checks_for(model_name, quote_field_name): [
            {
                f"invalid_count({field_name_for_soda}) = 0": {
                    "name": check_key,
                    "invalid values": [value],
                },
            }
        ],
    }
    return Check(
        id=str(uuid.uuid4()),
        key=check_key,
        category="schema",
        type=check_type,
        name=f"Check that field {field_name} is not equal to {value}",
        model=model_name,
        field=field_name,
        engine="soda",
        language="sodacl",
        implementation=yaml.dump(sodacl_check_dict),
    )


def check_field_enum(model_name: str, field_name: str, enum: list, quote_field_name: bool = False):
    if quote_field_name:
        field_name_for_soda = f'"{field_name}"'
    else:
        field_name_for_soda = field_name

    check_type = "field_enum"
    check_key = f"{model_name}__{field_name}__{check_type}"
    sodacl_check_dict = {
        checks_for(model_name, quote_field_name): [
            {
                f"invalid_count({field_name_for_soda}) = 0": {
                    "name": check_key,
                    "valid values": enum,
                },
            }
        ],
    }
    return Check(
        id=str(uuid.uuid4()),
        key=check_key,
        category="schema",
        type=check_type,
        name=f"Check that field {field_name} only contains enum values {enum}",
        model=model_name,
        field=field_name,
        engine="soda",
        language="sodacl",
        implementation=yaml.dump(sodacl_check_dict),
    )


def check_field_regex(model_name: str, field_name: str, pattern: str, quote_field_name: bool = False):
    if quote_field_name:
        field_name_for_soda = f'"{field_name}"'
    else:
        field_name_for_soda = field_name

    check_type = "field_regex"
    check_key = f"{model_name}__{field_name}__{check_type}"
    sodacl_check_dict = {
        checks_for(model_name, quote_field_name): [
            {
                f"invalid_count({field_name_for_soda}) = 0": {
                    "name": check_key,
                    "valid regex": pattern,
                },
            }
        ],
    }
    return Check(
        id=str(uuid.uuid4()),
        key=check_key,
        category="schema",
        type=check_type,
        name=f"Check that field {field_name} matches regex pattern {pattern}",
        model=model_name,
        field=field_name,
        engine="soda",
        language="sodacl",
        implementation=yaml.dump(sodacl_check_dict),
    )


def check_quality_list(model_name, field_name, quality_list: List[Quality]) -> List[Check]:
    checks: List[Check] = []

    count = 0
    for quality in quality_list:
        if quality.type == "sql":
            if field_name is None:
                check_key = f"{model_name}__quality_sql_{count}"
                check_type = "field_quality_sql"
            else:
                check_key = f"{model_name}__{field_name}__quality_sql_{count}"
                check_type = "model_quality_sql"
            threshold = to_sodacl_threshold(quality)
            query = prepare_query(quality, model_name, field_name)
            if query is None:
                logger.warning(f"Quality check {check_key} has no query")
                continue
            if threshold is None:
                logger.warning(f"Quality check {check_key} has no valid threshold")
                continue
            sodacl_check_dict = {
                f"checks for {model_name}": [
                    {
                        f"{check_key} {threshold}": {
                            f"{check_key} query": query,
                            "name": check_key,
                        },
                    }
                ]
            }
            checks.append(
                Check(
                    id=str(uuid.uuid4()),
                    key=check_key,
                    category="quality",
                    type=check_type,
                    name=quality.description if quality.description is not None else "Quality Check",
                    model=model_name,
                    field=field_name,
                    engine="soda",
                    language="sodacl",
                    implementation=yaml.dump(sodacl_check_dict),
                )
            )
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


def to_servicelevel_checks(data_contract_spec: DataContractSpecification) -> List[Check]:
    checks: List[Check] = []
    if data_contract_spec.servicelevels is None:
        return checks
    if data_contract_spec.servicelevels.freshness is not None:
        checks.append(to_servicelevel_freshness_check(data_contract_spec))
    if data_contract_spec.servicelevels.retention is not None:
        checks.append(to_servicelevel_retention_check(data_contract_spec))
    # only return checks that are not None
    return [check for check in checks if check is not None]


def to_servicelevel_freshness_check(data_contract_spec: DataContractSpecification) -> Check | None:
    if data_contract_spec.servicelevels.freshness.timestampField is None:
        return None
    freshness_threshold = data_contract_spec.servicelevels.freshness.threshold
    if freshness_threshold is None:
        logger.info("servicelevel.freshness.threshold is not defined")
        return None

    if not (
        "d" in freshness_threshold
        or "D" in freshness_threshold
        or "h" in freshness_threshold
        or "H" in freshness_threshold
        or "m" in freshness_threshold
        or "M" in freshness_threshold
    ):
        logger.info("servicelevel.freshness.threshold must be in days, hours, or minutes (e.g., PT1H, or 1h)")
        return None
    timestamp_field_fully_qualified = data_contract_spec.servicelevels.freshness.timestampField
    if "." not in timestamp_field_fully_qualified:
        logger.info("servicelevel.freshness.timestampField is not fully qualified, skipping freshness check")
        return None
    if timestamp_field_fully_qualified.count(".") > 1:
        logger.info(
            "servicelevel.freshness.timestampField contains multiple dots, which is currently not supported, skipping freshness check"
        )
        return None
    model_name = timestamp_field_fully_qualified.split(".")[0]
    field_name = timestamp_field_fully_qualified.split(".")[1]
    threshold = freshness_threshold
    threshold = threshold.replace("P", "")
    threshold = threshold.replace("T", "")
    threshold = threshold.lower()
    if model_name not in data_contract_spec.models:
        logger.info(f"Model {model_name} not found in data_contract_spec.models, skipping freshness check")
        return None

    check_type = "servicelevel_freshness"
    check_key = "servicelevel_freshness"

    sodacl_check_dict = {
        checks_for(model_name, False): [
            {
                f"freshness({field_name}) < {threshold}": {
                    "name": check_key,
                },
            }
        ]
    }
    return Check(
        id=str(uuid.uuid4()),
        key=check_key,
        category="servicelevel",
        type=check_type,
        name="Freshness",
        model=model_name,
        engine="soda",
        language="sodacl",
        implementation=yaml.dump(sodacl_check_dict),
    )


def to_servicelevel_retention_check(data_contract_spec) -> Check | None:
    if data_contract_spec.servicelevels.retention is None:
        return None
    if data_contract_spec.servicelevels.retention.unlimited is True:
        return None
    if data_contract_spec.servicelevels.retention.timestampField is None:
        logger.info("servicelevel.retention.timestampField is not defined")
        return None
    if data_contract_spec.servicelevels.retention.period is None:
        logger.info("servicelevel.retention.period is not defined")
        return None
    timestamp_field_fully_qualified = data_contract_spec.servicelevels.retention.timestampField
    if "." not in timestamp_field_fully_qualified:
        logger.info("servicelevel.retention.timestampField is not fully qualified, skipping retention check")
        return None
    if timestamp_field_fully_qualified.count(".") > 1:
        logger.info(
            "servicelevel.retention.timestampField contains multiple dots, which is currently not supported, skipping retention check"
        )
        return None

    model_name = timestamp_field_fully_qualified.split(".")[0]
    field_name = timestamp_field_fully_qualified.split(".")[1]
    period = data_contract_spec.servicelevels.retention.period
    period_in_seconds = period_to_seconds(period)
    if model_name not in data_contract_spec.models:
        logger.info(f"Model {model_name} not found in data_contract_spec.models, skipping retention check")
        return None
    check_type = "servicelevel_retention"
    check_key = "servicelevel_retention"
    sodacl_check_dict = {
        checks_for(model_name, False): [
            {
                f"orders_servicelevel_retention < {period_in_seconds}": {
                    "orders_servicelevel_retention expression": f"TIMESTAMPDIFF(SECOND, MIN({field_name}), CURRENT_TIMESTAMP)",
                    "name": check_key,
                }
            },
        ]
    }
    return Check(
        id=str(uuid.uuid4()),
        key=check_key,
        category="servicelevel",
        type=check_type,
        name=f"Retention: Oldest entry has a max age of {period}",
        model=model_name,
        engine="soda",
        language="sodacl",
        implementation=yaml.dump(sodacl_check_dict),
    )


def period_to_seconds(period: str) -> int | None:
    import re

    # if period is None:
    #     return None
    # if period is in form "30d" or "24h" or "60m"
    if re.match(r"^\d+[dhm]$", period):
        if period[-1] == "d":
            return int(period[:-1]) * 86400
        if period[-1] == "h":
            return int(period[:-1]) * 3600
        if period[-1] == "m":
            return int(period[:-1]) * 60
    # if it is in iso period format (do not use isodate, can also be years)
    iso_period_regex = re.compile(
        r"P(?:(?P<years>\d+)Y)?(?:(?P<months>\d+)M)?(?:(?P<days>\d+)D)?"
        r"(?:T(?:(?P<hours>\d+)H)?(?:(?P<minutes>\d+)M)?(?:(?P<seconds>\d+)S)?)?"
    )
    match = iso_period_regex.match(period)
    if match:
        years = int(match.group("years") or 0)
        months = int(match.group("months") or 0)
        days = int(match.group("days") or 0)
        hours = int(match.group("hours") or 0)
        minutes = int(match.group("minutes") or 0)
        seconds = int(match.group("seconds") or 0)

        # Convert everything to seconds
        total_seconds = (
            years * 365 * 86400  # Approximate conversion of years to seconds
            + months * 30 * 86400  # Approximate conversion of months to seconds
            + days * 86400
            + hours * 3600
            + minutes * 60
            + seconds
        )
        return total_seconds

    return None


# These are deprecated root-level quality specifications, use the model-level and field-level quality fields instead
def to_quality_check(data_contract_spec) -> Check | None:
    if data_contract_spec.quality is None:
        return None
    if data_contract_spec.quality.type is None:
        return None
    if data_contract_spec.quality.type.lower() != "sodacl":
        return None
    if isinstance(data_contract_spec.quality.specification, str):
        quality_specification = yaml.safe_load(data_contract_spec.quality.specification)
    else:
        quality_specification = data_contract_spec.quality.specification

    return Check(
        id=str(uuid.uuid4()),
        key="quality__sodacl",
        category="quality",
        type="quality",
        name="Quality Check",
        model=None,
        engine="soda",
        language="sodacl",
        implementation=yaml.dump(quality_specification),
    )
