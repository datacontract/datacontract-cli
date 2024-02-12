from array import array
from typing import Dict

import yaml

from datacontract.model.data_contract_specification import \
    DataContractSpecification, Model, Field


def to_dbt(data_contract_spec: DataContractSpecification):
    dbt = {
        "version": 2,
        "models": [],
    }
    for model_key, model_value in data_contract_spec.models.items():
        dbt_model = to_dbt_model(model_key, model_value)
        dbt["models"].append(dbt_model)
    return yaml.dump(dbt, indent=2)


def to_dbt_model(model_key, model_value: Model) -> dict:
    dbt_model = {
        "name": model_key,
    }
    model_type = model_value.type or "table" # TODO where to define the default? should be in the spec
    dbt_model["config"] = {}
    dbt_model["config"]["materialized"] = model_type

    if supports_constraints(model_type):
        dbt_model["config"]["contract"] = {
            "enforced": True
        }
    if model_value.description is not None:
        dbt_model["description"] = model_value.description
    columns = to_columns(model_value.fields, model_value.type)
    if columns:
        dbt_model["columns"] = columns
    return dbt_model


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
    dbt_type = convert_type(field.type)
    if dbt_type is not None:
        column["data_type"] = dbt_type
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

    # TODO: all constraints
    return column


def convert_type(type) -> None | str:
    if type is None:
        return None
    if type.lower() in ["string", "varchar", "text"]:
        return "text"
    if type.lower() in ["timestamp", "timestamp_tz", "date-time", "datetime"]:
        return "timestamp"
    if type.lower() in ["timestamp_ntz"]:
        return "string"
    if type.lower() in ["date"]:
        return "date"
    if type.lower() in ["time"]:
        return "time"
    if type.lower() in ["number", "decimal", "numeric", "float", "double"]:
        return "number"
    if type.lower() in ["integer", "int", "long", "bigint"]:
        return "integer"
    if type.lower() in ["boolean"]:
        return "boolean"
    if type.lower() in ["object", "record", "struct"]:
        return None
    if type.lower() in ["array"]:
        return "array"
    return None
