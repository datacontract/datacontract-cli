from typing import Dict

import yaml

from datacontract.model.data_contract_specification import DataContractSpecification, Model, Field
from datacontract.export.exporter import Exporter


class OdcsExporter(Exporter):
    def export(self, data_contract, model, server, sql_server_type, export_args) -> dict:
        return to_odcs_yaml(data_contract)


def to_odcs_yaml(data_contract_spec: DataContractSpecification):
    odcs = {
        "kind": "DataContract",
        "apiVersion": "2.3.0",
        "uuid": data_contract_spec.id,
        "version": data_contract_spec.info.version,
        "datasetDomain": data_contract_spec.info.owner,
        "quantumName": data_contract_spec.info.title,
        "status": "unknown",
    }

    if data_contract_spec.info.contact is not None:
        if data_contract_spec.info.contact.email is not None:
            odcs["productDl"] = data_contract_spec.info.contact.email
        if data_contract_spec.info.contact.email is not None:
            odcs["productFeedbackUrl"] = data_contract_spec.info.contact.url

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

    odcs["type"] = "tables"  # required, TODO read from models.type?
    odcs["dataset"] = []

    for model_key, model_value in data_contract_spec.models.items():
        odcs_table = to_odcs_table(model_key, model_value)
        odcs["dataset"].append(odcs_table)
    return yaml.dump(odcs, indent=2, sort_keys=False, allow_unicode=True)


def to_odcs_table(model_key, model_value: Model) -> dict:
    odcs_table = {
        "table": model_key,
        "physicalName": model_key,
        "columns": [],
    }
    if model_value.description is not None:
        odcs_table["description"] = model_value.description
    columns = to_columns(model_value.fields)
    if columns:
        odcs_table["columns"] = columns
    return odcs_table


def to_columns(fields: Dict[str, Field]) -> list:
    columns = []
    for field_name, field in fields.items():
        column = to_column(field_name, field)
        columns.append(column)
    return columns


def to_column(field_name: str, field: Field) -> dict:
    column = {"column": field_name}
    if field.type is not None:
        column["logicalType"] = field.type
        column["physicalType"] = field.type
    if field.description is not None:
        column["description"] = field.description
    if field.required is not None:
        column["isNullable"] = not field.required
    if field.unique is not None:
        column["isUnique"] = field.unique
    if field.classification is not None:
        column["classification"] = field.classification
    column["tags"] = []
    if field.tags is not None:
        column["tags"].extend(field.tags)
    if field.pii is not None:
        column["tags"].append(f"pii:{str(field.pii).lower()}")
    if field.minLength is not None:
        column["tags"].append(f"minLength:{field.minLength}")
    if field.maxLength is not None:
        column["tags"].append(f"maxLength:{field.maxLength}")
    if field.pattern is not None:
        column["tags"].append(f"pattern:{field.pattern}")
    if field.minimum is not None:
        column["tags"].append(f"minimum:{field.minimum}")
    if field.maximum is not None:
        column["tags"].append(f"maximum:{field.maximum}")
    if field.exclusiveMinimum is not None:
        column["tags"].append(f"exclusiveMinimum:{field.exclusiveMinimum}")
    if field.exclusiveMaximum is not None:
        column["tags"].append(f"exclusiveMaximum:{field.exclusiveMaximum}")
    if not column["tags"]:
        del column["tags"]

    # todo enum
    return column
