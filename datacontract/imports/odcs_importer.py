import datetime
import logging
from typing import Any, Dict, List
import yaml
from datacontract.model.data_contract_specification import Availability, Contact, DataContractSpecification, Info, Model, Field, Retention, Server, ServiceLevel, Terms
from datacontract.model.exceptions import DataContractException

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
    "null"
]


def import_odcs(data_contract_specification: DataContractSpecification, source: str) -> DataContractSpecification:
    
    try:
        with open(source, "r") as file:
            odcs_contract = yaml.safe_load(file.read())

    except Exception as e:
        raise DataContractException(
            type="schema",
            name="Parse ODCS contract",
            reason=f"Failed to parse odcs contract from {source}",
            engine="datacontract",
            original_exception=e,
        )

    data_contract_specification.id = odcs_contract["uuid"]
    data_contract_specification.info = import_info(odcs_contract)
    data_contract_specification.servers["default"] = import_servers(odcs_contract)
    data_contract_specification.terms = import_terms(odcs_contract)
    data_contract_specification.servicelevels = import_servicelevels(odcs_contract)
    data_contract_specification.models = import_models(odcs_contract)
    
    return data_contract_specification


def import_info(odcs_contract: Dict[str, Any]) -> Info:
    return Info(
        title = odcs_contract["quantumName"],
        version = odcs_contract["version"],
        description = odcs_contract["description"]["purpose"],
        owner = odcs_contract["tenant"],
        contact = Contact(name=odcs_contract["productDl"], url= odcs_contract["productFeedbackUrl"])
    )

def import_servers(odcs_contract: Dict[str, Any]) -> Dict[str, Server]:
    return Server(
        type = odcs_contract["sourceSystem"],
        location = f"{odcs_contract['server']}/{odcs_contract['database']}"
    )

def import_terms(odcs_contract: Dict[str, Any]) -> Terms:
    return Terms(
        usage = odcs_contract["description"]["usage"],
        limitations = odcs_contract["description"]["limitations"],
        billing = f"{odcs_contract['price']['priceAmount']} {odcs_contract['price']['priceCurrency']} / {odcs_contract['price']['priceUnit']}"
    )

def import_servicelevels(odcs_contract: Dict[str, Any]) -> ServiceLevel:
    # find the two properties we can map (based on the examples)
    sla_properties = odcs_contract["slaProperties"]
    availability = next((p for p in sla_properties if p["property"] == "generalAvailability"), None)
    retention = next((p for p in sla_properties if p["property"] == "retention"), None)

    result = ServiceLevel()

    if availability is not None:
        value = availability["value"]
        if isinstance(value, datetime.datetime):
            value = value.isoformat()
        result.availability = Availability(description= value)

    if retention is not None:
        result.retention = Retention(period=f"{retention['value']}{retention['unit']}")
    
    return result

def import_models(odcs_contract: Dict[str, Any]) -> Dict[str, Model]:
    custom_type_mappings = get_custom_type_mappings(odcs_contract["customProperties"])

    odcs_tables = odcs_contract["dataset"]
    result = {}

    for table in odcs_tables:
        model = Model(description=table["description"], type="table")
        model.fields = import_fields(table["columns"], custom_type_mappings)
        result[table["table"]] = model

    return result

def import_fields(odcs_columns: Dict[str, Any], custom_type_mappings: Dict[str, str]) -> Dict[str, Field]:
    logger = logging.getLogger(__name__)
    result = {}

    for column in odcs_columns:
        mapped_type = map_type(column["logicalType"], custom_type_mappings)
        if mapped_type is not None:
            field = Field(
                description= column.get("description"),
                type=mapped_type,
                title= column.get("businessName"),
                required= not column.get("isNullable") if column.get("isNullable") is not None else False,
                primary= column.get("isPrimary") if column.get("isPrimary") is not None else False,
                unique= column.get("isUnique") if column.get("isUnique") is not None else False,
                classification= column.get("classification"),
                tags= column.get("tags"),
            )
            result[column["column"]] = field
        else:
            logger.info(
                f"Can't properly map {column['logicalName']} to the Datacontract Mapping types, as there is no equivalent or special mapping. Consider introducing a customProperty 'dc_mapping_{column['logicalName']}' that defines your expected type as the 'value'"
            )

    return result

def map_type(odcs_type: str, custom_mappings: Dict[str, str]) -> str|None:
    t = odcs_type.lower()
    if t in DATACONTRACT_TYPES:
        return t
    elif custom_mappings[t] is not None:
        return custom_mappings[t]
    else:
        return None

def get_custom_type_mappings(odcs_custom_properties: List[Any]) -> Dict[str, str]:
    result = {}
    for prop in odcs_custom_properties:
        if prop["property"].startswith("dc_mapping_"):
            odcs_type_name = prop["property"].substring(11)
            datacontract_type = prop["value"]
            result[odcs_type_name] = datacontract_type
    
    return result