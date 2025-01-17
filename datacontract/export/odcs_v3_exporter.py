from typing import Dict

import yaml

from datacontract.export.exporter import Exporter
from datacontract.model.data_contract_specification import DataContractSpecification, Field, Model


class OdcsV3Exporter(Exporter):
    def export(self, data_contract, model, server, sql_server_type, export_args) -> dict:
        return to_odcs_v3_yaml(data_contract)


def to_odcs_v3_yaml(data_contract_spec: DataContractSpecification) -> str:
    odcs = {
        "apiVersion": "v3.0.0",
        "kind": "DataContract",
        "id": data_contract_spec.id,
        "name": data_contract_spec.info.title,
        "version": data_contract_spec.info.version,
        "domain": data_contract_spec.info.owner,
        "status": data_contract_spec.info.status,
    }

    if data_contract_spec.terms is not None:
        odcs["description"] = {
            "purpose": data_contract_spec.terms.description.strip()
            if data_contract_spec.terms.description is not None
            else None,
            "usage": data_contract_spec.terms.usage.strip() if data_contract_spec.terms.usage is not None else None,
            "limitations": data_contract_spec.terms.limitations.strip()
            if data_contract_spec.terms.limitations is not None
            else None,
        }

    odcs["schema"] = []
    for model_key, model_value in data_contract_spec.models.items():
        odcs_schema = to_odcs_schema(model_key, model_value)
        odcs["schema"].append(odcs_schema)

    if data_contract_spec.servicelevels is not None:
        slas = []
        if data_contract_spec.servicelevels.availability is not None:
            slas.append(
                {
                    "property": "generalAvailability",
                    "value": data_contract_spec.servicelevels.availability.description,
                }
            )
        if data_contract_spec.servicelevels.retention is not None:
            slas.append({"property": "retention", "value": data_contract_spec.servicelevels.retention.period})

        if len(slas) > 0:
            odcs["slaProperties"] = slas

    if data_contract_spec.info.contact is not None:
        support = []
        if data_contract_spec.info.contact.email is not None:
            support.append(
                {
                    "channel": "email",
                    "url": "mailto:" + data_contract_spec.info.contact.email,
                }
            )
        if data_contract_spec.info.contact.url is not None:
            support.append(
                {
                    "channel": "other",
                    "url": data_contract_spec.info.contact.url,
                }
            )
        if len(support) > 0:
            odcs["support"] = support

    if data_contract_spec.servers is not None and len(data_contract_spec.servers) > 0:
        servers = []

        for server_key, server_value in data_contract_spec.servers.items():
            server_dict = {}
            server_dict["server"] = server_key
            if server_value.type is not None:
                server_dict["type"] = server_value.type
            if server_value.environment is not None:
                server_dict["environment"] = server_value.environment
            if server_value.account is not None:
                server_dict["account"] = server_value.account
            if server_value.database is not None:
                server_dict["database"] = server_value.database
            if server_value.schema_ is not None:
                server_dict["schema"] = server_value.schema_
            if server_value.format is not None:
                server_dict["format"] = server_value.format
            if server_value.project is not None:
                server_dict["project"] = server_value.project
            if server_value.dataset is not None:
                server_dict["dataset"] = server_value.dataset
            if server_value.path is not None:
                server_dict["path"] = server_value.path
            if server_value.delimiter is not None:
                server_dict["delimiter"] = server_value.delimiter
            if server_value.endpointUrl is not None:
                server_dict["endpointUrl"] = server_value.endpointUrl
            if server_value.location is not None:
                server_dict["location"] = server_value.location
            if server_value.host is not None:
                server_dict["host"] = server_value.host
            if server_value.port is not None:
                server_dict["port"] = server_value.port
            if server_value.catalog is not None:
                server_dict["catalog"] = server_value.catalog
            if server_value.topic is not None:
                server_dict["topic"] = server_value.topic
            if server_value.http_path is not None:
                server_dict["http_path"] = server_value.http_path
            if server_value.token is not None:
                server_dict["token"] = server_value.token
            if server_value.driver is not None:
                server_dict["driver"] = server_value.driver
            if server_value.roles is not None:
                server_dict["roles"] = [
                    {"name": role.name, "description": role.description} for role in server_value.roles
                ]
            servers.append(server_dict)

        if len(servers) > 0:
            odcs["servers"] = servers

    odcs["customProperties"] = []
    if data_contract_spec.info.model_extra is not None:
        for key, value in data_contract_spec.info.model_extra.items():
            odcs["customProperties"].append({"property": key, "value": value})
    if len(odcs["customProperties"]) == 0:
        del odcs["customProperties"]

    return yaml.dump(odcs, indent=2, sort_keys=False, allow_unicode=True)


def to_odcs_schema(model_key, model_value: Model) -> dict:
    odcs_table = {
        "name": model_key,
        "physicalName": model_key,
        "logicalType": "object",
        "physicalType": model_value.type,
    }
    if model_value.description is not None:
        odcs_table["description"] = model_value.description
    properties = to_properties(model_value.fields)
    if properties:
        odcs_table["properties"] = properties

    model_quality = to_odcs_quality_list(model_value.quality)
    if len(model_quality) > 0:
        odcs_table["quality"] = model_quality

    odcs_table["customProperties"] = []
    if model_value.model_extra is not None:
        for key, value in model_value.model_extra.items():
            odcs_table["customProperties"].append({"property": key, "value": value})
    if len(odcs_table["customProperties"]) == 0:
        del odcs_table["customProperties"]

    return odcs_table


def to_properties(fields: Dict[str, Field]) -> list:
    properties = []
    for field_name, field in fields.items():
        property = to_property(field_name, field)
        properties.append(property)
    return properties


def to_logical_type(type: str) -> str | None:
    if type is None:
        return None
    if type.lower() in ["string", "varchar", "text"]:
        return "string"
    if type.lower() in ["timestamp", "timestamp_tz"]:
        return "date"
    if type.lower() in ["timestamp_ntz"]:
        return "date"
    if type.lower() in ["date"]:
        return "date"
    if type.lower() in ["time"]:
        return "string"
    if type.lower() in ["number", "decimal", "numeric"]:
        return "number"
    if type.lower() in ["float", "double"]:
        return "number"
    if type.lower() in ["integer", "int", "long", "bigint"]:
        return "integer"
    if type.lower() in ["boolean"]:
        return "boolean"
    if type.lower() in ["object", "record", "struct"]:
        return "object"
    if type.lower() in ["bytes"]:
        return "array"
    if type.lower() in ["array"]:
        return "array"
    if type.lower() in ["null"]:
        return None
    return None


def to_physical_type(type: str) -> str | None:
    # TODO: to we need to do a server mapping here?
    return type


def to_property(field_name: str, field: Field) -> dict:
    property = {"name": field_name}
    if field.title is not None:
        property["businessName"] = field.title
    if field.type is not None:
        property["logicalType"] = to_logical_type(field.type)
        property["physicalType"] = to_physical_type(field.type)
    if field.description is not None:
        property["description"] = field.description
    if field.required is not None:
        property["isNullable"] = not field.required
    if field.unique is not None:
        property["isUnique"] = field.unique
    if field.classification is not None:
        property["classification"] = field.classification
    if field.examples is not None:
        property["examples"] = field.examples
    if field.example is not None:
        property["examples"] = [field.example]
    if field.primaryKey is not None and field.primaryKey:
        property["primaryKey"] = field.primaryKey
        property["primaryKeyPosition"] = 1
    if field.primary is not None and field.primary:
        property["primaryKey"] = field.primary
        property["primaryKeyPosition"] = 1

    property["customProperties"] = []
    if field.model_extra is not None:
        for key, value in field.model_extra.items():
            property["customProperties"].append({"property": key, "value": value})
    if field.pii is not None:
        property["customProperties"].append({"property": "pii", "value": field.pii})
    if property.get("customProperties") is not None and len(property["customProperties"]) == 0:
        del property["customProperties"]

    property["tags"] = []
    if field.tags is not None:
        property["tags"].extend(field.tags)
    if not property["tags"]:
        del property["tags"]

    property["logicalTypeOptions"] = {}
    if field.minLength is not None:
        property["logicalTypeOptions"]["minLength"] = field.minLength
    if field.maxLength is not None:
        property["logicalTypeOptions"]["maxLength"] = field.maxLength
    if field.pattern is not None:
        property["logicalTypeOptions"]["pattern"] = field.pattern
    if field.minimum is not None:
        property["logicalTypeOptions"]["minimum"] = field.minimum
    if field.maximum is not None:
        property["logicalTypeOptions"]["maximum"] = field.maximum
    if field.exclusiveMinimum is not None:
        property["logicalTypeOptions"]["exclusiveMinimum"] = field.exclusiveMinimum
    if field.exclusiveMaximum is not None:
        property["logicalTypeOptions"]["exclusiveMaximum"] = field.exclusiveMaximum
    if property["logicalTypeOptions"] == {}:
        del property["logicalTypeOptions"]

    if field.quality is not None:
        quality_list = field.quality
        quality_property = to_odcs_quality_list(quality_list)
        if len(quality_property) > 0:
            property["quality"] = quality_property

    # todo enum

    return property


def to_odcs_quality_list(quality_list):
    quality_property = []
    for quality in quality_list:
        quality_property.append(to_odcs_quality(quality))
    return quality_property


def to_odcs_quality(quality):
    quality_dict = {"type": quality.type}
    if quality.description is not None:
        quality_dict["description"] = quality.description
    if quality.query is not None:
        quality_dict["query"] = quality.query
    # dialect is not supported in v3.0.0
    if quality.mustBe is not None:
        quality_dict["mustBe"] = quality.mustBe
    if quality.mustNotBe is not None:
        quality_dict["mustNotBe"] = quality.mustNotBe
    if quality.mustBeGreaterThan is not None:
        quality_dict["mustBeGreaterThan"] = quality.mustBeGreaterThan
    if quality.mustBeGreaterThanOrEqualTo is not None:
        quality_dict["mustBeGreaterThanOrEqualTo"] = quality.mustBeGreaterThanOrEqualTo
    if quality.mustBeLessThan is not None:
        quality_dict["mustBeLessThan"] = quality.mustBeLessThan
    if quality.mustBeLessThanOrEqualTo is not None:
        quality_dict["mustBeLessThanOrEqualTo"] = quality.mustBeLessThanOrEqualTo
    if quality.mustBeBetween is not None:
        quality_dict["mustBeBetween"] = quality.mustBeBetween
    if quality.mustNotBeBetween is not None:
        quality_dict["mustNotBeBetween"] = quality.mustNotBeBetween
    if quality.engine is not None:
        quality_dict["engine"] = quality.engine
    if quality.implementation is not None:
        quality_dict["implementation"] = quality.implementation
    return quality_dict
