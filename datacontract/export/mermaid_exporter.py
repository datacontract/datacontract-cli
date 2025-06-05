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


def dcs_to_mermaid(data_contract_spec):
    mmd_entity = "erDiagram\n\t"
    mmd_references = []
    try:
        for model_name, model in data_contract_spec.models.items():
            entity_block = ""
            for field_name, field in model.fields.items():
                entity_block += f"\t{field_name.replace('#', 'Nb').replace(' ', '_').replace('/', 'by')}{'🔑' if field.primaryKey or (field.unique and field.required) else ''}{'⌘' if field.references else ''} {field.type}\n"
                if field.references:
                    mmd_references.append(
                        f'"📑{field.references.split(".")[0] if "." in field.references else ""}"'
                        + "}o--{ ||"
                        + f'"📑{model_name}"'
                    )
            mmd_entity += f'\t"**{model_name}**"' + "{\n" + entity_block + "}\n"

        if mmd_entity == "":
            return None
        else:
            return f"{mmd_entity}\n"
    except Exception as e:
        print(f"error : {e}")
        return None


def odcs_to_mermaid(data_contract_spec: OpenDataContractStandard) -> str | None:
    """
    Convert OpenDataContractStandard to Mermaid ER diagram.
    ODCS uses schema_ (array) instead of models (dict) and properties instead of fields.
    """
    mmd_entity = "erDiagram\n\t"
    mmd_references = []
    try:
        if not data_contract_spec.schema_:
            return None

        for schema in data_contract_spec.schema_:
            entity_block = ""
            schema_name = schema.name or schema.physicalName

            if schema.properties:
                for prop in schema.properties:
                    prop_name = prop.name.replace("#", "Nb").replace(" ", "_").replace("/", "by")

                    # Add key indicators
                    indicators = ""
                    if prop.primaryKey:
                        indicators += "🔑"
                    if getattr(prop, "partitioned", False):
                        indicators += "🔀"
                    if getattr(prop, "criticalDataElement", False):
                        indicators += "⚠️"

                    # Use logicalType or physicalType
                    prop_type = prop.logicalType or prop.physicalType or "unknown"

                    entity_block += f"\t{prop_name}{indicators} {prop_type}\n"

                    # Handle references if they exist (ODCS doesn't have direct references like DCS)
                    # You could potentially add this if ODCS properties have reference information

            mmd_entity += f'\t"**{schema_name}**"' + "{\n" + entity_block + "}\n"

        if mmd_entity.strip() == "erDiagram":
            return None
        else:
            # Add any references
            if mmd_references:
                mmd_entity += "\n" + "\n".join(mmd_references)
            return f"{mmd_entity}\n"

    except Exception as e:
        print(f"error generating ODCS mermaid diagram: {e}")
        return None
