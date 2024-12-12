import json
from typing import TypedDict

from dbt.artifacts.resources.v1.components import ColumnInfo
from dbt.contracts.graph.manifest import Manifest

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
    return Manifest.from_dict(manifest_dict)


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
    for model_contents in manifest.nodes.values():
        # Only intressted in processing models.
        if model_contents.resource_type not in resource_types:
            continue

        # To allow args stored in dbt_models to filter relevant models.
        # If dbt_models is empty, use all models.
        if dbt_nodes and model_contents.name not in dbt_nodes:
            continue

        dc_model = Model(
            description=model_contents.description,
            tags=model_contents.tags,
            fields=create_fields(columns=model_contents.columns, adapter_type=adapter_type),
        )

        data_contract_specification.models[model_contents.name] = dc_model

    return data_contract_specification


def convert_data_type_by_adapter_type(data_type: str, adapter_type: str) -> str:
    if adapter_type == "bigquery":
        return map_type_from_bigquery(data_type)
    return data_type


def create_fields(columns: dict[str, ColumnInfo], adapter_type: str) -> dict[str, Field]:
    fields = {
        column.name: Field(
            description=column.description,
            type=convert_data_type_by_adapter_type(column.data_type, adapter_type) if column.data_type else "",
            tags=column.tags,
        )
        for column in columns.values()
    }

    return fields
