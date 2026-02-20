"""Importer for Open Semantic Interchange (OSI) format."""

from typing import Any, Dict, List, Optional

import yaml
from open_data_contract_standard.model import CustomProperty, OpenDataContractStandard, Relationship, SchemaProperty

from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import create_odcs, create_property, create_schema_object
from datacontract.model.exceptions import DataContractException


class OsiImporter(Importer):
    def import_source(self, source: str, import_args: dict) -> OpenDataContractStandard:
        return import_osi(source)


def import_osi(source: str) -> OpenDataContractStandard:
    """Import an OSI semantic model and create an ODCS data contract."""
    try:
        with open(source, "r") as f:
            osi_data = yaml.safe_load(f)
    except Exception as e:
        raise DataContractException(
            type="schema",
            name="Parse OSI",
            reason=f"Failed to parse OSI file from {source}",
            engine="datacontract",
            original_exception=e,
        )

    if "semantic_model" not in osi_data:
        raise DataContractException(
            type="schema",
            name="Parse OSI",
            reason="Invalid OSI format: missing 'semantic_model' root element",
            engine="datacontract",
        )

    semantic_model = osi_data["semantic_model"]
    return convert_osi_to_odcs(semantic_model)


def convert_osi_to_odcs(semantic_model: Dict[str, Any]) -> OpenDataContractStandard:
    """Convert OSI semantic model to ODCS format."""
    name = semantic_model.get("name", "unnamed_model")
    description = semantic_model.get("description")
    ai_context = semantic_model.get("ai_context")

    # Combine description and ai_context
    full_description = description
    if ai_context:
        if full_description:
            full_description = f"{full_description}\n\nAI Context: {ai_context}"
        else:
            full_description = f"AI Context: {ai_context}"

    odcs = create_odcs(name=name)

    # Build relationship lookup: from_dataset.from_column -> to_dataset.to_column
    relationships = semantic_model.get("relationships", [])
    relationship_map = build_relationship_map(relationships)

    # Convert datasets to schemas
    datasets = semantic_model.get("datasets", [])
    schemas = []
    for dataset in datasets:
        schema = convert_dataset_to_schema(dataset, relationship_map)
        schemas.append(schema)

    odcs.schema_ = schemas

    # Store metrics in custom properties if present
    metrics = semantic_model.get("metrics", [])
    if metrics:
        odcs.customProperties = [
            CustomProperty(property="osi_metrics", value=metrics)
        ]

    return odcs


def build_relationship_map(relationships: List[Dict[str, Any]]) -> Dict[str, str]:
    """Build a map of from_dataset.column -> to_dataset.column for FK references."""
    rel_map = {}
    for rel in relationships:
        from_dataset = rel.get("from")
        to_dataset = rel.get("to")
        from_columns = rel.get("from_columns", [])
        to_columns = rel.get("to_columns", [])

        for from_col, to_col in zip(from_columns, to_columns):
            key = f"{from_dataset}.{from_col}"
            value = f"{to_dataset}.{to_col}"
            rel_map[key] = value

    return rel_map


def convert_dataset_to_schema(dataset: Dict[str, Any], relationship_map: Dict[str, str]):
    """Convert an OSI dataset to an ODCS SchemaObject."""
    name = dataset.get("name")
    source = dataset.get("source")
    description = dataset.get("description")
    ai_context = dataset.get("ai_context")
    primary_key = dataset.get("primary_key", [])
    unique_keys = dataset.get("unique_keys", [])
    fields = dataset.get("fields", [])

    # Combine description and ai_context
    full_description = description
    if ai_context:
        if full_description:
            full_description = f"{full_description}\n\nAI Context: {ai_context}"
        else:
            full_description = f"AI Context: {ai_context}"

    # Flatten unique_keys to a set of column names
    unique_columns = set()
    for uk in unique_keys:
        if isinstance(uk, list):
            for col in uk:
                unique_columns.add(col)
        else:
            unique_columns.add(uk)

    # Convert fields to properties
    properties = []
    for idx, field in enumerate(fields):
        prop = convert_field_to_property(
            field=field,
            dataset_name=name,
            primary_key=primary_key,
            unique_columns=unique_columns,
            relationship_map=relationship_map,
        )
        properties.append(prop)

    schema = create_schema_object(
        name=name,
        physical_type="table",
        description=full_description,
        properties=properties,
    )
    schema.physicalName = source

    return schema


def convert_field_to_property(
    field: Dict[str, Any],
    dataset_name: str,
    primary_key: List[str],
    unique_columns: set,
    relationship_map: Dict[str, str],
) -> SchemaProperty:
    """Convert an OSI field to an ODCS SchemaProperty."""
    name = field.get("name")
    label = field.get("label")
    description = field.get("description")
    ai_context = field.get("ai_context")
    expression = field.get("expression", {})
    dimension = field.get("dimension", {})

    # Combine description and ai_context
    full_description = description
    if ai_context:
        if full_description:
            full_description = f"{full_description}\n\nAI Context: {ai_context}"
        else:
            full_description = f"AI Context: {ai_context}"

    # Determine if this is a time dimension
    is_time = dimension.get("is_time", False) if dimension else False

    # Infer logical type from dimension or default to string
    logical_type = "string"
    if is_time:
        logical_type = "timestamp"

    # Check if primary key
    is_primary_key = name in primary_key
    pk_position = primary_key.index(name) + 1 if is_primary_key else None

    # Check if unique
    is_unique = name in unique_columns

    # Check for foreign key reference
    fk_key = f"{dataset_name}.{name}"
    reference = relationship_map.get(fk_key)

    # Get expression for storage
    dialects = expression.get("dialects", [])
    expr_value = None
    if dialects:
        # Prefer ANSI_SQL, fallback to first dialect
        for d in dialects:
            if d.get("dialect") == "ANSI_SQL":
                expr_value = d.get("expression")
                break
        if not expr_value and dialects:
            expr_value = dialects[0].get("expression")

    # Store non-ANSI dialects in custom properties
    custom_props = {}
    other_dialects = [d for d in dialects if d.get("dialect") != "ANSI_SQL"]
    if other_dialects:
        custom_props["osi_dialects"] = other_dialects

    prop = create_property(
        name=name,
        logical_type=logical_type,
        description=full_description,
        primary_key=is_primary_key,
        primary_key_position=pk_position,
        unique=is_unique if is_unique else None,
        custom_properties=custom_props if custom_props else None,
    )

    # Set business name from label
    if label:
        prop.businessName = label

    # Set relationship for foreign keys
    if reference:
        prop.relationships = [Relationship(type="foreignKey", to=reference)]

    return prop
