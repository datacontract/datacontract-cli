"""Exporter for Open Semantic Interchange (OSI) format."""

from typing import Any, Dict, List, Optional

import yaml
from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, SchemaProperty

from datacontract.export.exporter import Exporter


class OsiExporter(Exporter):
    def export(
        self,
        data_contract: OpenDataContractStandard,
        schema_name: str,
        server: str,
        sql_server_type: str,
        export_args: dict,
    ) -> str:
        return export_osi(data_contract)


def export_osi(data_contract: OpenDataContractStandard) -> str:
    """Export ODCS data contract to OSI semantic model format."""
    semantic_model = convert_odcs_to_osi(data_contract)
    return yaml.dump({"semantic_model": semantic_model}, default_flow_style=False, sort_keys=False, allow_unicode=True)


def convert_odcs_to_osi(data_contract: OpenDataContractStandard) -> Dict[str, Any]:
    """Convert ODCS data contract to OSI semantic model."""
    model = {
        "name": data_contract.id or data_contract.name or "unnamed_model",
    }

    # Add description
    if data_contract.description:
        if hasattr(data_contract.description, "purpose") and data_contract.description.purpose:
            model["description"] = data_contract.description.purpose
        elif isinstance(data_contract.description, str):
            model["description"] = data_contract.description

    # Convert schemas to datasets and collect relationships
    datasets = []
    relationships = []

    if data_contract.schema_:
        for schema in data_contract.schema_:
            dataset = convert_schema_to_dataset(schema)
            datasets.append(dataset)

            # Extract relationships from property references
            schema_relationships = extract_relationships_from_schema(schema)
            relationships.extend(schema_relationships)

    model["datasets"] = datasets

    if relationships:
        model["relationships"] = relationships

    return model


def convert_schema_to_dataset(schema: SchemaObject) -> Dict[str, Any]:
    """Convert ODCS SchemaObject to OSI dataset."""
    dataset = {
        "name": schema.name,
        "source": schema.physicalName or schema.name,
    }

    # Extract primary key columns
    primary_key = []
    unique_keys = []
    unique_columns = []

    if schema.properties:
        for prop in schema.properties:
            if prop.primaryKey:
                primary_key.append((prop.primaryKeyPosition or 999, prop.name))
            if prop.unique and not prop.primaryKey:
                unique_columns.append(prop.name)

    # Sort primary key by position
    primary_key.sort(key=lambda x: x[0])
    if primary_key:
        dataset["primary_key"] = [pk[1] for pk in primary_key]

    # Add unique keys (each as single-column key)
    if unique_columns:
        dataset["unique_keys"] = [[col] for col in unique_columns]

    # Add description
    if schema.description:
        dataset["description"] = schema.description

    # Convert properties to fields
    if schema.properties:
        fields = [convert_property_to_field(prop) for prop in schema.properties]
        dataset["fields"] = fields

    return dataset


def convert_property_to_field(prop: SchemaProperty) -> Dict[str, Any]:
    """Convert ODCS SchemaProperty to OSI field."""
    field = {
        "name": prop.name,
        "expression": {
            "dialects": [
                {
                    "dialect": "ANSI_SQL",
                    "expression": prop.physicalName or prop.name,
                }
            ]
        },
    }

    # Add other dialects from custom properties
    if prop.customProperties:
        for cp in prop.customProperties:
            if cp.property == "osi_dialects" and cp.value:
                field["expression"]["dialects"].extend(cp.value)

    # Add dimension for time types
    if prop.logicalType in ["date", "timestamp", "datetime"]:
        field["dimension"] = {"is_time": True}

    # Add description
    if prop.description:
        field["description"] = prop.description

    # Add label from businessName
    if prop.businessName:
        field["label"] = prop.businessName

    return field


def extract_relationships_from_schema(schema: SchemaObject) -> List[Dict[str, Any]]:
    """Extract foreign key relationships from schema properties."""
    relationships = []

    if not schema.properties:
        return relationships

    for prop in schema.properties:
        if prop.relationships:
            for rel_obj in prop.relationships:
                # Parse reference from 'to' field: "target_table.target_column"
                if rel_obj.to:
                    parts = rel_obj.to.split(".")
                    if len(parts) >= 2:
                        to_table = parts[0]
                        to_column = parts[1]

                        rel = {
                            "name": f"{schema.name}_{prop.name}_to_{to_table}",
                            "from": schema.name,
                            "to": to_table,
                            "from_columns": [prop.name],
                            "to_columns": [to_column],
                        }
                        relationships.append(rel)

    return relationships
