from datacontract.export.exporter import Exporter
from datacontract.model.data_contract_specification import DataContractSpecification


class MermaidExporter(Exporter):
    def export(self, data_contract, model, server, sql_server_type, export_args) -> dict:
        return to_mermaid(data_contract)


def to_mermaid(data_contract_spec: DataContractSpecification) -> str | None:
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
