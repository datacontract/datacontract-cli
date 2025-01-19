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
    name: str = None
    url: str = None
    email: str = None

    model_config = pyd.ConfigDict(
        extra="allow",
    )


class ServerRole(pyd.BaseModel):
    name: str = None
    description: str = None
    model_config = pyd.ConfigDict(
        extra="allow",
    )


class Server(pyd.BaseModel):
    type: str = None
    description: str = None
    environment: str = None
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
    driver: str = None
    storageAccount: str = None
    roles: List[ServerRole] = None

    model_config = pyd.ConfigDict(
        extra="allow",
    )


class Terms(pyd.BaseModel):
    usage: str = None
    limitations: str = None
    billing: str = None
    noticePeriod: str = None
    description: str = None

    model_config = pyd.ConfigDict(
        extra="allow",
    )


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
    fields: Dict[str, "Field"] = {}
    tags: List[str] = []
    links: Dict[str, str] = {}
    example: str = None
    examples: List[Any] | None = None

    model_config = pyd.ConfigDict(
        extra="allow",
    )


class Quality(pyd.BaseModel):
    type: str = None
    description: str = None
    query: str = None
    dialect: str = None
    mustBe: int = None
    mustNotBe: int = None
    mustBeGreaterThan: int = None
    mustBeGreaterThanOrEqualTo: int = None
    mustBeLessThan: int = None
    mustBeLessThanOrEqualTo: int = None
    mustBeBetween: List[int] = None
    mustNotBeBetween: List[int] = None
    engine: str = None
    implementation: str | Dict[str, Any] = None

    model_config = pyd.ConfigDict(
        extra="allow",
    )


class Field(pyd.BaseModel):
    ref: str = pyd.Field(default=None, alias="$ref")
    title: str | None = None
    type: str = None
    format: str = None
    required: bool = None
    primary: bool = pyd.Field(
        default=None,
        deprecated="Removed in Data Contract Specification v1.1.0. Use primaryKey instead.",
    )
    primaryKey: bool | None = None
    unique: bool | None = None
    references: str = None
    description: str | None = None
    pii: bool | None = None
    classification: str | None = None
    pattern: str = None
    minLength: int = None
    maxLength: int = None
    minimum: int = None
    exclusiveMinimum: int = None
    maximum: int = None
    exclusiveMaximum: int = None
    enum: List[str] | None = []
    tags: List[str] | None = []
    links: Dict[str, str] = {}
    fields: Dict[str, "Field"] = {}
    items: "Field" = None
    keys: "Field" = None
    values: "Field" = None
    precision: int = None
    scale: int = None
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
    title: str = None
    version: str = None
    status: str = None
    description: str = None
    owner: str = None
    contact: Contact = None

    model_config = pyd.ConfigDict(
        extra="allow",
    )


class Example(pyd.BaseModel):
    type: str = None
    description: str = None
    model: str = None
    data: str | object = None


# Deprecated Quality class
class DeprecatedQuality(pyd.BaseModel):
    type: str = None
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
    dataContractSpecification: str = None
    id: str = None
    info: Info = None
    servers: Dict[str, Server] = {}
    terms: Terms = None
    models: Dict[str, Model] = {}
    definitions: Dict[str, Definition] = {}
    examples: List[Example] = pyd.Field(
        default_factory=list,
        deprecated="Removed in Data Contract Specification " "v1.1.0. Use models.examples instead.",
    )
    quality: DeprecatedQuality = pyd.Field(
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
