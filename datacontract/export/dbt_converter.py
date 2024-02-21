from typing import Dict

import yaml

from datacontract.model.data_contract_specification import \
    DataContractSpecification, Model, Field


# snowflake data types:
# https://docs.snowflake.com/en/sql-reference/data-types.html


def to_dbt(data_contract_spec: DataContractSpecification):
    dbt = {
        "version": 2,
        "models": [],
    }
    for model_key, model_value in data_contract_spec.models.items():
        dbt_model = to_dbt_model(model_key, model_value)
        dbt["models"].append(dbt_model)
    return yaml.dump(dbt, indent=2, sort_keys=False)


def to_dbt_model(model_key, model_value: Model) -> dict:
    dbt_model = {
        "name": model_key,
    }
    model_type = to_dbt_model_type(model_value.type)
    dbt_model["config"] = {}
    dbt_model["config"]["materialized"] = model_type

    if supports_constraints(model_type):
        dbt_model["config"]["contract"] = {
            "enforced": True
        }
    if model_value.description is not None:
        dbt_model["description"] = model_value.description
    columns = to_columns(model_value.fields, model_type)
    if columns:
        dbt_model["columns"] = columns
    return dbt_model


def to_dbt_model_type(model_type):
    # https://docs.getdbt.com/docs/build/materializations
    # Allowed values: table, view, incremental, ephemeral, materialized view
    # Custom values also possible
    if model_type is None:
        return "table"
    if model_type.lower() == "table":
        return "table"
    if model_type.lower() == "view":
        return "view"
    return "table"


def supports_constraints(model_type):
    return model_type == "table" or model_type == "incremental"


def to_columns(fields: Dict[str, Field], model_type: str) -> list:
    columns = []
    for field_name, field in fields.items():
        column = to_column(field, model_type)
        column["name"] = field_name
        columns.append(column)
    return columns


def to_column(field: Field, model_type: str) -> dict:
    column = {}
    dbt_type = convert_type_to_snowflake(field.type)
    if dbt_type is not None:
        column["data_type"] = dbt_type
    if field.description is not None:
        column["description"] = field.description
    if field.required:
        if supports_constraints(model_type):
            column.setdefault("constraints", []).append({"type": "not_null"})
        else:
            column.setdefault("tests", []).append("not_null")
    if field.unique:
        if supports_constraints(model_type):
            column.setdefault("constraints", []).append({"type": "unique"})
        else:
            column.setdefault("tests", []).append("unique")
    if field.enum is not None and len(field.enum) > 0:
        column.setdefault("tests", []).append({"accepted_values": {"values": field.enum}})
    if field.minLength is not None or field.maxLength is not None:
        length_test = {}
        if field.minLength is not None:
            length_test["min_value"] = field.minLength
        if field.maxLength is not None:
            length_test["max_value"] = field.maxLength
        column.setdefault("tests", []).append({"dbt_expectations.expect_column_value_lengths_to_be_between": length_test})
    if field.pii is not None:
        column.setdefault("meta", {})["pii"] = field.pii
    if field.classification is not None:
        column.setdefault("meta", {})["classification"] = field.classification
    if field.tags is not None and len(field.tags) > 0:
        column.setdefault("tags", []).extend(field.tags)
    if field.pattern is not None:
        # Beware, the data contract pattern is a regex, not a like pattern
        column.setdefault("tests", []).append({"dbt_expectations.expect_column_values_to_match_regex": {"regex": field.pattern}})
    if field.minimum is not None or field.maximum is not None and field.minimumExclusive is None and field.maximumExclusive is None:
        range_test = {}
        if field.minimum is not None:
            range_test["min_value"] = field.minimum
        if field.maximum is not None:
            range_test["max_value"] = field.maximum
        column.setdefault("tests", []).append({"dbt_expectations.expect_column_values_to_be_between": range_test})
    elif field.minimumExclusive is not None or field.maximumExclusive is not None and field.minimum is None and field.maximum is None:
        range_test = {}
        if field.minimumExclusive is not None:
            range_test["min_value"] = field.minimumExclusive
        if field.maximumExclusive is not None:
            range_test["max_value"] = field.maximumExclusive
        range_test["strictly"] = True
        column.setdefault("tests", []).append({"dbt_expectations.expect_column_values_to_be_between": range_test})
    else:
        if field.minimum is not None:
            column.setdefault("tests", []).append({"dbt_expectations.expect_column_values_to_be_between": {"min_value": field.minimum}})
        if field.maximum is not None:
            column.setdefault("tests", []).append({"dbt_expectations.expect_column_values_to_be_between": {"max_value": field.maximum}})
        if field.minimumExclusive is not None:
            column.setdefault("tests", []).append({"dbt_expectations.expect_column_values_to_be_between": {"min_value": field.minimumExclusive, "strictly": True}})
        if field.maximumExclusive is not None:
            column.setdefault("tests", []).append({"dbt_expectations.expect_column_values_to_be_between": {"max_value": field.maximumExclusive, "strictly": True}})

    # TODO: all constraints
    return column


def convert_type_to_snowflake(type) -> None | str:
    # currently optimized for snowflake
    # LEARNING: data contract has no direct support for CHAR,CHARACTER
    # LEARNING: data contract has no support for "date-time", "datetime", "time"
    # LEARNING: No precision and scale support in data contract
    # LEARNING: no support for any
    # GEOGRAPHY and GEOMETRY are not supported by the mapping
    if type is None:
        return None
    if type.lower() in ["string", "varchar", "text"]:
        return type.upper() # STRING, TEXT, VARCHAR are all the same in snowflake
    if type.lower() in ["timestamp", "timestamp_tz"]:
        return "TIMESTAMP_TZ"
    if type.lower() in ["timestamp_ntz"]:
        return "TIMESTAMP_NTZ"
    if type.lower() in ["date"]:
        return "DATE"
    if type.lower() in ["time"]:
        return "TIME"
    if type.lower() in ["number", "decimal", "numeric"]:
        return "NUMBER" # precision and scale not supported by data contract
    if type.lower() in [ "float", "double"]:
        return "FLOAT"
    if type.lower() in ["integer", "int", "long", "bigint"]:
        return "NUMBER" # always NUMBER(38,0)
    if type.lower() in ["boolean"]:
        return "BOOLEAN"
    if type.lower() in ["object", "record", "struct"]:
        return "OBJECT"
    if type.lower() in ["bytes"]:
        return "BINARY"
    if type.lower() in ["array"]:
        return "ARRAY"
    return None
