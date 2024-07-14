import json

from typing import (
    List,
)

from datacontract.imports.importer import Importer
from datacontract.model.data_contract_specification import DataContractSpecification, Field, Model


class DbtManifestImporter(Importer):
    def import_source(
        self, data_contract_specification: DataContractSpecification, source: str, import_args: dict
    ) -> dict:
        data = read_dbt_manifest(manifest_path=source)
        return import_dbt_manifest(
            data_contract_specification, manifest_dict=data, dbt_models=import_args.get("dbt_model")
        )


def import_dbt_manifest(
    data_contract_specification: DataContractSpecification, manifest_dict: dict, dbt_models: List[str]
):
    data_contract_specification.info.title = manifest_dict.get("info").get("project_name")
    data_contract_specification.info.dbt_version = manifest_dict.get("info").get("dbt_version")

    if data_contract_specification.models is None:
        data_contract_specification.models = {}

    for model in manifest_dict.get("models", []):
        if dbt_models and model.name not in dbt_models:
            continue

        dc_model = Model(
            description=model.description,
            tags=model.tags,
            fields=create_fields(model.columns),
        )

        data_contract_specification.models[model.name] = dc_model

    return data_contract_specification


def create_fields(columns: List):
    fields = {}
    for column in columns:
        field = Field(
            description=column.description, type=column.data_type if column.data_type else "", tags=column.tags
        )
        fields[column.name] = field

    return fields


def read_dbt_manifest(manifest_path: str):
    with open(manifest_path, "r", encoding="utf-8") as f:
        manifest = json.load(f)
    return {"info": manifest.get("metadata"), "models": create_manifest_models(manifest)}


def create_manifest_models(manifest: dict) -> List:
    models = []
    nodes = manifest.get("nodes")

    for node in nodes.values():
        if node["resource_type"] != "model":
            continue

        models.append(DbtModel(node))
    return models


class DbtColumn:
    name: str
    description: str
    data_type: str
    meta: dict
    tags: List

    def __init__(self, node_column: dict):
        self.name = node_column.get("name")
        self.description = node_column.get("description")
        self.data_type = node_column.get("data_type")
        self.meta = node_column.get("meta", {})
        self.tags = node_column.get("tags", [])

    def __repr__(self) -> str:
        return self.name


class DbtModel:
    name: str
    database: str
    schema: str
    description: str
    unique_id: str
    tags: List

    def __init__(self, node: dict):
        self.name = node.get("name")
        self.database = node.get("database")
        self.schema = node.get("schema")
        self.description = node.get("description")
        self.display_name = node.get("display_name")
        self.unique_id = node.get("unique_id")
        self.columns = []
        self.tags = node.get("tags")
        if node.get("columns"):
            self.add_columns(node.get("columns").values())

    def add_columns(self, model_columns: List):
        for column in model_columns:
            self.columns.append(DbtColumn(column))

    def __repr__(self) -> str:
        return self.name
