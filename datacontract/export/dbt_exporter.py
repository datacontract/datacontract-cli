from typing import List, Optional, Union

import yaml
from open_data_contract_standard.model import Description, OpenDataContractStandard, SchemaObject, SchemaProperty

from datacontract.export.exporter import Exporter, _check_schema_name_for_export
from datacontract.export.sql_type_converter import convert_to_sql_type


def _get_description_str(description: Union[str, Description, None]) -> Optional[str]:
    """Extract description string from either a string or Description object."""
    if description is None:
        return None
    if isinstance(description, str):
        return description.strip().replace("\n", " ")
    # Description object - use purpose field
    if hasattr(description, "purpose") and description.purpose:
        return description.purpose.strip().replace("\n", " ")
    return None


class DbtExporter(Exporter):
    def export(self, data_contract, schema_name, server, sql_server_type, export_args) -> dict:
        return to_dbt_models_yaml(data_contract, server)


class DbtSourceExporter(Exporter):
    def export(self, data_contract, schema_name, server, sql_server_type, export_args) -> dict:
        return to_dbt_sources_yaml(data_contract, server)


class DbtStageExporter(Exporter):
    def export(self, data_contract, schema_name, server, sql_server_type, export_args) -> dict:
        model_name, model_value = _check_schema_name_for_export(data_contract, schema_name, self.export_format)
        return to_dbt_staging_sql(
            data_contract,
            model_name,
            model_value,
        )


def _get_custom_property_value(prop: SchemaProperty, key: str) -> Optional[str]:
    """Get a custom property value."""
    if prop.customProperties is None:
        return None
    for cp in prop.customProperties:
        if cp.property == key:
            return cp.value
    return None


def _get_logical_type_option(prop: SchemaProperty, key: str):
    """Get a logical type option value."""
    if prop.logicalTypeOptions is None:
        return None
    return prop.logicalTypeOptions.get(key)


def _get_enum_values(prop: SchemaProperty):
    """Get enum values from logicalTypeOptions, customProperties, or quality rules."""
    import json
    # First check logicalTypeOptions
    enum_values = _get_logical_type_option(prop, "enum")
    if enum_values:
        return enum_values
    # Then check customProperties
    enum_str = _get_custom_property_value(prop, "enum")
    if enum_str:
        try:
            if isinstance(enum_str, list):
                return enum_str
            return json.loads(enum_str)
        except (json.JSONDecodeError, TypeError):
            pass
    # Finally check quality rules for invalidValues with validValues
    if prop.quality:
        for q in prop.quality:
            if q.metric == "invalidValues" and q.arguments:
                valid_values = q.arguments.get("validValues")
                if valid_values:
                    return valid_values
    return None


def _get_owner(data_contract: OpenDataContractStandard) -> Optional[str]:
    """Get owner from team."""
    if data_contract.team is None:
        return None
    return data_contract.team.name


def _get_server_by_name(data_contract: OpenDataContractStandard, name: str):
    """Get a server by name."""
    if data_contract.servers is None:
        return None
    return next((s for s in data_contract.servers if s.server == name), None)


def to_dbt_models_yaml(odcs: OpenDataContractStandard, server: str = None) -> str:
    dbt = {
        "version": 2,
        "models": [],
    }

    if odcs.schema_:
        for schema_obj in odcs.schema_:
            dbt_model = _to_dbt_model(schema_obj.name, schema_obj, odcs, adapter_type=server)
            dbt["models"].append(dbt_model)
    return yaml.safe_dump(dbt, indent=2, sort_keys=False, allow_unicode=True)


def to_dbt_staging_sql(odcs: OpenDataContractStandard, model_name: str, model_value: SchemaObject) -> str:
    contract_id = odcs.id
    columns = []
    if model_value.properties:
        for prop in model_value.properties:
            # TODO escape SQL reserved key words, probably dependent on server type
            columns.append(prop.name)
    return f"""
    select
        {", ".join(columns)}
    from {{{{ source('{contract_id}', '{model_name}') }}}}
"""


def to_dbt_sources_yaml(odcs: OpenDataContractStandard, server: str = None):
    source = {"name": odcs.id}
    dbt = {
        "version": 2,
        "sources": [source],
    }
    owner = _get_owner(odcs)
    if owner is not None:
        source["meta"] = {"owner": owner}
    desc_str = _get_description_str(odcs.description)
    if desc_str is not None:
        source["description"] = desc_str

    found_server = _get_server_by_name(odcs, server) if server else None
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
    if odcs.schema_:
        for schema_obj in odcs.schema_:
            dbt_model = _to_dbt_source_table(odcs, schema_obj.name, schema_obj, adapter_type)
            source["tables"].append(dbt_model)
    return yaml.dump(dbt, indent=2, sort_keys=False, allow_unicode=True)


def _to_dbt_source_table(
    odcs: OpenDataContractStandard, model_key: str, model_value: SchemaObject, adapter_type: Optional[str]
) -> dict:
    dbt_model = {
        "name": model_key,
    }

    if model_value.description is not None:
        dbt_model["description"] = model_value.description.strip().replace("\n", " ")
    columns = _to_columns(odcs, model_value.properties or [], False, adapter_type)
    if columns:
        dbt_model["columns"] = columns
    return dbt_model


def _to_dbt_model(
    schema_name: str, schema_object: SchemaObject, odcs: OpenDataContractStandard, adapter_type: Optional[str]
) -> dict:
    dbt_model = {
        "name": schema_name,
    }
    model_type = _to_dbt_model_type(schema_object.physicalType)

    dbt_model["config"] = {"meta": {"data_contract": odcs.id}}

    if model_type:
        dbt_model["config"]["materialized"] = model_type

    owner = _get_owner(odcs)
    if owner is not None:
        dbt_model["config"]["meta"]["owner"] = owner

    if _supports_constraints(model_type):
        dbt_model["config"]["contract"] = {"enforced": True}
    if schema_object.description is not None:
        dbt_model["description"] = schema_object.description.strip().replace("\n", " ")

    # Handle model-level primaryKey from properties
    primary_key_columns = []
    if schema_object.properties:
        for prop in schema_object.properties:
            if prop.primaryKey:
                primary_key_columns.append(prop.name)

    if len(primary_key_columns) > 1:
        # Multiple columns: use dbt_utils.unique_combination_of_columns
        dbt_model["data_tests"] = [
            {"dbt_utils.unique_combination_of_columns": {"combination_of_columns": primary_key_columns}}
        ]

    columns = _to_columns(
        odcs, schema_object.properties or [], _supports_constraints(model_type), adapter_type, primary_key_columns
    )
    if columns:
        dbt_model["columns"] = columns

    return dbt_model


def _to_dbt_model_type(model_type: Optional[str]):
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


def _supports_constraints(model_type: Optional[str]) -> bool:
    return model_type == "table" or model_type == "incremental"


def _to_columns(
    odcs: OpenDataContractStandard,
    properties: List[SchemaProperty],
    supports_constraints: bool,
    adapter_type: Optional[str],
    primary_key_columns: Optional[list] = None,
) -> list:
    columns = []
    primary_key_columns = primary_key_columns or []
    is_single_pk = len(primary_key_columns) == 1
    for prop in properties:
        is_primary_key = prop.name in primary_key_columns
        # Only pass is_primary_key for unique constraint if it's a single-column PK
        # Composite PKs use unique_combination_of_columns at model level instead
        column = _to_column(odcs, prop, supports_constraints, adapter_type, is_primary_key, is_single_pk)
        columns.append(column)
    return columns


def get_table_name_and_column_name(references: str) -> tuple:
    parts = references.split(".")
    if len(parts) < 2:
        return None, parts[0]
    return parts[-2], parts[-1]


def _to_column(
    data_contract: OpenDataContractStandard,
    prop: SchemaProperty,
    supports_constraints: bool,
    adapter_type: Optional[str],
    is_primary_key: bool = False,
    is_single_pk: bool = False,
) -> dict:
    column = {"name": prop.name}
    adapter_type = adapter_type or "snowflake"
    dbt_type = convert_to_sql_type(prop, adapter_type)

    column["data_tests"] = []
    if dbt_type is not None:
        column["data_type"] = dbt_type
    else:
        column["data_tests"].append(
            {"dbt_expectations.dbt_expectations.expect_column_values_to_be_of_type": {"column_type": dbt_type}}
        )
    if prop.description is not None:
        column["description"] = prop.description.strip().replace("\n", " ")

    # Handle required/not_null constraint
    if prop.required or is_primary_key:
        if supports_constraints:
            column.setdefault("constraints", []).append({"type": "not_null"})
        else:
            column["data_tests"].append("not_null")

    # Handle unique constraint
    # For composite primary keys, uniqueness is handled at model level via unique_combination_of_columns
    # Only add unique constraint for single-column primary keys or explicit unique fields
    if prop.unique or (is_primary_key and is_single_pk):
        if supports_constraints:
            column.setdefault("constraints", []).append({"type": "unique"})
        else:
            column["data_tests"].append("unique")

    enum_values = _get_enum_values(prop)
    if enum_values and len(enum_values) > 0:
        column["data_tests"].append({"accepted_values": {"values": enum_values}})

    min_length = _get_logical_type_option(prop, "minLength")
    max_length = _get_logical_type_option(prop, "maxLength")
    if min_length is not None or max_length is not None:
        length_test = {}
        if min_length is not None:
            length_test["min_value"] = min_length
        if max_length is not None:
            length_test["max_value"] = max_length
        column["data_tests"].append({"dbt_expectations.expect_column_value_lengths_to_be_between": length_test})

    if prop.classification is not None:
        column.setdefault("meta", {})["classification"] = prop.classification
    if prop.tags is not None and len(prop.tags) > 0:
        column.setdefault("tags", []).extend(prop.tags)

    pattern = _get_logical_type_option(prop, "pattern")
    if pattern is not None:
        # Beware, the data contract pattern is a regex, not a like pattern
        column["data_tests"].append({"dbt_expectations.expect_column_values_to_match_regex": {"regex": pattern}})

    minimum = _get_logical_type_option(prop, "minimum")
    maximum = _get_logical_type_option(prop, "maximum")
    exclusive_minimum = _get_logical_type_option(prop, "exclusiveMinimum")
    exclusive_maximum = _get_logical_type_option(prop, "exclusiveMaximum")

    if (minimum is not None or maximum is not None) and exclusive_minimum is None and exclusive_maximum is None:
        range_test = {}
        if minimum is not None:
            range_test["min_value"] = minimum
        if maximum is not None:
            range_test["max_value"] = maximum
        column["data_tests"].append({"dbt_expectations.expect_column_values_to_be_between": range_test})
    elif (exclusive_minimum is not None or exclusive_maximum is not None) and minimum is None and maximum is None:
        range_test = {}
        if exclusive_minimum is not None:
            range_test["min_value"] = exclusive_minimum
        if exclusive_maximum is not None:
            range_test["max_value"] = exclusive_maximum
        range_test["strictly"] = True
        column["data_tests"].append({"dbt_expectations.expect_column_values_to_be_between": range_test})
    else:
        if minimum is not None:
            column["data_tests"].append(
                {"dbt_expectations.expect_column_values_to_be_between": {"min_value": minimum}}
            )
        if maximum is not None:
            column["data_tests"].append(
                {"dbt_expectations.expect_column_values_to_be_between": {"max_value": maximum}}
            )
        if exclusive_minimum is not None:
            column["data_tests"].append(
                {
                    "dbt_expectations.expect_column_values_to_be_between": {
                        "min_value": exclusive_minimum,
                        "strictly": True,
                    }
                }
            )
        if exclusive_maximum is not None:
            column["data_tests"].append(
                {
                    "dbt_expectations.expect_column_values_to_be_between": {
                        "max_value": exclusive_maximum,
                        "strictly": True,
                    }
                }
            )

    # Handle references from relationships
    references = None
    if prop.relationships:
        for rel in prop.relationships:
            if hasattr(rel, 'to') and rel.to:
                references = rel.to
                break
    if references is not None:
        ref_source_name = data_contract.id
        table_name, column_name = get_table_name_and_column_name(references)
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
