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
            entity_block = ""

            for field_name, field in model.fields.items():
                clean_name = _sanitize_name(field_name)
                indicators = ""

                if field.primaryKey or (field.unique and field.required):
                    indicators += "🔑"
                if field.references:
                    indicators += "⌘"

                field_type = field.type or "unknown"
                entity_block += f"\t{clean_name}{indicators} {field_type}\n"

                if field.references:
                    referenced_model = field.references.split(".")[0] if "." in field.references else ""
                    if referenced_model:
                        mmd_references.append(f'"📑{referenced_model}"' + "}o--{ ||" + f'"📑{model_name}"')

            mmd_entity += f'\t"**{model_name}**"' + "{\n" + entity_block + "}\n"

        if mmd_references:
            mmd_entity += "\n" + "\n".join(mmd_references)

        return f"{mmd_entity}\n"

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
