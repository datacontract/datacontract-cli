import re
import uuid
from dataclasses import dataclass
from typing import List, Optional
from venv import logger

import yaml
from open_data_contract_standard.model import (
    DataQuality,
    OpenDataContractStandard,
    SchemaObject,
    SchemaProperty,
    Server,
)

from datacontract.export.sql_type_converter import convert_to_sql_type
from datacontract.model.run import Check


@dataclass
class QuotingConfig:
    quote_field_name: bool = False
    quote_model_name: bool = False
    quote_model_name_with_backticks: bool = False


def _get_logical_type_option(prop: SchemaProperty, key: str):
    """Get a logical type option value."""
    if prop.logicalTypeOptions is None:
        return None
    return prop.logicalTypeOptions.get(key)


def _get_custom_property_value(prop: SchemaProperty, key: str) -> Optional[str]:
    """Get a custom property value."""
    if prop.customProperties is None:
        return None
    for cp in prop.customProperties:
        if cp.property == key:
            return cp.value
    return None


def _get_schema_custom_property_value(schema: SchemaObject, key: str) -> Optional[str]:
    """Get a custom property value from schema."""
    if schema.customProperties is None:
        return None
    for cp in schema.customProperties:
        if cp.property == key:
            return cp.value
    return None


def create_checks(data_contract: OpenDataContractStandard, server: Server) -> List[Check]:
    checks: List[Check] = []
    if data_contract.schema_ is None:
        return checks
    for schema_obj in data_contract.schema_:
        schema_checks = to_schema_checks(schema_obj, server)
        checks.extend(schema_checks)
    checks.extend(to_servicelevel_checks(data_contract))
    return [check for check in checks if check is not None]


def to_schema_checks(schema_object: SchemaObject, server: Server) -> List[Check]:
    checks: List[Check] = []
    server_type = server.type if server and server.type else None
    schema_name = to_schema_name(schema_object, server_type)
    properties = schema_object.properties or []

    check_types = is_check_types(server)

    type1 = server.type if server and server.type else None
    config = QuotingConfig(
        quote_field_name=type1 in ["postgres", "sqlserver"],
        quote_model_name=type1 in ["postgres", "sqlserver"],
        quote_model_name_with_backticks=type1 == "bigquery",
    )
    quoting_config = config

    for prop in properties:
        property_name = prop.name
        logical_type = prop.logicalType

        checks.append(check_property_is_present(schema_name, property_name, quoting_config))
        if check_types and logical_type is not None:
            sql_type: str = convert_to_sql_type(prop, server_type)
            checks.append(check_property_type(schema_name, property_name, sql_type, quoting_config))
        if prop.required:
            checks.append(check_property_required(schema_name, property_name, quoting_config))
        if prop.unique:
            checks.append(check_property_unique(schema_name, property_name, quoting_config))

        min_length = _get_logical_type_option(prop, "minLength")
        if min_length is not None:
            checks.append(check_property_min_length(schema_name, property_name, min_length, quoting_config))

        max_length = _get_logical_type_option(prop, "maxLength")
        if max_length is not None:
            checks.append(check_property_max_length(schema_name, property_name, max_length, quoting_config))

        minimum = _get_logical_type_option(prop, "minimum")
        if minimum is not None:
            checks.append(check_property_minimum(schema_name, property_name, minimum, quoting_config))

        maximum = _get_logical_type_option(prop, "maximum")
        if maximum is not None:
            checks.append(check_property_maximum(schema_name, property_name, maximum, quoting_config))

        exclusive_minimum = _get_logical_type_option(prop, "exclusiveMinimum")
        if exclusive_minimum is not None:
            checks.append(check_property_minimum(schema_name, property_name, exclusive_minimum, quoting_config))
            checks.append(check_property_not_equal(schema_name, property_name, exclusive_minimum, quoting_config))

        exclusive_maximum = _get_logical_type_option(prop, "exclusiveMaximum")
        if exclusive_maximum is not None:
            checks.append(check_property_maximum(schema_name, property_name, exclusive_maximum, quoting_config))
            checks.append(check_property_not_equal(schema_name, property_name, exclusive_maximum, quoting_config))

        pattern = _get_logical_type_option(prop, "pattern")
        if pattern is not None:
            checks.append(check_property_regex(schema_name, property_name, pattern, quoting_config))

        enum_values = _get_logical_type_option(prop, "enum")
        if enum_values is not None and len(enum_values) > 0:
            checks.append(check_property_enum(schema_name, property_name, enum_values, quoting_config))

        if prop.quality is not None and len(prop.quality) > 0:
            quality_list = check_quality_list(schema_name, property_name, prop.quality, quoting_config, server)
            if (quality_list is not None) and len(quality_list) > 0:
                checks.extend(quality_list)

    if schema_object.quality is not None and len(schema_object.quality) > 0:
        quality_list = check_quality_list(schema_name, None, schema_object.quality, quoting_config, server)
        if (quality_list is not None) and len(quality_list) > 0:
            checks.extend(quality_list)

    return checks


def checks_for(model_name: str, quoting_config: QuotingConfig, check_type: str) -> str:
    if quoting_config.quote_model_name:
        return f'checks for "{model_name}"'
    elif quoting_config.quote_model_name_with_backticks and check_type not in ["field_is_present", "field_type"]:
        return f"checks for `{model_name}`"
    return f"checks for {model_name}"


def is_check_types(server: Server) -> bool:
    if server is None:
        return True
    return server.format != "json" and server.format != "csv" and server.format != "avro"


def to_schema_name(schema_object: SchemaObject, server_type: str) -> str:
    # For Kafka, use name (not physicalName) since the Spark SQL view uses schema name
    # physicalName in Kafka represents the topic name, not the SQL view name
    if server_type == "kafka":
        return schema_object.name

    # Use physicalName if set (ODCS standard way to specify actual table name)
    if schema_object.physicalName:
        return schema_object.physicalName

    return schema_object.name



def check_property_is_present(model_name, field_name, quoting_config: QuotingConfig = QuotingConfig()) -> Check:
    check_type = "field_is_present"
    check_key = f"{model_name}__{field_name}__{check_type}"
    sodacl_check_dict = {
        checks_for(model_name, quoting_config, check_type): [
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


def check_property_type(
    model_name: str, field_name: str, expected_type: str, quoting_config: QuotingConfig = QuotingConfig()
):
    check_type = "field_type"
    check_key = f"{model_name}__{field_name}__{check_type}"
    sodacl_check_dict = {
        checks_for(model_name, quoting_config, check_type): [
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


def check_property_required(model_name: str, field_name: str, quoting_config: QuotingConfig = QuotingConfig()):
    if quoting_config.quote_field_name:
        field_name_for_soda = f'"{field_name}"'
    else:
        field_name_for_soda = field_name

    check_type = "field_required"
    check_key = f"{model_name}__{field_name}__{check_type}"
    sodacl_check_dict = {
        checks_for(model_name, quoting_config, check_type): [
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


def check_property_unique(model_name: str, field_name: str, quoting_config: QuotingConfig = QuotingConfig()):
    if quoting_config.quote_field_name:
        field_name_for_soda = f'"{field_name}"'
    else:
        field_name_for_soda = field_name

    check_type = "field_unique"
    check_key = f"{model_name}__{field_name}__{check_type}"
    sodacl_check_dict = {
        checks_for(model_name, quoting_config, check_type): [
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


def check_property_min_length(
    model_name: str, field_name: str, min_length: int, quoting_config: QuotingConfig = QuotingConfig()
):
    if quoting_config.quote_field_name:
        field_name_for_soda = f'"{field_name}"'
    else:
        field_name_for_soda = field_name

    check_type = "field_min_length"
    check_key = f"{model_name}__{field_name}__{check_type}"
    sodacl_check_dict = {
        checks_for(model_name, quoting_config, check_type): [
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


def check_property_max_length(
    model_name: str, field_name: str, max_length: int, quoting_config: QuotingConfig = QuotingConfig()
):
    if quoting_config.quote_field_name:
        field_name_for_soda = f'"{field_name}"'
    else:
        field_name_for_soda = field_name

    check_type = "field_max_length"
    check_key = f"{model_name}__{field_name}__{check_type}"
    sodacl_check_dict = {
        checks_for(model_name, quoting_config, check_type): [
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


def check_property_minimum(
    model_name: str, field_name: str, minimum: int, quoting_config: QuotingConfig = QuotingConfig()
):
    if quoting_config.quote_field_name:
        field_name_for_soda = f'"{field_name}"'
    else:
        field_name_for_soda = field_name

    check_type = "field_minimum"
    check_key = f"{model_name}__{field_name}__{check_type}"
    sodacl_check_dict = {
        checks_for(model_name, quoting_config, check_type): [
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


def check_property_maximum(
    model_name: str, field_name: str, maximum: int, quoting_config: QuotingConfig = QuotingConfig()
):
    if quoting_config.quote_field_name:
        field_name_for_soda = f'"{field_name}"'
    else:
        field_name_for_soda = field_name

    check_type = "field_maximum"
    check_key = f"{model_name}__{field_name}__{check_type}"
    sodacl_check_dict = {
        checks_for(model_name, quoting_config, check_type): [
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


def check_property_not_equal(
    model_name: str, field_name: str, value: int, quoting_config: QuotingConfig = QuotingConfig()
):
    if quoting_config.quote_field_name:
        field_name_for_soda = f'"{field_name}"'
    else:
        field_name_for_soda = field_name

    check_type = "field_not_equal"
    check_key = f"{model_name}__{field_name}__{check_type}"
    sodacl_check_dict = {
        checks_for(model_name, quoting_config, check_type): [
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


def check_property_enum(model_name: str, field_name: str, enum: list, quoting_config: QuotingConfig = QuotingConfig()):
    if quoting_config.quote_field_name:
        field_name_for_soda = f'"{field_name}"'
    else:
        field_name_for_soda = field_name

    check_type = "field_enum"
    check_key = f"{model_name}__{field_name}__{check_type}"
    sodacl_check_dict = {
        checks_for(model_name, quoting_config, check_type): [
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


def check_property_regex(model_name: str, field_name: str, pattern: str, quoting_config: QuotingConfig = QuotingConfig()):
    if quoting_config.quote_field_name:
        field_name_for_soda = f'"{field_name}"'
    else:
        field_name_for_soda = field_name

    check_type = "field_regex"
    check_key = f"{model_name}__{field_name}__{check_type}"
    sodacl_check_dict = {
        checks_for(model_name, quoting_config, check_type): [
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


def check_row_count(model_name: str, threshold: str, quoting_config: QuotingConfig = QuotingConfig()):
    check_type = "row_count"
    check_key = f"{model_name}__{check_type}"
    sodacl_check_dict = {
        checks_for(model_name, quoting_config, check_type): [
            {
                f"row_count {threshold}": {"name": check_key},
            }
        ],
    }
    return Check(
        id=str(uuid.uuid4()),
        key=check_key,
        category="schema",
        type=check_type,
        name=f"Check that model {model_name} has row_count {threshold}",
        model=model_name,
        field=None,
        engine="soda",
        language="sodacl",
        implementation=yaml.dump(sodacl_check_dict),
    )


def check_model_duplicate_values(
    model_name: str, cols: list[str], threshold: str, quoting_config: QuotingConfig = QuotingConfig()
):
    check_type = "model_duplicate_values"
    check_key = f"{model_name}__{check_type}"
    col_joined = ", ".join(cols)
    sodacl_check_dict = {
        checks_for(model_name, quoting_config, check_type): [
            {
                f"duplicate_count({col_joined}) {threshold}": {"name": check_key},
            }
        ],
    }
    return Check(
        id=str(uuid.uuid4()),
        key=check_key,
        category="quality",
        type=check_type,
        name=f"Check that model {model_name} has duplicate_count {threshold} for columns {col_joined}",
        model=model_name,
        field=None,
        engine="soda",
        language="sodacl",
        implementation=yaml.dump(sodacl_check_dict),
    )


def check_property_duplicate_values(
    model_name: str, field_name: str, threshold: str, quoting_config: QuotingConfig = QuotingConfig()
):
    if quoting_config.quote_field_name:
        field_name_for_soda = f'"{field_name}"'
    else:
        field_name_for_soda = field_name

    check_type = "field_duplicate_values"
    check_key = f"{model_name}__{field_name}__{check_type}"
    sodacl_check_dict = {
        checks_for(model_name, quoting_config, check_type): [
            {
                f"duplicate_count({field_name_for_soda}) {threshold}": {
                    "name": check_key,
                },
            }
        ],
    }
    return Check(
        id=str(uuid.uuid4()),
        key=check_key,
        category="quality",
        type=check_type,
        name=f"Check that field {field_name} has duplicate_count {threshold}",
        model=model_name,
        field=field_name,
        engine="soda",
        language="sodacl",
        implementation=yaml.dump(sodacl_check_dict),
    )


def check_property_null_values(
    model_name: str, field_name: str, threshold: str, quoting_config: QuotingConfig = QuotingConfig()
):
    if quoting_config.quote_field_name:
        field_name_for_soda = f'"{field_name}"'
    else:
        field_name_for_soda = field_name

    check_type = "field_null_values"
    check_key = f"{model_name}__{field_name}__{check_type}"
    sodacl_check_dict = {
        checks_for(model_name, quoting_config, check_type): [
            {
                f"missing_count({field_name_for_soda}) {threshold}": {
                    "name": check_key,
                },
            }
        ],
    }
    return Check(
        id=str(uuid.uuid4()),
        key=check_key,
        category="quality",
        type=check_type,
        name=f"Check that field {field_name} has missing_count {threshold}",
        model=model_name,
        field=field_name,
        engine="soda",
        language="sodacl",
        implementation=yaml.dump(sodacl_check_dict),
    )


def check_property_invalid_values(
    model_name: str,
    field_name: str,
    threshold: str,
    valid_values: list = None,
    quoting_config: QuotingConfig = QuotingConfig(),
):
    if quoting_config.quote_field_name:
        field_name_for_soda = f'"{field_name}"'
    else:
        field_name_for_soda = field_name

    check_type = "field_invalid_values"
    check_key = f"{model_name}__{field_name}__{check_type}"

    sodacl_check_config = {
        "name": check_key,
    }

    if valid_values is not None:
        sodacl_check_config["valid values"] = valid_values

    sodacl_check_dict = {
        checks_for(model_name, quoting_config, check_type): [
            {
                f"invalid_count({field_name_for_soda}) {threshold}": sodacl_check_config,
            }
        ],
    }
    return Check(
        id=str(uuid.uuid4()),
        key=check_key,
        category="quality",
        type=check_type,
        name=f"Check that field {field_name} has invalid_count {threshold}",
        model=model_name,
        field=field_name,
        engine="soda",
        language="sodacl",
        implementation=yaml.dump(sodacl_check_dict),
    )


def check_property_missing_values(
    model_name: str,
    field_name: str,
    threshold: str,
    missing_values: list = None,
    quoting_config: QuotingConfig = QuotingConfig(),
):
    if quoting_config.quote_field_name:
        field_name_for_soda = f'"{field_name}"'
    else:
        field_name_for_soda = field_name

    check_type = "field_missing_values"
    check_key = f"{model_name}__{field_name}__{check_type}"

    sodacl_check_config = {
        "name": check_key,
    }

    if missing_values is not None:
        filtered_missing_values = [v for v in missing_values if v is not None]
        if filtered_missing_values:
            sodacl_check_config["missing values"] = filtered_missing_values

    sodacl_check_dict = {
        checks_for(model_name, quoting_config, check_type): [
            {
                f"missing_count({field_name_for_soda}) {threshold}": sodacl_check_config,
            }
        ],
    }
    return Check(
        id=str(uuid.uuid4()),
        key=check_key,
        category="quality",
        type=check_type,
        name=f"Check that field {field_name} has missing_count {threshold}",
        model=model_name,
        field=field_name,
        engine="soda",
        language="sodacl",
        implementation=yaml.dump(sodacl_check_dict),
    )


def check_quality_list(
    schema_name,
    property_name,
    quality_list: List[DataQuality],
    quoting_config: QuotingConfig = QuotingConfig(),
    server: Server = None,
) -> List[Check]:
    checks: List[Check] = []

    count = 0
    for quality in quality_list:
        if quality.type == "custom" and quality.engine == "soda" and quality.implementation:
            # Custom SodaCL quality check with raw implementation
            check_key = f"{schema_name}__quality_custom_{count}"
            check_type = "quality_custom_soda"
            checks.append(
                Check(
                    id=str(uuid.uuid4()),
                    key=check_key,
                    category="quality",
                    type=check_type,
                    name=quality.description if quality.description is not None else "Custom SodaCL Check",
                    model=schema_name,
                    field=property_name,
                    engine="soda",
                    language="sodacl",
                    implementation=quality.implementation,
                )
            )
        elif quality.type == "sql":
            if property_name is None:
                check_key = f"{schema_name}__quality_sql_{count}"
                check_type = "field_quality_sql"
            else:
                check_key = f"{schema_name}__{property_name}__quality_sql_{count}"
                check_type = "model_quality_sql"
            threshold = to_sodacl_threshold(quality)
            query = prepare_query(quality, schema_name, property_name, quoting_config, server)
            if query is None:
                logger.warning(f"Quality check {check_key} has no query")
                continue
            if threshold is None:
                logger.warning(f"Quality check {check_key} has no valid threshold")
                continue

            if quoting_config.quote_model_name:
                model_name_for_soda = f'"{schema_name}"'
            else:
                model_name_for_soda = schema_name
            sodacl_check_dict = {
                f"checks for {model_name_for_soda}": [
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
                    model=schema_name,
                    field=property_name,
                    engine="soda",
                    language="sodacl",
                    implementation=yaml.dump(sodacl_check_dict),
                )
            )
        elif quality.metric is not None:
            threshold = to_sodacl_threshold(quality)

            if threshold is None:
                logger.warning(f"Quality metric {quality.metric} has no valid threshold")
                continue

            if quality.metric == "rowCount":
                checks.append(check_row_count(schema_name, threshold, quoting_config))
            elif quality.metric == "duplicateValues":
                if property_name is None:
                    checks.append(
                        check_model_duplicate_values(
                            schema_name, quality.arguments.get("properties"), threshold, quoting_config
                        )
                    )
                else:
                    checks.append(check_property_duplicate_values(schema_name, property_name, threshold, quoting_config))
            elif quality.metric == "nullValues":
                if property_name is not None:
                    checks.append(check_property_null_values(schema_name, property_name, threshold, quoting_config))
                else:
                    logger.warning("Quality check nullValues is only supported at field level")
            elif quality.metric == "invalidValues":
                if property_name is not None:
                    valid_values = quality.arguments.get("validValues") if quality.arguments else None
                    checks.append(
                        check_property_invalid_values(schema_name, property_name, threshold, valid_values, quoting_config)
                    )
                else:
                    logger.warning("Quality check invalidValues is only supported at field level")
            elif quality.metric == "missingValues":
                if property_name is not None:
                    missing_values = quality.arguments.get("missingValues") if quality.arguments else None
                    checks.append(
                        check_property_missing_values(schema_name, property_name, threshold, missing_values, quoting_config)
                    )
                else:
                    logger.warning("Quality check missingValues is only supported at field level")
            else:
                logger.warning(f"Quality check {quality.metric} is not yet supported")

        count += 1

    return checks


def prepare_query(
    quality: DataQuality,
    model_name: str,
    field_name: str = None,
    quoting_config: QuotingConfig = QuotingConfig(),
    server: Server = None,
) -> str | None:
    if quality.query is None:
        return None
    if quality.query == "":
        return None

    query = quality.query

    if quoting_config.quote_field_name:
        field_name_for_soda = f'"{field_name}"'
    else:
        field_name_for_soda = field_name

    if quoting_config.quote_model_name:
        model_name_for_soda = f'"{model_name}"'
    elif quoting_config.quote_model_name_with_backticks:
        model_name_for_soda = f"`{model_name}`"
    else:
        model_name_for_soda = model_name

    query = re.sub(r'["\']?\$?\{model}["\']?', model_name_for_soda, query)
    query = re.sub(r'["\']?\$?\{table}["\']?', model_name_for_soda, query)

    if server and server.schema_:
        if quoting_config.quote_model_name:
            schema_name_for_soda = f'"{server.schema_}"'
        elif quoting_config.quote_model_name_with_backticks:
            schema_name_for_soda = f"`{server.schema_}`"
        else:
            schema_name_for_soda = server.schema_
        query = re.sub(r'["\']?\$?\{schema}["\']?', schema_name_for_soda, query)
    else:
        query = re.sub(r'["\']?\$?\{schema}["\']?', model_name_for_soda, query)

    if field_name is not None:
        query = re.sub(r'["\']?\$?\{field}["\']?', field_name_for_soda, query)
        query = re.sub(r'["\']?\$?\{column}["\']?', field_name_for_soda, query)
        query = re.sub(r'["\']?\$?\{property}["\']?', field_name_for_soda, query)

    return query


def to_sodacl_threshold(quality: DataQuality) -> str | None:
    if quality.mustBe is not None:
        return f"= {quality.mustBe}"
    if quality.mustNotBe is not None:
        return f"!= {quality.mustNotBe}"
    if quality.mustBeGreaterThan is not None:
        return f"> {quality.mustBeGreaterThan}"
    if quality.mustBeGreaterOrEqualTo is not None:
        return f">= {quality.mustBeGreaterOrEqualTo}"
    if quality.mustBeLessThan is not None:
        return f"< {quality.mustBeLessThan}"
    if quality.mustBeLessOrEqualTo is not None:
        return f"<= {quality.mustBeLessOrEqualTo}"
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


def _get_schema_by_name(data_contract: OpenDataContractStandard, name: str) -> Optional[SchemaObject]:
    """Get a schema object by name from the data contract."""
    if data_contract.schema_ is None:
        return None
    return next((s for s in data_contract.schema_ if s.name == name), None)


def to_servicelevel_checks(data_contract: OpenDataContractStandard) -> List[Check]:
    checks: List[Check] = []
    if data_contract.slaProperties is None:
        return checks

    for sla in data_contract.slaProperties:
        if sla.property == "freshness":
            check = to_sla_freshness_check(data_contract, sla)
            if check is not None:
                checks.append(check)
        elif sla.property == "retention":
            check = to_servicelevel_retention_check(data_contract, sla)
            if check is not None:
                checks.append(check)

    return checks


def to_sla_freshness_check(data_contract: OpenDataContractStandard, sla) -> Check | None:
    """Create a freshness check from an ODCS latency SLA property."""
    if sla.element is None:
        logger.info("slaProperties.latency.element is not defined, skipping freshness check")
        return None

    if sla.value is None:
        logger.info("slaProperties.latency.value is not defined, skipping freshness check")
        return None

    # Parse element to get model and field (e.g., "my_table.field_three")
    element = sla.element
    if "." not in element:
        logger.info("slaProperties.latency.element is not fully qualified (model.field), skipping freshness check")
        return None

    if element.count(".") > 1:
        logger.info("slaProperties.latency.element contains multiple dots, which is currently not supported")
        return None

    model_name = element.split(".")[0]
    field_name = element.split(".")[1]

    # Verify the model exists
    schema = _get_schema_by_name(data_contract, model_name)
    if schema is None:
        logger.info(f"Model {model_name} not found in schema, skipping freshness check")
        return None

    # Build threshold from value and unit
    unit = sla.unit.lower() if sla.unit else "d"
    value = sla.value

    # Normalize unit to soda format (d, h, m)
    if unit in ["d", "day", "days"]:
        threshold = f"{value}d"
    elif unit in ["h", "hr", "hour", "hours"]:
        threshold = f"{value}h"
    elif unit in ["m", "min", "minute", "minutes"]:
        threshold = f"{value}m"
    else:
        logger.info(f"Unsupported unit {unit} for freshness check, must be days, hours, or minutes")
        return None

    check_type = "servicelevel_freshness"
    check_key = "servicelevel_freshness"
    sodacl_check_dict = {
        f"checks for {model_name}": [
            {
                f"freshness({field_name}) < {threshold}": {
                    "name": check_key,
                },
            }
        ],
    }
    return Check(
        id=str(uuid.uuid4()),
        key=check_key,
        category="servicelevel",
        type=check_type,
        name=f"Freshness of {model_name}.{field_name} < {threshold}",
        model=model_name,
        field=field_name,
        engine="soda",
        language="sodacl",
        implementation=yaml.dump(sodacl_check_dict),
    )


def to_servicelevel_retention_check(data_contract: OpenDataContractStandard, sla) -> Check | None:
    """Create a retention check from an ODCS retention SLA property."""
    if sla.element is None:
        logger.info("slaProperties.retention.element is not defined, skipping retention check")
        return None

    if sla.value is None:
        logger.info("slaProperties.retention.value is not defined, skipping retention check")
        return None

    # Parse element to get model and field (e.g., "orders.processed_timestamp")
    element = sla.element
    if "." not in element:
        logger.info("slaProperties.retention.element is not fully qualified (model.field), skipping retention check")
        return None

    if element.count(".") > 1:
        logger.info("slaProperties.retention.element contains multiple dots, which is currently not supported")
        return None

    model_name = element.split(".")[0]
    field_name = element.split(".")[1]

    # Verify the model exists
    schema = _get_schema_by_name(data_contract, model_name)
    if schema is None:
        logger.info(f"Model {model_name} not found in schema, skipping retention check")
        return None

    # Parse ISO 8601 duration to seconds
    retention_period = sla.value
    seconds = _parse_iso8601_to_seconds(retention_period)
    if seconds is None:
        logger.info(f"Could not parse retention period {retention_period}, skipping retention check")
        return None

    check_type = "servicelevel_retention"
    check_key = "servicelevel_retention"
    sodacl_check_dict = {
        f"checks for {model_name}": [
            {
                f"{model_name}_servicelevel_retention < {seconds}": {
                    "name": check_key,
                    f"{model_name}_servicelevel_retention expression": f"TIMESTAMPDIFF(SECOND, MIN({field_name}), CURRENT_TIMESTAMP)",
                },
            }
        ],
    }
    return Check(
        id=str(uuid.uuid4()),
        key=check_key,
        category="servicelevel",
        type=check_type,
        name=f"Retention of {model_name}.{field_name} < {seconds}s",
        model=model_name,
        field=field_name,
        engine="soda",
        language="sodacl",
        implementation=yaml.dump(sodacl_check_dict),
    )


def _parse_iso8601_to_seconds(duration: str) -> int | None:
    """Parse ISO 8601 duration to seconds."""
    if not duration:
        return None

    duration = duration.upper()

    # Simple patterns: P1Y, P1M, P1D, PT1H, PT1M, PT1S
    # For simplicity, we support only single unit durations
    import re

    # Year
    match = re.match(r"P(\d+)Y", duration)
    if match:
        return int(match.group(1)) * 365 * 24 * 60 * 60

    # Month (approximate as 30 days)
    match = re.match(r"P(\d+)M", duration)
    if match:
        return int(match.group(1)) * 30 * 24 * 60 * 60

    # Day
    match = re.match(r"P(\d+)D", duration)
    if match:
        return int(match.group(1)) * 24 * 60 * 60

    # Hour
    match = re.match(r"PT(\d+)H", duration)
    if match:
        return int(match.group(1)) * 60 * 60

    # Minute
    match = re.match(r"PT(\d+)M", duration)
    if match:
        return int(match.group(1)) * 60

    # Second
    match = re.match(r"PT(\d+)S", duration)
    if match:
        return int(match.group(1))

    return None

