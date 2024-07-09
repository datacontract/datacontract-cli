import json

# from __future__ import annotations
from typing import (
    List,
    Optional,
)

from datacontract.imports.importer import Importer
from datacontract.model.data_contract_specification import DataContractSpecification, Field, Model


class DbtManifestImporter(Importer):
    def import_source(
        self, data_contract_specification: DataContractSpecification, source: str, import_args: dict = {}
    ) -> dict:
        manifest_dict = read_dbt_manifest(manifest_path=source)
        return import_dbt_manifest(data_contract_specification, manifest_dict, import_args.get("dbt_model"))


def import_dbt_manifest(data_contract_specification: DataContractSpecification, data: dict, dbt_models: List[str]):
    data_contract_specification.info.title = data.get("info").get("project_name")
    data_contract_specification.info.dbt_version = data.get("info").get("dbt_version")

    if data_contract_specification.models is None:
        data_contract_specification.models = {}

    for model in data.get("models", []):
        if dbt_models and model.name not in dbt_models:
            continue

        dc_model = Model(
            description=model.description,
            tags=model.tags,
            fields=convert_fields(model.columns),
        )

        data_contract_specification.models[model.name] = dc_model

    return data_contract_specification


def convert_fields(columns):
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
        return {"info": manifest.get("metadata"), "models": get_models(manifest)}


def get_models(manifest):
    models = []
    nodes = manifest.get("nodes")

    for node in nodes.values():
        if node["resource_type"] != "model":
            continue

        models.append(DbtModel(node))
    return models


class DbtColumn:
    name: str
    description: Optional[str] = None
    data_type: Optional[str] = None
    meta: Optional[dict] = None
    constraints: Optional[str] = None
    quote: Optional[str] = None
    tags: Optional[str] = None

    def __init__(self, node_column) -> None:
        self.name = node_column.get("name", "")
        self.description = node_column.get("description", "")
        self.data_type = node_column.get("data_type", None)
        self.meta = node_column.get("meta", {})
        self.tags = node_column.get("tags", [])

    def __repr__(self) -> str:
        return self.name


class DbtModel:
    name: str
    database: str
    schema: str
    description: Optional[str] = None
    unique_id: str
    tags: Optional[str] = None

    def __init__(self, node) -> None:
        self.name = node.get("name")
        self.database = node.get("database")
        self.schema = node.get("schema")
        self.description = node.get("description")
        self.display_name = node.get("display_name")
        self.unique_id = node.get("unique_id")
        self.columns = []
        self.tags = node.get("tags")
        self.add_columns(node.get("columns").values())

    def add_columns(self, model_columns) -> Optional[str]:
        for column in model_columns:
            self.columns.append(DbtColumn(column))

    def __repr__(self) -> str:
        return self.name
