import json
from typing import TypedDict

from dbt.artifacts.resources.v1.components import ColumnInfo
from dbt.contracts.graph.manifest import Manifest
from dbt.contracts.graph.nodes import GenericTestNode, ManifestNode, ModelNode
from dbt_common.contracts.constraints import ConstraintType

from datacontract.imports.bigquery_importer import map_type_from_bigquery
from datacontract.imports.importer import Importer
from datacontract.model.data_contract_specification import DataContractSpecification, Field, Model


class DBTImportArgs(TypedDict, total=False):
    """
    A dictionary representing arguments for importing DBT models.
    Makes the DBT Importer more customizable by allowing for flexible filtering
    of models and their properties, through wrapping or extending.

    Attributes:
        dbt_models: The keys of models to be used in contract. All as default.
        resource_types: Nodes listed in resource_types are kept while importing. model as default.
    """

    dbt_nodes: list[str]
    resource_types: list[str]


class DbtManifestImporter(Importer):
    def import_source(
        self,
        data_contract_specification: DataContractSpecification,
        source: str,
        import_args: DBTImportArgs,
    ) -> DataContractSpecification:
        manifest = read_dbt_manifest(manifest_path=source)
        return import_dbt_manifest(
            data_contract_specification=data_contract_specification,
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
    data_contract_specification: DataContractSpecification,
    manifest: Manifest,
    dbt_nodes: list[str],
    resource_types: list[str],
) -> DataContractSpecification:
    """
    Extracts all relevant information from the manifest,
    and puts it in a data contract specification.
    """
    data_contract_specification.info.title = manifest.metadata.project_name
    data_contract_specification.info.dbt_version = manifest.metadata.dbt_version
    adapter_type = manifest.metadata.adapter_type
    data_contract_specification.models = data_contract_specification.models or {}
    for node in manifest.nodes.values():
        # Only intressted in processing models.
        if node.resource_type not in resource_types:
            continue

        # To allow args stored in dbt_models to filter relevant models.
        # If dbt_models is empty, use all models.
        if dbt_nodes and node.name not in dbt_nodes:
            continue

        model_unique_id = node.unique_id
        primary_keys = _get_primary_keys(manifest, node)
        references = _get_references(manifest, node)

        primary_key = None
        if len(primary_keys) == 1:
            primary_key = primary_keys[0]

        dc_model = Model(
            description=node.description,
            tags=node.tags,
            fields=create_fields(
                manifest,
                model_unique_id=model_unique_id,
                columns=node.columns,
                primary_key_name=primary_key,
                references=references,
                adapter_type=adapter_type,
            ),
        )
        if len(primary_keys) > 1:
            dc_model.primaryKey = primary_keys

        data_contract_specification.models[node.name] = dc_model

    return data_contract_specification


def convert_data_type_by_adapter_type(data_type: str, adapter_type: str) -> str:
    if adapter_type == "bigquery":
        return map_type_from_bigquery(data_type)
    return data_type


def create_fields(
    manifest: Manifest,
    model_unique_id: str,
    columns: dict[str, ColumnInfo],
    primary_key_name: str,
    references: dict[str, str],
    adapter_type: str,
) -> dict[str, Field]:
    fields = {
        column.name: create_field(manifest, model_unique_id, column, primary_key_name, references, adapter_type)
        for column in columns.values()
    }
    return fields


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
) -> Field:
    column_type = convert_data_type_by_adapter_type(column.data_type, adapter_type) if column.data_type else ""
    field = Field(
        description=column.description,
        type=column_type,
        tags=column.tags,
    )

    all_tests = get_column_tests(manifest, model_unique_id, column.name)

    required = False
    if any(constraint.type == ConstraintType.not_null for constraint in column.constraints):
        required = True
    if [test for test in all_tests if test["test_type"] == "not_null"]:
        required = True
    if required:
        field.required = required

    unique = False
    if any(constraint.type == ConstraintType.unique for constraint in column.constraints):
        unique = True
    if [test for test in all_tests if test["test_type"] == "unique"]:
        unique = True
    if unique:
        field.unique = unique

    if column.name == primary_key_name:
        field.primaryKey = True

    references_key = f"{manifest.nodes[model_unique_id].name}.{column.name}"
    if references_key in references:
        field.references = references[references_key]

    return field
