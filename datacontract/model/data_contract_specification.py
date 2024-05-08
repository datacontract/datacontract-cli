import os
from typing import List, Dict, Optional, Any

import pydantic as pyd
import yaml


class Contact(pyd.BaseModel):
    name: str = None
    url: str = None
    email: str = None


class Server(pyd.BaseModel):
    type: str = None
    format: str = None
    project: str = None
    dataset: str = None
    path: str = None
    delimiter: str = None
    endpointUrl: str = None
    location: str = None
    account: str = None
    database: str = None
    schema_: str = pyd.Field(default=None, alias="schema")
    host: str = None
    port: int = None
    catalog: str = None
    topic: str = None
    http_path: str = None  # Use ENV variable
    token: str = None  # Use ENV variable
    dataProductId: str = None
    outputPortId: str = None


class Terms(pyd.BaseModel):
    usage: str = None
    limitations: str = None
    billing: str = None
    noticePeriod: str = None


class Definition(pyd.BaseModel):
    domain: str = None
    name: str = None
    title: str = None
    description: str = None
    type: str = None
    enum: List[str] = []
    format: str = None
    minLength: int = None
    maxLength: int = None
    pattern: str = None
    minimum: int = None
    exclusiveMinimum: int = None
    maximum: int = None
    exclusiveMaximum: int = None
    pii: bool = None
    classification: str = None
    tags: List[str] = []


class Field(pyd.BaseModel):
    ref: str = pyd.Field(default=None, alias="$ref")
    ref_obj: Definition = pyd.Field(default=None, exclude=True)
    title: str = None
    type: str = None
    format: str = None
    required: bool = None
    primary: bool = None
    unique: bool = None
    references: str = None
    description: str = None
    pii: bool = None
    classification: str = None
    pattern: str = None
    minLength: int = None
    maxLength: int = None
    minimum: int = None
    exclusiveMinimum: int = None
    maximum: int = None
    exclusiveMaximum: int = None
    logicalType: Optional[str] = None
    default: Optional[Any] = None
    enum: List[str] = []
    tags: List[str] = []
    fields: Dict[str, "Field"] = {}
    items: "Field" = None


class Model(pyd.BaseModel):
    description: str = None
    type: str = None
    namespace: str = None
    fields: Dict[str, Field] = {}


class Info(pyd.BaseModel):
    title: str = None
    version: str = None
    status: str = None
    description: str = None
    owner: str = None
    contact: Contact = None


class Example(pyd.BaseModel):
    type: str = None
    description: str = None
    model: str = None
    data: str | object = None


class Quality(pyd.BaseModel):
    type: str = None
    specification: str | object = None


class DataContractSpecification(pyd.BaseModel):
    dataContractSpecification: str = None
    id: str = None
    info: Info = None
    servers: Dict[str, Server] = {}
    terms: Terms = None
    models: Dict[str, Model] = {}
    definitions: Dict[str, Definition] = {}
    # schema: Dict[str, str]
    examples: List[Example] = []
    quality: Quality = None

    @classmethod
    def from_file(cls, file):
        if not os.path.exists(file):
            raise (f"The file '{file}' does not exist.")
        with open(file, "r") as file:
            file_content = file.read()
        return DataContractSpecification.from_string(file_content)

    @classmethod
    def from_string(cls, data_contract_str):
        data = yaml.safe_load(data_contract_str)
        return DataContractSpecification(**data)

    def to_yaml(self):
        return yaml.dump(self.model_dump(exclude_defaults=True, exclude_none=True), sort_keys=False, allow_unicode=True)
