from typing import Any, Dict

from open_data_contract_standard.model import (
    CustomProperty,
    DataQuality,
    Description,
    OpenDataContractStandard,
    Role,
    SchemaObject,
    SchemaProperty,
    Server,
    ServiceLevelAgreementProperty,
    Support,
)

from datacontract.export.exporter import Exporter
from datacontract.model.data_contract_specification import DataContractSpecification, Field, Model


class OdcsV3Exporter(Exporter):
    def export(self, data_contract, model, server, sql_server_type, export_args) -> dict:
        return to_odcs_v3_yaml(data_contract)


def to_odcs_v3_yaml(data_contract_spec: DataContractSpecification) -> str:
    result = OpenDataContractStandard(
        apiVersion="v3.0.1",
        kind="DataContract",
        id=data_contract_spec.id,
        name=data_contract_spec.info.title,
        version=data_contract_spec.info.version,
        status=to_status(data_contract_spec.info.status),
    )

    if data_contract_spec.terms is not None:
        result.description = Description(
            purpose=data_contract_spec.terms.description.strip()
            if data_contract_spec.terms.description is not None
            else None,
            usage=data_contract_spec.terms.usage.strip() if data_contract_spec.terms.usage is not None else None,
            limitations=data_contract_spec.terms.limitations.strip()
            if data_contract_spec.terms.limitations is not None
            else None,
        )

    result.schema_ = []
    for model_key, model_value in data_contract_spec.models.items():
        odcs_schema = to_odcs_schema(model_key, model_value)
        result.schema_.append(odcs_schema)

    if data_contract_spec.servicelevels is not None:
        slas = []
        if data_contract_spec.servicelevels.availability is not None:
            slas.append(
                ServiceLevelAgreementProperty(
                    property="generalAvailability", value=data_contract_spec.servicelevels.availability.description
                )
            )
        if data_contract_spec.servicelevels.retention is not None:
            slas.append(
                ServiceLevelAgreementProperty(
                    property="retention", value=data_contract_spec.servicelevels.retention.period
                )
            )

        if len(slas) > 0:
            result.slaProperties = slas

    if data_contract_spec.info.contact is not None:
        support = []
        if data_contract_spec.info.contact.email is not None:
            support.append(Support(channel="email", url="mailto:" + data_contract_spec.info.contact.email))
        if data_contract_spec.info.contact.url is not None:
            support.append(Support(channel="other", url=data_contract_spec.info.contact.url))
        if len(support) > 0:
            result.support = support

    if data_contract_spec.servers is not None and len(data_contract_spec.servers) > 0:
        servers = []

        for server_key, server_value in data_contract_spec.servers.items():
            server = Server(server=server_key, type=server_value.type or "")

            # Set all the attributes that are not None
            if server_value.environment is not None:
                server.environment = server_value.environment
            if server_value.account is not None:
                server.account = server_value.account
            if server_value.database is not None:
                server.database = server_value.database
            if server_value.schema_ is not None:
                server.schema_ = server_value.schema_
            if server_value.format is not None:
                server.format = server_value.format
            if server_value.project is not None:
                server.project = server_value.project
            if server_value.dataset is not None:
                server.dataset = server_value.dataset
            if server_value.path is not None:
                server.path = server_value.path
            if server_value.delimiter is not None:
                server.delimiter = server_value.delimiter
            if server_value.endpointUrl is not None:
                server.endpointUrl = server_value.endpointUrl
            if server_value.location is not None:
                server.location = server_value.location
            if server_value.host is not None:
                server.host = server_value.host
            if server_value.port is not None:
                server.port = server_value.port
            if server_value.catalog is not None:
                server.catalog = server_value.catalog
            if server_value.topic is not None:
                server.topic = server_value.topic
            if server_value.http_path is not None:
                server.http_path = server_value.http_path
            if server_value.token is not None:
                server.token = server_value.token
            if server_value.driver is not None:
                server.driver = server_value.driver

            if server_value.roles is not None:
                server.roles = [Role(role=role.name, description=role.description) for role in server_value.roles]

            servers.append(server)

        if len(servers) > 0:
            result.servers = servers

    custom_properties = []
    if data_contract_spec.info.owner is not None:
        custom_properties.append(CustomProperty(property="owner", value=data_contract_spec.info.owner))
    if data_contract_spec.info.model_extra is not None:
        for key, value in data_contract_spec.info.model_extra.items():
            custom_properties.append(CustomProperty(property=key, value=value))

    if len(custom_properties) > 0:
        result.customProperties = custom_properties

    return result.to_yaml()


def to_odcs_schema(model_key, model_value: Model) -> SchemaObject:
    schema_obj = SchemaObject(
        name=model_key, physicalName=model_key, logicalType="object", physicalType=model_value.type
    )

    if model_value.description is not None:
        schema_obj.description = model_value.description

    properties = to_properties(model_value.fields)
    if properties:
        schema_obj.properties = properties

    model_quality = to_odcs_quality_list(model_value.quality)
    if len(model_quality) > 0:
        schema_obj.quality = model_quality

    custom_properties = []
    if model_value.model_extra is not None:
        for key, value in model_value.model_extra.items():
            custom_properties.append(CustomProperty(property=key, value=value))

    if len(custom_properties) > 0:
        schema_obj.customProperties = custom_properties

    return schema_obj


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
    if type.lower() in ["variant"]:
        return "variant"
    if type.lower() in ["null"]:
        return None
    return None


def to_physical_type(config: Dict[str, Any]) -> str | None:
    if config is None:
        return None
    if "postgresType" in config:
        return config["postgresType"]
    elif "bigqueryType" in config:
        return config["bigqueryType"]
    elif "snowflakeType" in config:
        return config["snowflakeType"]
    elif "redshiftType" in config:
        return config["redshiftType"]
    elif "sqlserverType" in config:
        return config["sqlserverType"]
    elif "databricksType" in config:
        return config["databricksType"]
    elif "physicalType" in config:
        return config["physicalType"]
    return None


def to_property(field_name: str, field: Field) -> SchemaProperty:
    property = SchemaProperty(name=field_name)

    if field.fields:
        properties = []
        for field_name_, field_ in field.fields.items():
            property_ = to_property(field_name_, field_)
            properties.append(property_)
        property.properties = properties

    if field.items:
        items = to_property(field_name, field.items)
        items.name = None  # Clear the name for items
        property.items = items

    if field.title is not None:
        property.businessName = field.title

    if field.type is not None:
        property.logicalType = to_logical_type(field.type)
        property.physicalType = to_physical_type(field.config) or field.type

    if field.description is not None:
        property.description = field.description

    if field.required is not None:
        property.required = field.required

    if field.unique is not None:
        property.unique = field.unique

    if field.classification is not None:
        property.classification = field.classification

    if field.examples is not None:
        property.examples = field.examples.copy()

    if field.example is not None:
        property.examples = [field.example]

    if field.primaryKey is not None and field.primaryKey:
        property.primaryKey = field.primaryKey
        property.primaryKeyPosition = 1

    if field.primary is not None and field.primary:
        property.primaryKey = field.primary
        property.primaryKeyPosition = 1

    custom_properties = []
    if field.model_extra is not None:
        for key, value in field.model_extra.items():
            custom_properties.append(CustomProperty(property=key, value=value))

    if field.pii is not None:
        custom_properties.append(CustomProperty(property="pii", value=field.pii))

    if len(custom_properties) > 0:
        property.customProperties = custom_properties

    if field.tags is not None and len(field.tags) > 0:
        property.tags = field.tags

    logical_type_options = {}
    if field.minLength is not None:
        logical_type_options["minLength"] = field.minLength
    if field.maxLength is not None:
        logical_type_options["maxLength"] = field.maxLength
    if field.pattern is not None:
        logical_type_options["pattern"] = field.pattern
    if field.minimum is not None:
        logical_type_options["minimum"] = field.minimum
    if field.maximum is not None:
        logical_type_options["maximum"] = field.maximum
    if field.exclusiveMinimum is not None:
        logical_type_options["exclusiveMinimum"] = field.exclusiveMinimum
    if field.exclusiveMaximum is not None:
        logical_type_options["exclusiveMaximum"] = field.exclusiveMaximum

    if logical_type_options:
        property.logicalTypeOptions = logical_type_options

    if field.quality is not None:
        quality_list = field.quality
        quality_property = to_odcs_quality_list(quality_list)
        if len(quality_property) > 0:
            property.quality = quality_property

    return property


def to_odcs_quality_list(quality_list):
    quality_property = []
    for quality in quality_list:
        quality_property.append(to_odcs_quality(quality))
    return quality_property


def to_odcs_quality(quality):
    quality_obj = DataQuality(type=quality.type)

    if quality.description is not None:
        quality_obj.description = quality.description
    if quality.query is not None:
        quality_obj.query = quality.query
    # dialect is not supported in v3.0.0
    if quality.mustBe is not None:
        quality_obj.mustBe = quality.mustBe
    if quality.mustNotBe is not None:
        quality_obj.mustNotBe = quality.mustNotBe
    if quality.mustBeGreaterThan is not None:
        quality_obj.mustBeGreaterThan = quality.mustBeGreaterThan
    if quality.mustBeGreaterThanOrEqualTo is not None:
        quality_obj.mustBeGreaterOrEqualTo = quality.mustBeGreaterThanOrEqualTo
    if quality.mustBeLessThan is not None:
        quality_obj.mustBeLessThan = quality.mustBeLessThan
    if quality.mustBeLessThanOrEqualTo is not None:
        quality_obj.mustBeLessOrEqualTo = quality.mustBeLessThanOrEqualTo
    if quality.mustBeBetween is not None:
        quality_obj.mustBeBetween = quality.mustBeBetween
    if quality.mustNotBeBetween is not None:
        quality_obj.mustNotBeBetween = quality.mustNotBeBetween
    if quality.engine is not None:
        quality_obj.engine = quality.engine
    if quality.implementation is not None:
        quality_obj.implementation = quality.implementation

    return quality_obj


def to_status(status):
    """Convert the data contract status to ODCS v3 format."""
    if status is None:
        return "draft"  # Default to draft if no status is provided

    # Valid status values according to ODCS v3.0.1 spec
    valid_statuses = ["proposed", "draft", "active", "deprecated", "retired"]

    # Convert to lowercase for comparison
    status_lower = status.lower()

    # If status is already valid, return it as is
    if status_lower in valid_statuses:
        return status_lower

    # Default to "draft" for any non-standard status
    return "draft"
