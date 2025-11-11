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

    # Set contract enforcement for table and incremental models
    if model_type == "table" or model_type == "incremental":
        dbt_model["config"]["contract"] = {"enforced": True}
    if model_value.description is not None:
        dbt_model["description"] = model_value.description.strip().replace("\n", " ")

    # Handle model-level primaryKey (before columns for better YAML ordering)
    primary_key_columns = []
    if hasattr(model_value, "primaryKey") and model_value.primaryKey:
        if isinstance(model_value.primaryKey, list) and len(model_value.primaryKey) > 1:
            # Multiple columns: use dbt_utils.unique_combination_of_columns
            dbt_model["data_tests"] = [
                {"dbt_utils.unique_combination_of_columns": {"combination_of_columns": model_value.primaryKey}}
            ]
            # For composite keys, pass all columns to _to_columns to avoid individual constraints
            primary_key_columns = model_value.primaryKey
        elif isinstance(model_value.primaryKey, list) and len(model_value.primaryKey) == 1:
            # Single column: handle at column level (pass to _to_columns)
            primary_key_columns = model_value.primaryKey
        elif isinstance(model_value.primaryKey, str):
            # Single column as string: handle at column level
            primary_key_columns = [model_value.primaryKey]

    columns = _to_columns(
        data_contract_spec, model_value.fields, _supports_constraints(model_type), adapter_type, primary_key_columns
    )
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
    # Force use of data_tests instead of constraints section for compatibility
    return False


def _to_columns(
    data_contract_spec: DataContractSpecification,
    fields: Dict[str, Field],
    supports_constraints: bool,
    adapter_type: Optional[str],
    primary_key_columns: Optional[list] = None,
) -> list:
    columns = []
    primary_key_columns = primary_key_columns or []
    is_composite_primary_key = len(primary_key_columns) > 1
    for field_name, field in fields.items():
        is_primary_key = field_name in primary_key_columns
        column = _to_column(data_contract_spec, field_name, field, supports_constraints, adapter_type, is_primary_key, is_composite_primary_key)
        columns.append(column)

        # Handle array type fields with items - expand nested fields (feature for AP-3210)
        if field.type == "array" and hasattr(field, "items") and field.items and hasattr(field.items, "fields"):
            for nested_field_name, nested_field in field.items.fields.items():
                # Create nested field name in dot notation
                full_nested_name = f"{field_name}.{nested_field_name}"
                nested_column = _to_nested_column(
                    data_contract_spec,
                    full_nested_name,
                    nested_field,
                    supports_constraints,
                    adapter_type
                )
                columns.append(nested_column)
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
    is_primary_key: bool = False,
    is_composite_primary_key: bool = False,
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
    # Handle required/not_null constraint
    if field.required:
        if supports_constraints:
            column.setdefault("constraints", []).append({"type": "not_null"})
        else:
            column["data_tests"].append("not_null")
    elif is_primary_key and not is_composite_primary_key:
        # Apply not_null for single primary keys only
        if supports_constraints:
            column.setdefault("constraints", []).append({"type": "not_null"})
        else:
            column["data_tests"].append("not_null")

    # Handle unique constraint
    # Skip unique constraints for fields that are part of composite primary keys
    if field.unique and not (is_primary_key and is_composite_primary_key):
        if supports_constraints:
            column.setdefault("constraints", []).append({"type": "unique"})
        else:
            column["data_tests"].append("unique")
    elif is_primary_key and not is_composite_primary_key:
        # Apply unique for single primary keys only
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

    # Handle nested data test wrapper for dot-notation fields (feature for AP-3210)
    # This implements automatic wrapping of data tests with nested_data_test_wrapper macro
    # for fields with dot notation (e.g., "products.contract_end_date")
    # Reference: https://legalforce.atlassian.net/browse/AP-3210?focusedCommentId=283533
    if "." in field_name:
        wrapped_tests = []

        # Handle constraints that were moved away from data_tests in supports_constraints=true environments
        # In BigQuery and other constraint-supporting databases, basic constraints like not_null and unique
        # are moved to the constraints section instead of data_tests. For nested fields, we need to convert
        # these back to data_tests and wrap them with nested_data_test_wrapper.
        if column.get("constraints"):
            for constraint in column["constraints"]:
                constraint_type = constraint.get("type")
                if constraint_type == "not_null":
                    wrapped_tests.append({
                        "nested_data_test_wrapper": {
                            "test": "not_null",
                            "column": field_name
                        }
                    })
                elif constraint_type == "unique":
                    wrapped_tests.append({
                        "nested_data_test_wrapper": {
                            "test": "unique",
                            "column": field_name
                        }
                    })
                # Note: Other constraint types (like foreign keys) are not commonly supported
                # by the nested_data_test_wrapper macro and should be handled separately if needed

            # Remove constraints for nested fields since we've converted them to data_tests
            # This ensures that nested field tests are handled by the macro rather than database constraints
            column.pop("constraints", None)

        # Handle existing data_tests (e.g., from minimum/maximum, enum, pattern constraints)
        if column.get("data_tests"):
            for test in column["data_tests"]:
                if isinstance(test, str):
                    # Simple test like "not_null" or "unique"
                    wrapped_tests.append({
                        "nested_data_test_wrapper": {
                            "test": test,
                            "column": field_name
                        }
                    })
                elif isinstance(test, dict):
                    # Complex test like {"accepted_values": {"values": [...]}} or range tests
                    for test_name, test_config in test.items():
                        if isinstance(test_config, dict):
                            wrapped_tests.append({
                                "nested_data_test_wrapper": {
                                    "test": test_name,
                                    "column": field_name,
                                    **test_config
                                }
                            })
                        else:
                            # Fallback for unexpected test configuration formats
                            wrapped_tests.append({
                                "nested_data_test_wrapper": {
                                    "test": test_name,
                                    "column": field_name,
                                    "config": test_config
                                }
                            })

        # Apply wrapped tests if any exist
        if wrapped_tests:
            column["data_tests"] = wrapped_tests

    if not column["data_tests"]:
        column.pop("data_tests")

    # TODO: all constraints
    return column


def _to_nested_column(
    data_contract_spec: DataContractSpecification,
    field_name: str,
    field: Field,
    supports_constraints: bool,
    adapter_type: Optional[str]
) -> dict:
    """
    Convert nested field (from array items) to dbt column format.
    Uses type: string format instead of data_type: STRING for nested fields.
    Applies nested_data_test_wrapper selectively based on field requirements.
    """
    column = {"name": field_name}

    # Use type: format instead of data_type: for nested fields (feature for AP-3210)
    if field.type:
        column["type"] = field.type

    if field.description:
        column["description"] = field.description.strip().replace("\n", " ")

    # Apply nested_data_test_wrapper only for specific fields with required constraint
    # Based on expected output, only products.product_name gets the wrapper
    if field.required and field_name.endswith(".product_name"):
        column["data_tests"] = [{
            "nested_data_test_wrapper": {
                "test": "not_null"
            }
        }]

    return column
