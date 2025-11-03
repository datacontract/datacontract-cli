import datetime
import logging
import re
from typing import Any, Dict, List
from venv import logger

from datacontract_specification.model import Quality
from open_data_contract_standard.model import CustomProperty, OpenDataContractStandard, SchemaProperty

from datacontract.imports.importer import Importer
from datacontract.lint.resources import read_resource
from datacontract.model.data_contract_specification import (
    DATACONTRACT_TYPES,
    Availability,
    DataContractSpecification,
    Field,
    Info,
    Model,
    Retention,
    Server,
    ServerRole,
    ServiceLevel,
    Terms,
)
from datacontract.model.exceptions import DataContractException


class OdcsImporter(Importer):
    def import_source(
        self, data_contract_specification: DataContractSpecification, source: str, import_args: dict
    ) -> DataContractSpecification:
        return import_odcs_v3_as_dcs(data_contract_specification, source)


def import_odcs_v3_as_dcs(
    data_contract_specification: DataContractSpecification, source: str
) -> DataContractSpecification:
    source_str = read_resource(source)
    odcs = parse_odcs_v3_from_str(source_str)
    return import_from_odcs(data_contract_specification, odcs)


def parse_odcs_v3_from_str(source_str):
    try:
        odcs = OpenDataContractStandard.from_string(source_str)
    except Exception as e:
        raise DataContractException(
            type="schema",
            name="Parse ODCS contract",
            reason=f"Failed to parse odcs contract from {source_str}",
            engine="datacontract",
            original_exception=e,
        )
    return odcs


def import_from_odcs(data_contract_specification: DataContractSpecification, odcs: OpenDataContractStandard):
    data_contract_specification.id = odcs.id
    data_contract_specification.info = import_info(odcs)
    data_contract_specification.servers = import_servers(odcs)
    data_contract_specification.terms = import_terms(odcs)
    data_contract_specification.servicelevels = import_servicelevels(odcs)
    data_contract_specification.models = import_models(odcs)
    data_contract_specification.tags = import_tags(odcs)
    return data_contract_specification


def import_info(odcs: Any) -> Info:
    info = Info()

    info.title = odcs.name if odcs.name is not None else ""

    if odcs.version is not None:
        info.version = odcs.version

    # odcs.description.purpose => datacontract.description
    if odcs.description is not None and odcs.description.purpose is not None:
        info.description = odcs.description.purpose

    # odcs.domain => datacontract.owner
    owner = get_owner(odcs.customProperties)
    if owner is not None:
        info.owner = owner

    # add dataProduct as custom property
    if odcs.dataProduct is not None:
        info.dataProduct = odcs.dataProduct

    # add tenant as custom property
    if odcs.tenant is not None:
        info.tenant = odcs.tenant

    return info


def import_server_roles(roles: List[Dict]) -> List[ServerRole] | None:
    if roles is None:
        return None
    result = []
    for role in roles:
        server_role = ServerRole()
        server_role.name = role.role
        server_role.description = role.description
        result.append(server_role)


def import_servers(odcs: OpenDataContractStandard) -> Dict[str, Server] | None:
    if odcs.servers is None:
        return None
    servers = {}
    for odcs_server in odcs.servers:
        server_name = odcs_server.server
        if server_name is None:
            logger.warning("Server name is missing, skipping server")
            continue

        server = Server()
        server.type = odcs_server.type
        server.description = odcs_server.description
        server.environment = odcs_server.environment
        server.format = odcs_server.format
        server.project = odcs_server.project
        server.dataset = odcs_server.dataset
        server.path = odcs_server.path
        server.delimiter = odcs_server.delimiter
        server.endpointUrl = odcs_server.endpointUrl
        server.location = odcs_server.location
        server.account = odcs_server.account
        server.database = odcs_server.database
        server.schema_ = odcs_server.schema_
        server.host = odcs_server.host
        server.port = odcs_server.port
        server.catalog = odcs_server.catalog
        server.stagingDir = odcs_server.stagingDir
        server.topic = getattr(odcs_server, "topic", None)
        server.http_path = getattr(odcs_server, "http_path", None)
        server.token = getattr(odcs_server, "token", None)
        server.driver = getattr(odcs_server, "driver", None)
        server.roles = import_server_roles(odcs_server.roles)
        server.storageAccount = (
            to_azure_storage_account(odcs_server.location)
            if server.type == "azure" and "://" in server.location
            else None
        )

        servers[server_name] = server
    return servers


def import_terms(odcs: Any) -> Terms | None:
    if odcs.description is None:
        return None
    if odcs.description.usage is not None or odcs.description.limitations is not None or odcs.price is not None:
        terms = Terms()
        if odcs.description.usage is not None:
            terms.usage = odcs.description.usage
        if odcs.description.limitations is not None:
            terms.limitations = odcs.description.limitations
        if odcs.price is not None:
            terms.billing = f"{odcs.price.priceAmount} {odcs.price.priceCurrency} / {odcs.price.priceUnit}"

        return terms
    else:
        return None


def import_servicelevels(odcs: Any) -> ServiceLevel:
    # find the two properties we can map (based on the examples)
    sla_properties = odcs.slaProperties if odcs.slaProperties is not None else []
    availability = next((p for p in sla_properties if p.property == "generalAvailability"), None)
    retention = next((p for p in sla_properties if p.property == "retention"), None)

    if availability is not None or retention is not None:
        servicelevel = ServiceLevel()

        if availability is not None:
            value = availability.value
            if isinstance(value, datetime.datetime):
                value = value.isoformat()
            servicelevel.availability = Availability(description=value)

        if retention is not None:
            servicelevel.retention = Retention(period=f"{retention.value}{retention.unit}")

        return servicelevel
    else:
        return None


def get_server_type(odcs: OpenDataContractStandard) -> str | None:
    servers = import_servers(odcs)
    if servers is None or len(servers) == 0:
        return None
    # get first server from map
    server = next(iter(servers.values()))
    return server.type


def import_models(odcs: Any) -> Dict[str, Model]:
    custom_type_mappings = get_custom_type_mappings(odcs.customProperties)

    odcs_schemas = odcs.schema_ if odcs.schema_ is not None else []
    result = {}

    for odcs_schema in odcs_schemas:
        schema_name = odcs_schema.name
        schema_physical_name = odcs_schema.physicalName
        schema_description = odcs_schema.description if odcs_schema.description is not None else ""
        model_name = schema_physical_name if schema_physical_name is not None else schema_name
        model = Model(
            description=" ".join(schema_description.splitlines()) if schema_description else "",
            type="table",
            tags=odcs_schema.tags if odcs_schema.tags is not None else None,
        )
        model.fields = import_fields(odcs_schema.properties, custom_type_mappings, server_type=get_server_type(odcs))
        if odcs_schema.quality is not None:
            model.quality = convert_quality_list(odcs_schema.quality)
        model.title = schema_name
        if odcs_schema.dataGranularityDescription is not None:
            model.config = {"dataGranularityDescription": odcs_schema.dataGranularityDescription}
        result[model_name] = model

    return result


def convert_quality_list(odcs_quality_list):
    """Convert a list of ODCS DataQuality objects to datacontract Quality objects"""
    quality_list = []

    if odcs_quality_list is not None:
        for odcs_quality in odcs_quality_list:
            quality = Quality(type=odcs_quality.type)

            if odcs_quality.description is not None:
                quality.description = odcs_quality.description
            if odcs_quality.query is not None:
                quality.query = odcs_quality.query
            if odcs_quality.rule is not None:
                quality.metric = odcs_quality.rule
            if odcs_quality.mustBe is not None:
                quality.mustBe = odcs_quality.mustBe
            if odcs_quality.mustNotBe is not None:
                quality.mustNotBe = odcs_quality.mustNotBe
            if odcs_quality.mustBeGreaterThan is not None:
                quality.mustBeGreaterThan = odcs_quality.mustBeGreaterThan
            if odcs_quality.mustBeGreaterOrEqualTo is not None:
                quality.mustBeGreaterOrEqualTo = odcs_quality.mustBeGreaterOrEqualTo
            if odcs_quality.mustBeLessThan is not None:
                quality.mustBeLessThan = odcs_quality.mustBeLessThan
            if odcs_quality.mustBeLessOrEqualTo is not None:
                quality.mustBeLessOrEqualTo = odcs_quality.mustBeLessOrEqualTo
            if odcs_quality.mustBeBetween is not None:
                quality.mustBeBetween = odcs_quality.mustBeBetween
            if odcs_quality.mustNotBeBetween is not None:
                quality.mustNotBeBetween = odcs_quality.mustNotBeBetween
            if odcs_quality.engine is not None:
                quality.engine = odcs_quality.engine
            if odcs_quality.implementation is not None:
                quality.implementation = odcs_quality.implementation
            if odcs_quality.businessImpact is not None:
                quality.model_extra["businessImpact"] = odcs_quality.businessImpact
            if odcs_quality.dimension is not None:
                quality.model_extra["dimension"] = odcs_quality.dimension
            if odcs_quality.schedule is not None:
                quality.model_extra["schedule"] = odcs_quality.schedule
            if odcs_quality.scheduler is not None:
                quality.model_extra["scheduler"] = odcs_quality.scheduler
            if odcs_quality.severity is not None:
                quality.model_extra["severity"] = odcs_quality.severity
            if odcs_quality.method is not None:
                quality.model_extra["method"] = odcs_quality.method
            if odcs_quality.customProperties is not None:
                quality.model_extra["customProperties"] = []
                for item in odcs_quality.customProperties:
                    quality.model_extra["customProperties"].append(
                        {
                            "property": item.property,
                            "value": item.value,
                        }
                    )

            quality_list.append(quality)

    return quality_list


def import_field_config(odcs_property: SchemaProperty, server_type=None) -> dict[Any, Any] | None:
    config = {}
    if odcs_property.criticalDataElement is not None:
        config["criticalDataElement"] = odcs_property.criticalDataElement
    if odcs_property.encryptedName is not None:
        config["encryptedName"] = odcs_property.encryptedName
    if odcs_property.partitionKeyPosition is not None:
        config["partitionKeyPosition"] = odcs_property.partitionKeyPosition
    if odcs_property.partitioned is not None:
        config["partitioned"] = odcs_property.partitioned

    if odcs_property.customProperties is not None:
        for item in odcs_property.customProperties:
            config[item.property] = item.value

    physical_type = odcs_property.physicalType
    if physical_type is not None:
        if server_type == "postgres" or server_type == "postgresql":
            config["postgresType"] = physical_type
        elif server_type == "bigquery":
            config["bigqueryType"] = physical_type
        elif server_type == "snowflake":
            config["snowflakeType"] = physical_type
        elif server_type == "redshift":
            config["redshiftType"] = physical_type
        elif server_type == "sqlserver":
            config["sqlserverType"] = physical_type
        elif server_type == "databricks":
            config["databricksType"] = physical_type
        else:
            config["physicalType"] = physical_type

    if len(config) == 0:
        return None

    return config


def has_composite_primary_key(odcs_properties: List[SchemaProperty]) -> bool:
    primary_keys = [prop for prop in odcs_properties if prop.primaryKey is not None and prop.primaryKey]
    return len(primary_keys) > 1


def import_fields(
    odcs_properties: List[SchemaProperty], custom_type_mappings: Dict[str, str], server_type
) -> Dict[str, Field]:
    result = {}

    if odcs_properties is None:
        return result

    for odcs_property in odcs_properties:
        field = import_field(odcs_property, odcs_properties, custom_type_mappings, server_type)
        if field is not None:
            result[odcs_property.name] = field

    return result


def import_field(
    odcs_property: SchemaProperty,
    odcs_properties: List[SchemaProperty],
    custom_type_mappings: Dict[str, str],
    server_type: str,
) -> Field | None:
    """
    Import a single ODCS property as a datacontract Field.
    Returns None if the property cannot be mapped.
    """
    logger = logging.getLogger(__name__)

    mapped_type = map_type(odcs_property.logicalType, custom_type_mappings, odcs_property.physicalType)

    if mapped_type is None:
        type_info = f"logicalType={odcs_property.logicalType}, physicalType={odcs_property.physicalType}"
        logger.warning(
            f"Can't map field '{odcs_property.name}' ({type_info}) to the datacontract mapping types. "
            f"Both logicalType and physicalType are missing or unmappable. "
            f"Consider introducing a customProperty 'dc_mapping_<type>' that defines your expected type as the 'value'"
        )
        return None

    description = odcs_property.description if odcs_property.description is not None else None
    field = Field(
        description=" ".join(description.splitlines()) if description is not None else None,
        type=mapped_type,
        title=odcs_property.businessName,
        required=odcs_property.required if odcs_property.required is not None else None,
        primaryKey=to_primary_key(odcs_property, odcs_properties),
        unique=odcs_property.unique if odcs_property.unique else None,
        examples=odcs_property.examples if odcs_property.examples is not None else None,
        classification=odcs_property.classification if odcs_property.classification is not None else None,
        tags=odcs_property.tags if odcs_property.tags is not None else None,
        quality=convert_quality_list(odcs_property.quality),
        fields=import_fields(odcs_property.properties, custom_type_mappings, server_type)
        if odcs_property.properties is not None
        else {},
        config=import_field_config(odcs_property, server_type),
        format=getattr(odcs_property, "format", None),
    )

    # mapped_type is array
    if field.type == "array" and odcs_property.items is not None:
        field.items = import_field(odcs_property.items, [], custom_type_mappings, server_type)

    # enum from quality validValues as enum
    if field.type == "string":
        for q in field.quality:
            if hasattr(q, "validValues"):
                field.enum = q.validValues

    return field


def to_primary_key(odcs_property: SchemaProperty, odcs_properties: list[SchemaProperty]) -> bool | None:
    if odcs_property.primaryKey is None:
        return None
    if has_composite_primary_key(odcs_properties):
        return None
    return odcs_property.primaryKey


def map_type(odcs_logical_type: str, custom_mappings: Dict[str, str], physical_type: str = None) -> str | None:
    # Try to map logicalType first
    if odcs_logical_type is not None:
        t = odcs_logical_type.lower()
        if t in DATACONTRACT_TYPES:
            return t
        elif custom_mappings.get(t) is not None:
            return custom_mappings.get(t)

    # Fallback to physicalType if logicalType is not mapped
    if physical_type is not None:
        pt = physical_type.lower()
        # Remove parameters from physical type (e.g., VARCHAR(50) -> varchar, DECIMAL(10,2) -> decimal)
        pt_base = pt.split("(")[0].strip()

        # Try direct mapping of physical type
        if pt in DATACONTRACT_TYPES:
            return pt
        elif pt_base in DATACONTRACT_TYPES:
            return pt_base
        elif custom_mappings.get(pt) is not None:
            return custom_mappings.get(pt)
        elif custom_mappings.get(pt_base) is not None:
            return custom_mappings.get(pt_base)
        # Common physical type mappings
        elif pt_base in ["varchar", "char", "nvarchar", "nchar", "text", "ntext", "string", "character varying"]:
            return "string"
        elif pt_base in ["int", "integer", "smallint", "tinyint", "mediumint", "int2", "int4", "int8"]:
            return "int"
        elif pt_base in ["bigint", "long", "int64"]:
            return "long"
        elif pt_base in ["float", "real", "float4", "float8"]:
            return "float"
        elif pt_base in ["double", "double precision"]:
            return "double"
        elif pt_base in ["decimal", "numeric", "number"]:
            return "decimal"
        elif pt_base in ["boolean", "bool", "bit"]:
            return "boolean"
        elif pt_base in ["timestamp", "datetime", "datetime2", "timestamptz", "timestamp with time zone"]:
            return "timestamp"
        elif pt_base in ["date"]:
            return "date"
        elif pt_base in ["time"]:
            return "time"
        elif pt_base in ["json", "jsonb"]:
            return "json"
        elif pt_base in ["array"]:
            return "array"
        elif pt_base in ["object", "struct", "record"]:
            return "object"
        elif pt_base in ["bytes", "binary", "varbinary", "blob", "bytea"]:
            return "bytes"
        else:
            return None
    return None


def get_custom_type_mappings(odcs_custom_properties: List[CustomProperty]) -> Dict[str, str]:
    result = {}
    if odcs_custom_properties is not None:
        for prop in odcs_custom_properties:
            if prop.property.startswith("dc_mapping_"):
                odcs_type_name = prop.property[11:]  # Changed substring to slice
                datacontract_type = prop.value
                result[odcs_type_name] = datacontract_type

    return result


def get_owner(odcs_custom_properties: List[CustomProperty]) -> str | None:
    if odcs_custom_properties is not None:
        for prop in odcs_custom_properties:
            if prop.property == "owner":
                return prop.value

    return None


def import_tags(odcs: OpenDataContractStandard) -> List[str] | None:
    if odcs.tags is None:
        return None
    return odcs.tags


def to_azure_storage_account(location: str) -> str | None:
    """
    Converts a storage location string to extract the storage account name.
    ODCS v3.0 has no explicit field for the storage account. It uses the location field, which is a URI.

    This function parses a storage location string to identify and return the
    storage account name. It handles two primary patterns:
    1. Protocol://containerName@storageAccountName
    2. Protocol://storageAccountName

    :param location: The storage location string to parse, typically following
                     the format protocol://containerName@storageAccountName. or
                     protocol://storageAccountName.
    :return: The extracted storage account name if found, otherwise None
    """
    # to catch protocol://containerName@storageAccountName. pattern from location
    match = re.search(r"(?<=@)([^.]*)", location, re.IGNORECASE)
    if match:
        return match.group()
    else:
        # to catch protocol://storageAccountName. pattern from location
        match = re.search(r"(?<=//)(?!@)([^.]*)", location, re.IGNORECASE)
    return match.group() if match else None
