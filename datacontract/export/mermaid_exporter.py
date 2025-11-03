from open_data_contract_standard.model import OpenDataContractStandard

from datacontract.export.exporter import Exporter
from datacontract.model.data_contract_specification import DataContractSpecification


class MermaidExporter(Exporter):
    def export(self, data_contract, model, server, sql_server_type, export_args) -> dict:
        return to_mermaid(data_contract)


def to_mermaid(data_contract_spec: DataContractSpecification | OpenDataContractStandard) -> str | None:
    if isinstance(data_contract_spec, DataContractSpecification):
        return dcs_to_mermaid(data_contract_spec)
    elif isinstance(data_contract_spec, OpenDataContractStandard):
        return odcs_to_mermaid(data_contract_spec)
    else:
        return None


def dcs_to_mermaid(data_contract_spec: DataContractSpecification) -> str | None:
    try:
        if not data_contract_spec.models:
            return None

        mmd_entity = "erDiagram\n"
        mmd_references = []

        for model_name, model in data_contract_spec.models.items():
            clean_model = _sanitize_name(model_name)
            entity_block = ""

            for field_name, field in model.fields.items():
                clean_name = _sanitize_name(field_name)
                field_type = field.type or "unknown"

                is_pk = bool(field.primaryKey or (field.unique and field.required))
                is_fk = bool(field.references)

                entity_block += _field_line(clean_name, field_type, pk=is_pk, uk=bool(field.unique), fk=is_fk)

                if field.references:
                    references = field.references.replace(".", "·")
                    parts = references.split("·")
                    referenced_model = _sanitize_name(parts[0]) if len(parts) > 0 else ""
                    referenced_field = _sanitize_name(parts[1]) if len(parts) > 1 else ""
                    if referenced_model:
                        label = referenced_field or clean_name
                        mmd_references.append(f'"**{referenced_model}**" ||--o{{ "**{clean_model}**" : {label}')

            mmd_entity += f'\t"**{clean_model}**" {{\n{entity_block}}}\n'

        if mmd_references:
            mmd_entity += "\n" + "\n".join(mmd_references)

        return mmd_entity + "\n"

    except Exception as e:
        print(f"Error generating DCS mermaid diagram: {e}")
        return None


def odcs_to_mermaid(data_contract_spec: OpenDataContractStandard) -> str | None:
    try:
        if not data_contract_spec.schema_:
            return None

        mmd_entity = "erDiagram\n"

        for schema in data_contract_spec.schema_:
            schema_name = schema.name or schema.physicalName
            entity_block = ""

            if schema.properties:
                for prop in schema.properties:
                    clean_name = _sanitize_name(prop.name)
                    indicators = ""

                    if prop.primaryKey:
                        indicators += "🔑"
                    if getattr(prop, "partitioned", False):
                        indicators += "🔀"
                    if getattr(prop, "criticalDataElement", False):
                        indicators += "⚠️"

                    prop_type = prop.logicalType or prop.physicalType or "unknown"
                    entity_block += f"\t{clean_name}{indicators} {prop_type}\n"

            mmd_entity += f'\t"**{schema_name}**"' + "{\n" + entity_block + "}\n"

        return f"{mmd_entity}\n"

    except Exception as e:
        print(f"Error generating ODCS mermaid diagram: {e}")
        return None


def _sanitize_name(name: str) -> str:
    return name.replace("#", "Nb").replace(" ", "_").replace("/", "by")


def _field_line(name: str, field_type: str, pk: bool = False, uk: bool = False, fk: bool = False) -> str:
    indicators = ""
    if pk:
        indicators += "🔑"
    if uk:
        indicators += "🔒"
    if fk:
        indicators += "⌘"
    return f"\t{name}{indicators} {field_type}\n"
