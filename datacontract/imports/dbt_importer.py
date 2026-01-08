import json
from typing import List, TypedDict

from dbt.artifacts.resources.v1.components import ColumnInfo
from dbt.contracts.graph.manifest import Manifest
from dbt.contracts.graph.nodes import GenericTestNode, ManifestNode, ModelNode
from dbt_common.contracts.constraints import ConstraintType
from open_data_contract_standard.model import OpenDataContractStandard, SchemaProperty

from datacontract.imports.bigquery_importer import map_type_from_bigquery
from datacontract.imports.importer import Importer
from datacontract.imports.odcs_helper import (
    create_odcs,
    create_property,
    create_schema_object,
)


class DBTImportArgs(TypedDict, total=False):
    dbt_nodes: list[str]
    resource_types: list[str]


class DbtManifestImporter(Importer):
    def import_source(
        self,
        source: str,
        import_args: DBTImportArgs,
    ) -> OpenDataContractStandard:
        manifest = read_dbt_manifest(manifest_path=source)
        return import_dbt_manifest(
            manifest=manifest,
            dbt_nodes=import_args.get("dbt_model", []),
            resource_types=import_args.get("resource_types", ["model"]),
        )


def read_dbt_manifest(manifest_path: str) -> Manifest:
    """Read a manifest from file."""
    with open(file=manifest_path, mode="r", encoding="utf-8") as f:
        manifest_dict: dict = json.load(f)
    manifest = Manifest.from_dict(manifest_dict)
    manifest.build_parent_and_child_maps()
    return manifest


def _get_primary_keys(manifest: Manifest, node: ManifestNode) -> list[str]:
    node_unique_id = node.unique_id
    if isinstance(node, ModelNode):
        test_nodes = []
        for node_id in manifest.child_map.get(node_unique_id, []):
            test_node = manifest.nodes.get(node_id)
            if not test_node or test_node.resource_type != "test":
                continue
            if not isinstance(test_node, GenericTestNode):
                continue
            if test_node.config.where is not None:
                continue
            test_nodes.append(test_node)
        return node.infer_primary_key(test_nodes)
    return []


def _get_references(manifest: Manifest, node: ManifestNode) -> dict[str, str]:
    node_unique_id = node.unique_id
    references = {}
    for node_id in manifest.child_map.get(node_unique_id, []):
        test_node = manifest.nodes.get(node_id)
        if not test_node or test_node.resource_type != "test":
            continue
        if not isinstance(test_node, GenericTestNode):
            continue
        if test_node.test_metadata.name != "relationships":
            continue
        if test_node.config.where is not None:
            continue
        if test_node.attached_node != node_unique_id:
            continue
        relationship_target_node_id = [n for n in test_node.depends_on.nodes if n != node_unique_id][0]
        relationship_target_node = manifest.nodes.get(relationship_target_node_id)
        references[f"{node.name}.{test_node.column_name}"] = (
            f"""{relationship_target_node.name}.{test_node.test_metadata.kwargs["field"]}"""
        )
    return references


def import_dbt_manifest(
    manifest: Manifest,
    dbt_nodes: list[str],
    resource_types: list[str],
) -> OpenDataContractStandard:
    """Extracts all relevant information from the manifest into an ODCS data contract."""
    odcs = create_odcs()
    odcs.name = manifest.metadata.project_name

    # Store dbt version as custom property
    from open_data_contract_standard.model import CustomProperty
    odcs.customProperties = [CustomProperty(property="dbt_version", value=manifest.metadata.dbt_version)]

    adapter_type = manifest.metadata.adapter_type
    odcs.schema_ = []

    for node in manifest.nodes.values():
        if node.resource_type not in resource_types:
            continue

        if dbt_nodes and node.name not in dbt_nodes:
            continue

        model_unique_id = node.unique_id
        primary_keys = _get_primary_keys(manifest, node)
        references = _get_references(manifest, node)

        primary_key = None
        if len(primary_keys) == 1:
            primary_key = primary_keys[0]

        properties = create_fields(
            manifest,
            model_unique_id=model_unique_id,
            columns=node.columns,
            primary_key_name=primary_key,
            references=references,
            adapter_type=adapter_type,
        )

        schema_obj = create_schema_object(
            name=node.name,
            physical_type="table",
            description=node.description,
            properties=properties,
        )

        # Add tags as custom property
        if node.tags:
            if schema_obj.customProperties is None:
                schema_obj.customProperties = []
            schema_obj.customProperties.append(CustomProperty(property="tags", value=",".join(node.tags)))

        # Handle composite primary key
        if len(primary_keys) > 1:
            if schema_obj.customProperties is None:
                schema_obj.customProperties = []
            schema_obj.customProperties.append(CustomProperty(property="primaryKey", value=",".join(primary_keys)))

        odcs.schema_.append(schema_obj)

    return odcs


def convert_data_type_by_adapter_type(data_type: str, adapter_type: str) -> str:
    if adapter_type == "bigquery":
        return map_type_from_bigquery(data_type)
    return map_dbt_type_to_odcs(data_type)


def map_dbt_type_to_odcs(data_type: str) -> str:
    """Map dbt data type to ODCS logical type."""
    if not data_type:
        return "string"

    data_type_lower = data_type.lower()

    type_mapping = {
        "string": "string",
        "varchar": "string",
        "text": "string",
        "char": "string",
        "int": "integer",
        "integer": "integer",
        "bigint": "integer",
        "smallint": "integer",
        "float": "number",
        "double": "number",
        "decimal": "number",
        "numeric": "number",
        "boolean": "boolean",
        "bool": "boolean",
        "date": "date",
        "datetime": "date",
        "timestamp": "date",
        "time": "string",
        "array": "array",
        "object": "object",
        "struct": "object",
        "json": "object",
    }

    for key, value in type_mapping.items():
        if data_type_lower.startswith(key):
            return value

    return "string"


def create_fields(
    manifest: Manifest,
    model_unique_id: str,
    columns: dict[str, ColumnInfo],
    primary_key_name: str,
    references: dict[str, str],
    adapter_type: str,
) -> List[SchemaProperty]:
    """Create ODCS SchemaProperties from dbt columns."""
    return [
        create_field(manifest, model_unique_id, column, primary_key_name, references, adapter_type)
        for column in columns.values()
    ]


def get_column_tests(manifest: Manifest, model_name: str, column_name: str) -> list[dict[str, str]]:
    column_tests = []
    model_node = manifest.nodes.get(model_name)
    if not model_node:
        raise ValueError(f"Model {model_name} not found in manifest.")

    model_unique_id = model_node.unique_id
    test_ids = manifest.child_map.get(model_unique_id, [])

    for test_id in test_ids:
        test_node = manifest.nodes.get(test_id)
        if not test_node or test_node.resource_type != "test":
            continue

        if not isinstance(test_node, GenericTestNode):
            continue

        if test_node.column_name != column_name:
            continue

        if test_node.config.where is not None:
            continue

        column_tests.append(
            {
                "test_name": test_node.name,
                "test_type": test_node.test_metadata.name,
                "column": test_node.column_name,
            }
        )
    return column_tests


def create_field(
    manifest: Manifest,
    model_unique_id: str,
    column: ColumnInfo,
    primary_key_name: str,
    references: dict[str, str],
    adapter_type: str,
) -> SchemaProperty:
    """Create an ODCS SchemaProperty from a dbt column."""
    column_type = convert_data_type_by_adapter_type(column.data_type, adapter_type) if column.data_type else "string"

    all_tests = get_column_tests(manifest, model_unique_id, column.name)

    required = False
    if any(constraint.type == ConstraintType.not_null for constraint in column.constraints):
        required = True
    if [test for test in all_tests if test["test_type"] == "not_null"]:
        required = True

    unique = False
    if any(constraint.type == ConstraintType.unique for constraint in column.constraints):
        unique = True
    if [test for test in all_tests if test["test_type"] == "unique"]:
        unique = True

    is_primary_key = column.name == primary_key_name

    custom_props = {}
    references_key = f"{manifest.nodes[model_unique_id].name}.{column.name}"
    if references_key in references:
        custom_props["references"] = references[references_key]
    if column.tags:
        custom_props["tags"] = ",".join(column.tags)

    return create_property(
        name=column.name,
        logical_type=column_type,
        physical_type=column.data_type,
        description=column.description,
        required=required if required else None,
        unique=unique if unique else None,
        primary_key=is_primary_key if is_primary_key else None,
        primary_key_position=1 if is_primary_key else None,
        custom_properties=custom_props if custom_props else None,
    )
