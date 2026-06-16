"""Build CTE-based virtual models for recursive Databricks nested checks.

For array item checks targeting `{model}__{array_field}`, this module generates
SQL WITH clauses that explode the array and expose nested properties as columns,
allowing read-only recursive checks without CREATE TABLE/CREATE VOLUME.

Example: For an `orders` table with `items ARRAY<STRUCT<id STRING, qty INT>>`,
the virtual model `orders__items` resolves to:

  WITH __dc_source__ AS (SELECT * FROM orders)
  SELECT __dc_nested__.* FROM __dc_source__
  LATERAL VIEW OUTER explode_outer(`items`) AS __dc_nested__

This is then available to checks targeting `orders__items` (nested array model).
"""

from __future__ import annotations

from open_data_contract_standard.model import OpenDataContractStandard, SchemaProperty


def build_databricks_virtual_model_queries_for_contract(
    data_contract: OpenDataContractStandard,
    schema_name: str = "all",
) -> dict[str, str]:
    """Build a dict of {model_name: CTE_query} for all nested array models in the contract.

    Only models matching the optional schema filter are included.
    """
    queries: dict[str, str] = {}
    if data_contract.schema_ is None:
        return queries

    for schema_obj in data_contract.schema_:
        if schema_name != "all" and schema_obj.name != schema_name:
            continue
        model = schema_obj.physicalName or schema_obj.name
        specs: dict[str, dict[str, str]] = {}
        _collect_databricks_virtual_model_specs(model, schema_obj.properties, specs)
        for virtual_model, query in _render_virtual_models(model, specs).items():
            queries[virtual_model] = query

    return queries


def _collect_databricks_virtual_model_specs(
    parent_model: str,
    properties: list[SchemaProperty] | None,
    specs: dict[str, dict[str, str]],
    prefix: str | None = None,
):
    """Recursively collect array specs that need virtual models.

    For each array field found, record (parent_model, field_name, item_type_properties)
    so we can render its CTE later.
    """
    for prop in properties or []:
        field = prop.physicalName or prop.name
        field_path = f"{prefix}.{field}" if prefix else field
        prop_type = (prop.physicalType or prop.logicalType or "").lower()

        # Array of struct: create a virtual model for this array.
        if prop_type == "array" and prop.items and prop.items.properties:
            virtual_model = f"{parent_model}__{field}"
            specs[virtual_model] = {
                "parent": parent_model,
                "field": field,
                "template": "SELECT __dc_nested__.* FROM {source} LATERAL VIEW OUTER explode_outer(`{field}`) AS __dc_nested__",
            }

        # Struct with nested properties: recurse for any nested arrays.
        if prop_type in {"object", "record", "struct"} and prop.properties:
            _collect_databricks_virtual_model_specs(parent_model, prop.properties, specs, field_path)


def _render_virtual_models(model: str, specs: dict[str, dict[str, str]]) -> dict[str, str]:
    """Render CTE SQL for all virtual models, handling dependencies."""
    queries: dict[str, str] = {}
    for virtual_model in specs:
        queries[virtual_model] = _render_databricks_virtual_model_query(virtual_model, specs)
    return queries


def _render_databricks_virtual_model_query(model: str, specs: dict[str, dict[str, str]]) -> str:
    """Render a single CTE query for a virtual model, recursively handling parent deps."""
    spec = specs[model]
    parent = spec["parent"]

    # If parent is also virtual, render its CTE first; otherwise, SELECT from the real table.
    if parent in specs:
        parent_query = _render_databricks_virtual_model_query(parent, specs)
    else:
        parent_query = f"SELECT * FROM {parent}"

    source = "__dc_source__"
    template = spec["template"]
    field = spec["field"]
    return f"WITH {source} AS ({parent_query}) {template.format(source=source, field=field)}"
