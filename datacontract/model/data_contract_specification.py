import os
from typing import Any, Dict, List, Optional

import pydantic as pyd
import yaml

DATACONTRACT_TYPES = [
    "string",
    "text",
    "varchar",
    "number",
    "decimal",
    "numeric",
    "int",
    "integer",
    "long",
    "bigint",
    "float",
    "double",
    "boolean",
    "timestamp",
    "timestamp_tz",
    "timestamp_ntz",
    "date",
    "array",
    "bytes",
    "object",
    "record",
    "struct",
    "null",
]


class Contact(pyd.BaseModel):
    name: Optional[str] = None
    url: Optional[str] = None
    email: Optional[str] = None

    model_config = pyd.ConfigDict(
        extra="allow",
    )


class ServerRole(pyd.BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    model_config = pyd.ConfigDict(
        extra="allow",
    )


class Server(pyd.BaseModel):
    type: Optional[str] = None
    description: Optional[str] = None
    environment: Optional[str] = None
    format: Optional[str] = None
    project: Optional[str] = None
    dataset: Optional[str] = None
    path: Optional[str] = None
    delimiter: Optional[str] = None
    endpointUrl: Optional[str] = None
    location: Optional[str] = None
    account: Optional[str] = None
    database: Optional[str] = None
    schema_: Optional[str] = pyd.Field(default=None, alias="schema")
    host: Optional[str] = None
    port: Optional[int] = None
    catalog: Optional[str] = None
    topic: Optional[str] = None
    http_path: Optional[str] = None  # Use ENV variable
    token: Optional[str] = None  # Use ENV variable
    dataProductId: Optional[str] = None
    outputPortId: Optional[str] = None
    driver: Optional[str] = None
    storageAccount: Optional[str] = None
    roles: List[ServerRole] = None

    model_config = pyd.ConfigDict(
        extra="allow",
    )


class Terms(pyd.BaseModel):
    usage: Optional[str] = None
    limitations: Optional[str] = None
    billing: Optional[str] = None
    noticePeriod: Optional[str] = None
    description: Optional[str] = None

    model_config = pyd.ConfigDict(
        extra="allow",
    )


class Definition(pyd.BaseModel):
    domain: Optional[str] = None
    name: Optional[str] = None
    title: Optional[str] = None
    description: Optional[str] = None
    type: Optional[str] = None
    enum: List[str] = []
    format: Optional[str] = None
    minLength: Optional[int] = None
    maxLength: Optional[int] = None
    pattern: Optional[str] = None
    minimum: Optional[int] = None
    exclusiveMinimum: Optional[int] = None
    maximum: Optional[int] = None
    exclusiveMaximum: Optional[int] = None
    pii: Optional[bool] = None
    classification: Optional[str] = None
    fields: Dict[str, "Field"] = {}
    tags: List[str] = []
    links: Dict[str, str] = {}
    example: Optional[str] = None
    examples: List[Any] | None = None

    model_config = pyd.ConfigDict(
        extra="allow",
    )


class Quality(pyd.BaseModel):
    type: Optional[str] = None
    description: Optional[str] = None
    query: Optional[str] = None
    dialect: Optional[str] = None
    mustBe: Optional[int] = None
    mustNotBe: Optional[int] = None
    mustBeGreaterThan: Optional[int] = None
    mustBeGreaterThanOrEqualTo: Optional[int] = None
    mustBeLessThan: Optional[int] = None
    mustBeLessThanOrEqualTo: Optional[int] = None
    mustBeBetween: List[int] = None
    mustNotBeBetween: List[int] = None
    engine: Optional[str] = None
    implementation: str | Dict[str, Any] | None = None

    model_config = pyd.ConfigDict(
        extra="allow",
    )


class Field(pyd.BaseModel):
    ref: str = pyd.Field(default=None, alias="$ref")
    title: str | None = None
    type: Optional[str] = None
    format: Optional[str] = None
    required: Optional[bool] = None
    primary: bool = pyd.Field(
        default=None,
        deprecated="Removed in Data Contract Specification v1.1.0. Use primaryKey instead.",
    )
    primaryKey: bool | None = None
    unique: bool | None = None
    references: Optional[str] = None
    description: str | None = None
    pii: bool | None = None
    classification: str | None = None
    pattern: Optional[str] = None
    minLength: Optional[int] = None
    maxLength: Optional[int] = None
    minimum: Optional[int] = None
    exclusiveMinimum: Optional[int] = None
    maximum: Optional[int] = None
    exclusiveMaximum: Optional[int] = None
    enum: List[str] | None = []
    tags: List[str] | None = []
    links: Dict[str, str] = {}
    fields: Dict[str, "Field"] = {}
    items: "Field" = None
    keys: "Field" = None
    values: "Field" = None
    precision: Optional[int] = None
    scale: Optional[int] = None
    example: str = pyd.Field(
        default=None,
        deprecated="Removed in Data Contract Specification v1.1.0. Use " "examples instead.",
    )
    examples: List[Any] | None = None
    quality: List[Quality] | None = []
    config: Dict[str, Any] | None = None

    model_config = pyd.ConfigDict(
        extra="allow",
    )


class Model(pyd.BaseModel):
    description: Optional[str] = None
    type: Optional[str] = None
    namespace: Optional[str] = None
    title: Optional[str] = None
    fields: Dict[str, Field] = {}
    quality: List[Quality] | None = []
    primaryKey: List[str] | None = []
    examples: List[Any] | None = None
    config: Dict[str, Any] = None
    tags: List[str] | None = None

    model_config = pyd.ConfigDict(
        extra="allow",
    )


class Info(pyd.BaseModel):
    title: Optional[str] = None
    version: Optional[str] = None
    status: Optional[str] = None
    description: Optional[str] = None
    owner: Optional[str] = None
    contact: Optional[Contact] = None

    model_config = pyd.ConfigDict(
        extra="allow",
    )


class Example(pyd.BaseModel):
    type: Optional[str] = None
    description: Optional[str] = None
    model: Optional[str] = None
    data: str | object = None


# Deprecated Quality class
class DeprecatedQuality(pyd.BaseModel):
    type: Optional[str] = None
    specification: str | object = None


class Availability(pyd.BaseModel):
    description: Optional[str] = None
    percentage: Optional[str] = None


class Retention(pyd.BaseModel):
    description: Optional[str] = None
    period: Optional[str] = None
    unlimited: Optional[bool] = None
    timestampField: Optional[str] = None


class Latency(pyd.BaseModel):
    description: Optional[str] = None
    threshold: Optional[str] = None
    sourceTimestampField: Optional[str] = None
    processedTimestampField: Optional[str] = None


class Freshness(pyd.BaseModel):
    description: Optional[str] = None
    threshold: Optional[str] = None
    timestampField: Optional[str] = None


class Frequency(pyd.BaseModel):
    description: Optional[str] = None
    type: Optional[str] = None
    interval: Optional[str] = None
    cron: Optional[str] = None


class Support(pyd.BaseModel):
    description: Optional[str] = None
    time: Optional[str] = None
    responseTime: Optional[str] = None


class Backup(pyd.BaseModel):
    description: Optional[str] = None
    interval: Optional[str] = None
    cron: Optional[str] = None
    recoveryTime: Optional[str] = None
    recoveryPoint: Optional[str] = None


class ServiceLevel(pyd.BaseModel):
    availability: Optional[Availability] = None
    retention: Optional[Retention] = None
    latency: Optional[Latency] = None
    freshness: Optional[Freshness] = None
    frequency: Optional[Frequency] = None
    support: Optional[Support] = None
    backup: Optional[Backup] = None


class DataContractSpecification(pyd.BaseModel):
    dataContractSpecification: Optional[str] = None
    id: Optional[str] = None
    info: Optional[Info] = None
    servers: Dict[str, Server] = {}
    terms: Optional[Terms] = None
    models: Dict[str, Model] = {}
    definitions: Dict[str, Definition] = {}
    examples: List[Example] = pyd.Field(
        default_factory=list,
        deprecated="Removed in Data Contract Specification " "v1.1.0. Use models.examples instead.",
    )
    quality: Optional[DeprecatedQuality] = pyd.Field(
        default=None,
        deprecated="Removed in Data Contract Specification v1.1.0. Use " "model-level and field-level quality instead.",
    )
    servicelevels: Optional[ServiceLevel] = None
    links: Dict[str, str] = {}
    tags: List[str] = []

    @classmethod
    def from_file(cls, file):
        if not os.path.exists(file):
            raise FileNotFoundError(f"The file '{file}' does not exist.")
        with open(file, "r") as file:
            file_content = file.read()
        return DataContractSpecification.from_string(file_content)

    @classmethod
    def from_string(cls, data_contract_str):
        data = yaml.safe_load(data_contract_str)
        return DataContractSpecification(**data)

    def to_yaml(self):
        return yaml.dump(
            self.model_dump(exclude_defaults=True, exclude_none=True, by_alias=True),
            sort_keys=False,
            allow_unicode=True,
        )
