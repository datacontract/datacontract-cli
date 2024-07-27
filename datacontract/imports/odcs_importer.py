import datetime
import logging
from typing import Any, Dict, List
import yaml
from datacontract.imports.importer import Importer
from datacontract.model.data_contract_specification import (
    Availability,
    Contact,
    DataContractSpecification,
    Info,
    Model,
    Field,
    Retention,
    ServiceLevel,
    Terms,
)
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
    "null",
]


class OdcsImporter(Importer):
    def import_source(
        self, data_contract_specification: DataContractSpecification, source: str, import_args: dict
    ) -> DataContractSpecification:
        return import_odcs(data_contract_specification, source)


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
    data_contract_specification.terms = import_terms(odcs_contract)
    data_contract_specification.servicelevels = import_servicelevels(odcs_contract)
    data_contract_specification.models = import_models(odcs_contract)

    return data_contract_specification


def import_info(odcs_contract: Dict[str, Any]) -> Info:
    info = Info(title=odcs_contract.get("quantumName"), version=odcs_contract.get("version"))

    if odcs_contract.get("description").get("purpose") is not None:
        info.description = odcs_contract.get("description").get("purpose")

    if odcs_contract.get("datasetDomain") is not None:
        info.owner = odcs_contract.get("datasetDomain")

    if odcs_contract.get("productDl") is not None or odcs_contract.get("productFeedbackUrl") is not None:
        contact = Contact()
        if odcs_contract.get("productDl") is not None:
            contact.name = odcs_contract.get("productDl")
        if odcs_contract.get("productFeedbackUrl") is not None:
            contact.url = odcs_contract.get("productFeedbackUrl")

        info.contact = contact

    return info


def import_terms(odcs_contract: Dict[str, Any]) -> Terms | None:
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


def import_models(odcs_contract: Dict[str, Any]) -> Dict[str, Model]:
    custom_type_mappings = get_custom_type_mappings(odcs_contract.get("customProperties"))

    odcs_tables = odcs_contract.get("dataset") if odcs_contract.get("dataset") is not None else []
    result = {}

    for table in odcs_tables:
        description = table.get("description") if table.get("description") is not None else ""
        model = Model(description=" ".join(description.splitlines()), type="table")
        model.fields = import_fields(table.get("columns"), custom_type_mappings)
        result[table.get("table")] = model

    return result


def import_fields(odcs_columns: Dict[str, Any], custom_type_mappings: Dict[str, str]) -> Dict[str, Field]:
    logger = logging.getLogger(__name__)
    result = {}

    for column in odcs_columns:
        mapped_type = map_type(column.get("logicalType"), custom_type_mappings)
        if mapped_type is not None:
            description = column.get("description") if column.get("description") is not None else ""
            field = Field(
                description=" ".join(description.splitlines()),
                type=mapped_type,
                title=column.get("businessName") if column.get("businessName") is not None else "",
                required=not column.get("isNullable") if column.get("isNullable") is not None else False,
                primary=column.get("isPrimary") if column.get("isPrimary") is not None else False,
                unique=column.get("isUnique") if column.get("isUnique") is not None else False,
                classification=column.get("classification") if column.get("classification") is not None else "",
                tags=column.get("tags") if column.get("tags") is not None else [],
            )
            result[column["column"]] = field
        else:
            logger.info(
                f"Can't properly map {column.get('column')} to the Datacontract Mapping types, as there is no equivalent or special mapping. Consider introducing a customProperty 'dc_mapping_{column.get('logicalName')}' that defines your expected type as the 'value'"
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
