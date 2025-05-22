from typing import Dict, Optional

import yaml

from datacontract.export.exporter import Exporter, _check_models_for_export
from datacontract.export.sql_type_converter import convert_to_sql_type
from datacontract.model.data_contract_specification import DataContractSpecification, Field, Model


class DbtExporter(Exporter):
    def export(self, data_contract, model, server, sql_server_type, export_args) -> dict:
        return to_dbt_models_yaml(data_contract, server)


class DbtSourceExporter(Exporter):
    def export(self, data_contract, model, server, sql_server_type, export_args) -> dict:
        return to_dbt_sources_yaml(data_contract, server)


class DbtStageExporter(Exporter):
    def export(self, data_contract, model, server, sql_server_type, export_args) -> dict:
        model_name, model_value = _check_models_for_export(data_contract, model, self.export_format)
        return to_dbt_staging_sql(
            data_contract,
            model_name,
            model_value,
        )


def to_dbt_models_yaml(data_contract_spec: DataContractSpecification, server: str = None) -> str:
    dbt = {
        "version": 2,
        "models": [],
    }

    for model_key, model_value in data_contract_spec.models.items():
        dbt_model = _to_dbt_model(model_key, model_value, data_contract_spec, adapter_type=server)
        dbt["models"].append(dbt_model)
    return yaml.safe_dump(dbt, indent=2, sort_keys=False, allow_unicode=True)


def to_dbt_staging_sql(data_contract_spec: DataContractSpecification, model_name: str, model_value: Model) -> str:
    id = data_contract_spec.id
    columns = []
    for field_name, field in model_value.fields.items():
        # TODO escape SQL reserved key words, probably dependent on server type
        columns.append(field_name)
    return f"""
    select
        {", ".join(columns)}
    from {{{{ source('{id}', '{model_name}') }}}}
"""


def to_dbt_sources_yaml(data_contract_spec: DataContractSpecification, server: str = None):
    source = {"name": data_contract_spec.id}
    dbt = {
        "version": 2,
        "sources": [source],
    }
    if data_contract_spec.info.owner is not None:
        source["meta"] = {"owner": data_contract_spec.info.owner}
    if data_contract_spec.info.description is not None:
        source["description"] = data_contract_spec.info.description.strip().replace("\n", " ")
    found_server = data_contract_spec.servers.get(server)
    adapter_type = None
    if found_server is not None:
        adapter_type = found_server.type
        if adapter_type == "bigquery":
            source["database"] = found_server.project
            source["schema"] = found_server.dataset
        else:
            source["database"] = found_server.database
            source["schema"] = found_server.schema_

    source["tables"] = []
    for model_key, model_value in data_contract_spec.models.items():
        dbt_model = _to_dbt_source_table(data_contract_spec, model_key, model_value, adapter_type)
        source["tables"].append(dbt_model)
    return yaml.dump(dbt, indent=2, sort_keys=False, allow_unicode=True)


def _to_dbt_source_table(
    data_contract_spec: DataContractSpecification, model_key, model_value: Model, adapter_type: Optional[str]
) -> dict:
    dbt_model = {
        "name": model_key,
    }

    if model_value.description is not None:
        dbt_model["description"] = model_value.description.strip().replace("\n", " ")
    columns = _to_columns(data_contract_spec, model_value.fields, False, adapter_type)
    if columns:
        dbt_model["columns"] = columns
    return dbt_model


def _to_dbt_model(
    model_key, model_value: Model, data_contract_spec: DataContractSpecification, adapter_type: Optional[str]
) -> dict:
    dbt_model = {
        "name": model_key,
    }
    model_type = _to_dbt_model_type(model_value.type)

    dbt_model["config"] = {"meta": {"data_contract": data_contract_spec.id}}

    if model_type:
        dbt_model["config"]["materialized"] = model_type

    if data_contract_spec.info.owner is not None:
        dbt_model["config"]["meta"]["owner"] = data_contract_spec.info.owner

    if _supports_constraints(model_type):
        dbt_model["config"]["contract"] = {"enforced": True}
    if model_value.description is not None:
        dbt_model["description"] = model_value.description.strip().replace("\n", " ")
    columns = _to_columns(data_contract_spec, model_value.fields, _supports_constraints(model_type), adapter_type)
    if columns:
        dbt_model["columns"] = columns
    return dbt_model


def _to_dbt_model_type(model_type):
    # https://docs.getdbt.com/docs/build/materializations
    # Allowed values: table, view, incremental, ephemeral, materialized view
    # Custom values also possible
    if model_type is None:
        return None
    if model_type.lower() == "table":
        return "table"
    if model_type.lower() == "view":
        return "view"
    return "table"


def _supports_constraints(model_type):
    return model_type == "table" or model_type == "incremental"


def _to_columns(
    data_contract_spec: DataContractSpecification,
    fields: Dict[str, Field],
    supports_constraints: bool,
    adapter_type: Optional[str],
) -> list:
    columns = []
    for field_name, field in fields.items():
        column = _to_column(data_contract_spec, field_name, field, supports_constraints, adapter_type)
        columns.append(column)
    return columns


def get_table_name_and_column_name(references: str) -> tuple[Optional[str], str]:
    parts = references.split(".")
    if len(parts) < 2:
        return None, parts[0]
    return parts[-2], parts[-1]


def _to_column(
    data_contract_spec: DataContractSpecification,
    field_name: str,
    field: Field,
    supports_constraints: bool,
    adapter_type: Optional[str],
) -> dict:
    column = {"name": field_name}
    adapter_type = adapter_type or "snowflake"
    dbt_type = convert_to_sql_type(field, adapter_type)

    column["data_tests"] = []
    if dbt_type is not None:
        column["data_type"] = dbt_type
    else:
        column["data_tests"].append(
            {"dbt_expectations.dbt_expectations.expect_column_values_to_be_of_type": {"column_type": dbt_type}}
        )
    if field.description is not None:
        column["description"] = field.description.strip().replace("\n", " ")
    if field.required:
        if supports_constraints:
            column.setdefault("constraints", []).append({"type": "not_null"})
        else:
            column["data_tests"].append("not_null")
    if field.unique:
        if supports_constraints:
            column.setdefault("constraints", []).append({"type": "unique"})
        else:
            column["data_tests"].append("unique")
    if field.enum is not None and len(field.enum) > 0:
        column["data_tests"].append({"accepted_values": {"values": field.enum}})
    if field.minLength is not None or field.maxLength is not None:
        length_test = {}
        if field.minLength is not None:
            length_test["min_value"] = field.minLength
        if field.maxLength is not None:
            length_test["max_value"] = field.maxLength
        column["data_tests"].append({"dbt_expectations.expect_column_value_lengths_to_be_between": length_test})
    if field.pii is not None:
        column.setdefault("meta", {})["pii"] = field.pii
    if field.classification is not None:
        column.setdefault("meta", {})["classification"] = field.classification
    if field.tags is not None and len(field.tags) > 0:
        column.setdefault("tags", []).extend(field.tags)
    if field.pattern is not None:
        # Beware, the data contract pattern is a regex, not a like pattern
        column["data_tests"].append({"dbt_expectations.expect_column_values_to_match_regex": {"regex": field.pattern}})
    if (
        field.minimum is not None
        or field.maximum is not None
        and field.exclusiveMinimum is None
        and field.exclusiveMaximum is None
    ):
        range_test = {}
        if field.minimum is not None:
            range_test["min_value"] = field.minimum
        if field.maximum is not None:
            range_test["max_value"] = field.maximum
        column["data_tests"].append({"dbt_expectations.expect_column_values_to_be_between": range_test})
    elif (
        field.exclusiveMinimum is not None
        or field.exclusiveMaximum is not None
        and field.minimum is None
        and field.maximum is None
    ):
        range_test = {}
        if field.exclusiveMinimum is not None:
            range_test["min_value"] = field.exclusiveMinimum
        if field.exclusiveMaximum is not None:
            range_test["max_value"] = field.exclusiveMaximum
        range_test["strictly"] = True
        column["data_tests"].append({"dbt_expectations.expect_column_values_to_be_between": range_test})
    else:
        if field.minimum is not None:
            column["data_tests"].append(
                {"dbt_expectations.expect_column_values_to_be_between": {"min_value": field.minimum}}
            )
        if field.maximum is not None:
            column["data_tests"].append(
                {"dbt_expectations.expect_column_values_to_be_between": {"max_value": field.maximum}}
            )
        if field.exclusiveMinimum is not None:
            column["data_tests"].append(
                {
                    "dbt_expectations.expect_column_values_to_be_between": {
                        "min_value": field.exclusiveMinimum,
                        "strictly": True,
                    }
                }
            )
        if field.exclusiveMaximum is not None:
            column["data_tests"].append(
                {
                    "dbt_expectations.expect_column_values_to_be_between": {
                        "max_value": field.exclusiveMaximum,
                        "strictly": True,
                    }
                }
            )
    if field.references is not None:
        ref_source_name = data_contract_spec.id
        table_name, column_name = get_table_name_and_column_name(field.references)
        if table_name is not None and column_name is not None:
            column["data_tests"].append(
                {
                    "relationships": {
                        "to": f"""source("{ref_source_name}", "{table_name}")""",
                        "field": f"{column_name}",
                    }
                }
            )

    if not column["data_tests"]:
        column.pop("data_tests")

    # TODO: all constraints
    return column
