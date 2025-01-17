import datetime
import logging
from typing import Any, Dict, List
from venv import logger

import yaml

from datacontract.imports.importer import Importer
from datacontract.lint.resources import read_resource
from datacontract.model.data_contract_specification import (
    DATACONTRACT_TYPES,
    Availability,
    DataContractSpecification,
    Field,
    Info,
    Model,
    Quality,
    Retention,
    Server,
    ServiceLevel,
    Terms,
)
from datacontract.model.exceptions import DataContractException


class OdcsImporter(Importer):
    def import_source(
        self, data_contract_specification: DataContractSpecification, source: str, import_args: dict
    ) -> DataContractSpecification:
        return import_odcs_v3(data_contract_specification, source)


def import_odcs_v3(data_contract_specification: DataContractSpecification, source: str) -> DataContractSpecification:
    source_str = read_resource(source)
    return import_odcs_v3_from_str(data_contract_specification, source_str)


def import_odcs_v3_from_str(
    data_contract_specification: DataContractSpecification, source_str: str
) -> DataContractSpecification:
    try:
        odcs_contract = yaml.safe_load(source_str)
    except Exception as e:
        raise DataContractException(
            type="schema",
            name="Parse ODCS contract",
            reason=f"Failed to parse odcs contract from {source_str}",
            engine="datacontract",
            original_exception=e,
        )

    data_contract_specification.id = odcs_contract["id"]
    data_contract_specification.info = import_info(odcs_contract)
    data_contract_specification.servers = import_servers(odcs_contract)
    data_contract_specification.terms = import_terms(odcs_contract)
    data_contract_specification.servicelevels = import_servicelevels(odcs_contract)
    data_contract_specification.models = import_models(odcs_contract)
    data_contract_specification.tags = import_tags(odcs_contract)

    return data_contract_specification


def import_info(odcs_contract: Dict[str, Any]) -> Info:
    info = Info()

    info.title = odcs_contract.get("name") if odcs_contract.get("name") is not None else ""

    if odcs_contract.get("version") is not None:
        info.version = odcs_contract.get("version")

    # odcs.description.purpose => datacontract.description
    if odcs_contract.get("description") is not None and odcs_contract.get("description").get("purpose") is not None:
        info.description = odcs_contract.get("description").get("purpose")

    # odcs.domain => datacontract.owner
    if odcs_contract.get("domain") is not None:
        info.owner = odcs_contract.get("domain")

    # add dataProduct as custom property
    if odcs_contract.get("dataProduct") is not None:
        info.dataProduct = odcs_contract.get("dataProduct")

    # add tenant as custom property
    if odcs_contract.get("tenant") is not None:
        info.tenant = odcs_contract.get("tenant")

    return info


def import_servers(odcs_contract: Dict[str, Any]) -> Dict[str, Server] | None:
    if odcs_contract.get("servers") is None:
        return None
    servers = {}
    for odcs_server in odcs_contract.get("servers"):
        server_name = odcs_server.get("server")
        if server_name is None:
            logger.warning("Server name is missing, skipping server")
            continue

        server = Server()
        server.type = odcs_server.get("type")
        server.description = odcs_server.get("description")
        server.environment = odcs_server.get("environment")
        server.format = odcs_server.get("format")
        server.project = odcs_server.get("project")
        server.dataset = odcs_server.get("dataset")
        server.path = odcs_server.get("path")
        server.delimiter = odcs_server.get("delimiter")
        server.endpointUrl = odcs_server.get("endpointUrl")
        server.location = odcs_server.get("location")
        server.account = odcs_server.get("account")
        server.database = odcs_server.get("database")
        server.schema_ = odcs_server.get("schema")
        server.host = odcs_server.get("host")
        server.port = odcs_server.get("port")
        server.catalog = odcs_server.get("catalog")
        server.topic = odcs_server.get("topic")
        server.http_path = odcs_server.get("http_path")
        server.token = odcs_server.get("token")
        server.dataProductId = odcs_server.get("dataProductId")
        server.outputPortId = odcs_server.get("outputPortId")
        server.driver = odcs_server.get("driver")
        server.roles = odcs_server.get("roles")

        servers[server_name] = server
    return servers


def import_terms(odcs_contract: Dict[str, Any]) -> Terms | None:
    if odcs_contract.get("description") is None:
        return None
    if (
        odcs_contract.get("description").get("usage") is not None
        or odcs_contract.get("description").get("limitations") is not None
        or odcs_contract.get("price") is not None
    ):
        terms = Terms()
        if odcs_contract.get("description").get("usage") is not None:
            terms.usage = odcs_contract.get("description").get("usage")
        if odcs_contract.get("description").get("limitations") is not None:
            terms.limitations = odcs_contract.get("description").get("limitations")
        if odcs_contract.get("price") is not None:
            terms.billing = f"{odcs_contract.get('price').get('priceAmount')} {odcs_contract.get('price').get('priceCurrency')} / {odcs_contract.get('price').get('priceUnit')}"

        return terms
    else:
        return None


def import_servicelevels(odcs_contract: Dict[str, Any]) -> ServiceLevel:
    # find the two properties we can map (based on the examples)
    sla_properties = odcs_contract.get("slaProperties") if odcs_contract.get("slaProperties") is not None else []
    availability = next((p for p in sla_properties if p["property"] == "generalAvailability"), None)
    retention = next((p for p in sla_properties if p["property"] == "retention"), None)

    if availability is not None or retention is not None:
        servicelevel = ServiceLevel()

        if availability is not None:
            value = availability.get("value")
            if isinstance(value, datetime.datetime):
                value = value.isoformat()
            servicelevel.availability = Availability(description=value)

        if retention is not None:
            servicelevel.retention = Retention(period=f"{retention.get('value')}{retention.get('unit')}")

        return servicelevel
    else:
        return None


def get_server_type(odcs_contract: Dict[str, Any]) -> str | None:
    servers = import_servers(odcs_contract)
    if servers is None or len(servers) == 0:
        return None
    # get first server from map
    server = next(iter(servers.values()))
    return server.type


def import_models(odcs_contract: Dict[str, Any]) -> Dict[str, Model]:
    custom_type_mappings = get_custom_type_mappings(odcs_contract.get("customProperties"))

    odcs_schemas = odcs_contract.get("schema") if odcs_contract.get("schema") is not None else []
    result = {}

    for odcs_schema in odcs_schemas:
        schema_name = odcs_schema.get("name")
        schema_physical_name = odcs_schema.get("physicalName")
        schema_description = odcs_schema.get("description") if odcs_schema.get("description") is not None else ""
        model_name = schema_physical_name if schema_physical_name is not None else schema_name
        model = Model(description=" ".join(schema_description.splitlines()), type="table")
        model.fields = import_fields(
            odcs_schema.get("properties"), custom_type_mappings, server_type=get_server_type(odcs_contract)
        )
        if odcs_schema.get("quality") is not None:
            # convert dict to pydantic model

            model.quality = [Quality.model_validate(q) for q in odcs_schema.get("quality")]
        model.title = schema_name
        if odcs_schema.get("dataGranularityDescription") is not None:
            model.config = {"dataGranularityDescription": odcs_schema.get("dataGranularityDescription")}
        result[model_name] = model

    return result


def import_field_config(odcs_property: Dict[str, Any], server_type=None) -> Dict[str, Any]:
    config = {}
    if odcs_property.get("criticalDataElement") is not None:
        config["criticalDataElement"] = odcs_property.get("criticalDataElement")
    if odcs_property.get("encryptedName") is not None:
        config["encryptedName"] = odcs_property.get("encryptedName")
    if odcs_property.get("partitionKeyPosition") is not None:
        config["partitionKeyPosition"] = odcs_property.get("partitionKeyPosition")
    if odcs_property.get("partitioned") is not None:
        config["partitioned"] = odcs_property.get("partitioned")

    if odcs_property.get("customProperties") is not None and isinstance(odcs_property.get("customProperties"), list):
        for item in odcs_property.get("customProperties"):
            config[item["property"]] = item["value"]

    physical_type = odcs_property.get("physicalType")
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
        elif server_type == "databricksType":
            config["databricksType"] = physical_type
        else:
            config["physicalType"] = physical_type

    return config


def has_composite_primary_key(odcs_properties) -> bool:
    primary_keys = [prop for prop in odcs_properties if prop.get("primaryKey") is not None and prop.get("primaryKey")]
    return len(primary_keys) > 1


def import_fields(
    odcs_properties: Dict[str, Any], custom_type_mappings: Dict[str, str], server_type
) -> Dict[str, Field]:
    logger = logging.getLogger(__name__)
    result = {}

    if odcs_properties is None:
        return result

    for odcs_property in odcs_properties:
        mapped_type = map_type(odcs_property.get("logicalType"), custom_type_mappings)
        if mapped_type is not None:
            property_name = odcs_property["name"]
            description = odcs_property.get("description") if odcs_property.get("description") is not None else None
            field = Field(
                description=" ".join(description.splitlines()) if description is not None else None,
                type=mapped_type,
                title=odcs_property.get("businessName"),
                required=not odcs_property.get("nullable") if odcs_property.get("nullable") is not None else False,
                primaryKey=odcs_property.get("primaryKey")
                if not has_composite_primary_key(odcs_properties) and odcs_property.get("primaryKey") is not None
                else False,
                unique=odcs_property.get("unique"),
                examples=odcs_property.get("examples") if odcs_property.get("examples") is not None else None,
                classification=odcs_property.get("classification")
                if odcs_property.get("classification") is not None
                else "",
                tags=odcs_property.get("tags") if odcs_property.get("tags") is not None else None,
                quality=odcs_property.get("quality") if odcs_property.get("quality") is not None else [],
                config=import_field_config(odcs_property, server_type),
            )
            result[property_name] = field
        else:
            logger.info(
                f"Can't map {odcs_property.get('column')} to the Datacontract Mapping types, as there is no equivalent or special mapping. Consider introducing a customProperty 'dc_mapping_{odcs_property.get('logicalName')}' that defines your expected type as the 'value'"
            )

    return result


def map_type(odcs_type: str, custom_mappings: Dict[str, str]) -> str | None:
    t = odcs_type.lower()
    if t in DATACONTRACT_TYPES:
        return t
    elif custom_mappings.get(t) is not None:
        return custom_mappings.get(t)
    else:
        return None


def get_custom_type_mappings(odcs_custom_properties: List[Any]) -> Dict[str, str]:
    result = {}
    if odcs_custom_properties is not None:
        for prop in odcs_custom_properties:
            if prop["property"].startswith("dc_mapping_"):
                odcs_type_name = prop["property"].substring(11)
                datacontract_type = prop["value"]
                result[odcs_type_name] = datacontract_type

    return result


def import_tags(odcs_contract) -> List[str] | None:
    if odcs_contract.get("tags") is None:
        return None
    return odcs_contract.get("tags")
