from open_data_contract_standard.model import OpenDataContractStandard

from datacontract.export.exporter import Exporter


class MermaidExporter(Exporter):
    def export(self, data_contract, schema_name, server, sql_server_type, export_args) -> str | None:
        return to_mermaid(data_contract)


def to_mermaid(data_contract: OpenDataContractStandard) -> str | None:
    """Convert ODCS data contract to Mermaid ER diagram."""
    try:
        if not data_contract.schema_:
            return None

        mmd_entity = "erDiagram\n"
        mmd_references = []

        for schema in data_contract.schema_:
            schema_name = schema.name or schema.physicalName
            clean_model = _sanitize_name(schema_name)
            entity_block = ""

            if schema.properties:
                for prop in schema.properties:
                    clean_name = _sanitize_name(prop.name)
                    prop_type = _sanitize_name(prop.logicalType or prop.physicalType or "unknown")

                    is_pk = bool(prop.primaryKey)
                    is_uk = bool(prop.unique)
                    is_fk = bool(prop.relationships)

                    entity_block += _field_line(clean_name, prop_type, pk=is_pk, uk=is_uk, fk=is_fk)

                    # Handle references from relationships
                    if prop.relationships:
                        for rel in prop.relationships:
                            ref_target = getattr(rel, "to", None) or getattr(rel, "ref", None)
                            if ref_target:
                                references = ref_target.replace(".", "·")
                                parts = references.split("·")
                                referenced_model = _sanitize_name(parts[0]) if len(parts) > 0 else ""
                                referenced_field = _sanitize_name(parts[1]) if len(parts) > 1 else ""
                                if referenced_model:
                                    label = referenced_field or clean_name
                                    mmd_references.append(
                                        f'"**{referenced_model}**" ||--o{{ "**{clean_model}**" : {label}'
                                    )

            mmd_entity += f'\t"**{clean_model}**" {{\n{entity_block}}}\n'

        if mmd_references:
            mmd_entity += "\n" + "\n".join(mmd_references)

        return mmd_entity + "\n"

    except Exception as e:
        print(f"Error generating ODCS mermaid diagram: {e}")
        return None


# Characters that must never reach the rendered diagram. The HTML exporter
# embeds the Mermaid source verbatim inside a `<pre class="mermaid">` block
# (marked `| safe`, since Mermaid's own arrow syntax must not be HTML-escaped),
# so any `<`, `>`, `&`, or quote coming from a model/field/type name would
# otherwise break out of that block and execute as HTML.
_HTML_UNSAFE = str.maketrans({c: "" for c in "<>&\"'`"})


def _sanitize_name(name: str) -> str:
    name = name.replace("#", "Nb").replace(" ", "_").replace("/", "by")
    return name.translate(_HTML_UNSAFE)


def _field_line(name: str, field_type: str, pk: bool = False, uk: bool = False, fk: bool = False) -> str:
    indicators = ""
    if pk:
        indicators += "🔑"
    if uk:
        indicators += "🔒"
    if fk:
        indicators += "⌘"
    return f"\t{name}{indicators} {field_type}\n"
