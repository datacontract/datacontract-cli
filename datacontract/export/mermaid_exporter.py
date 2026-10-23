from open_data_contract_standard.model import OpenDataContractStandard

from datacontract.export.exporter import Exporter


class MermaidExporter(Exporter):
    def export(self, data_contract, schema_name, server, sql_server_type, export_args) -> str | None:
        return to_mermaid(data_contract)


# Mermaid refuses to render a diagram above its `maxTextSize` setting (50000 characters by default).
MAX_TEXT_SIZE = 50000
# Once the diagram is too large, entities keep at most this many attributes (the others are replaced by an ellipsis)
# and their names are cut to the maximum length.
MAX_ATTRIBUTES = 5
MAX_ENTITY_NAME_LENGTH = 32


def to_mermaid(data_contract: OpenDataContractStandard) -> str | None:
    """Convert ODCS data contract to Mermaid ER diagram."""
    return to_mermaid_and_reduced(data_contract)[0]


def to_mermaid_and_reduced(data_contract: OpenDataContractStandard) -> tuple[str | None, bool]:
    """Convert to a Mermaid ER diagram, and tell whether it had to be reduced because it was too large.

    A reduced diagram has at most MAX_ATTRIBUTES per entity and entity names cut to MAX_ENTITY_NAME_LENGTH, so its
    entities no longer match the names of the data contract.
    """
    try:
        if not data_contract.schema_:
            return None, False
        diagram = _build_diagram(data_contract)
        if len(diagram) > MAX_TEXT_SIZE:
            return _build_diagram(data_contract, reduced=True), True
        return diagram, False

    except Exception as e:
        print(f"Error generating ODCS mermaid diagram: {e}")
        return None, False


def _build_diagram(data_contract: OpenDataContractStandard, reduced: bool = False) -> str:
    max_attributes = MAX_ATTRIBUTES if reduced else None
    entity_names: dict[str, str] = {}

    def entity_name(name: str) -> str:
        clean = _sanitize_name(name)
        if not reduced:
            return clean
        if name not in entity_names:
            candidate, n = clean[:MAX_ENTITY_NAME_LENGTH], 1
            while candidate in entity_names.values():  # two long names with the same beginning
                n += 1
                candidate = f"{clean[: MAX_ENTITY_NAME_LENGTH - len(str(n)) - 1]}_{n}"
            entity_names[name] = candidate
        return entity_names[name]

    mmd_entity = "erDiagram\n"
    mmd_references = []
    ids = _collect_ids(data_contract)

    # ODCS 3.2: relationships are declared on a property (implicit `from`) or on the schema (explicit `from`)
    relationships = []  # (from_model, from_fields, to_model, to_fields)
    for schema in data_contract.schema_:
        schema_name = schema.name or schema.physicalName
        for rel in schema.relationships or []:
            relationships.append(_resolve(rel, schema_name, None, ids))
        for prop in schema.properties or []:
            for rel in prop.relationships or []:
                relationships.append(_resolve(rel, schema_name, prop.name, ids))
    relationships = [r for r in relationships if r]
    fk_fields = {(model, field) for model, fields, _, _ in relationships for field in fields}

    for schema in data_contract.schema_:
        schema_name = schema.name or schema.physicalName
        clean_model = entity_name(schema_name)
        entity_block = ""

        properties = schema.properties or []
        truncated = max_attributes is not None and len(properties) > max_attributes
        if truncated:
            # keep primary keys, then foreign keys, then unique fields, then the first others, in schema order
            def rank(prop):
                if prop.primaryKey:
                    return 0
                if (schema_name, prop.name) in fk_fields:
                    return 1
                return 2 if prop.unique else 3

            kept = sorted(range(len(properties)), key=lambda i: (rank(properties[i]), i))[:max_attributes]
            properties = [properties[i] for i in sorted(kept)]

        for prop in properties:
            clean_name = _sanitize_name(prop.name)
            prop_type = _sanitize_name(prop.logicalType or prop.physicalType or "unknown")
            entity_block += _field_line(
                clean_name,
                prop_type,
                pk=bool(prop.primaryKey),
                uk=bool(prop.unique),
                fk=(schema_name, prop.name) in fk_fields,
            )

        if truncated:
            entity_block += "\t… …\n"
        mmd_entity += f'\t"**{clean_model}**" {{\n{entity_block}}}\n'

    for from_model, from_fields, to_model, to_fields in relationships:
        # Mermaid requires a label, but it may be empty
        label = ""
        if not reduced:
            label = f"{', '.join(map(_sanitize_name, from_fields))} → {', '.join(map(_sanitize_name, to_fields))}"
        line = f'"**{entity_name(to_model)}**" ||--o{{ "**{entity_name(from_model)}**" : "{label}"'
        if line not in mmd_references:
            mmd_references.append(line)

    if mmd_references:
        mmd_entity += "\n" + "\n".join(mmd_references)

    return mmd_entity + "\n"


def _collect_ids(data_contract: OpenDataContractStandard) -> dict[str, str]:
    """Map schema/property ids to names, to resolve fully qualified references (`schema/<id>/properties/<id>`)."""
    ids = {}
    for schema in data_contract.schema_:
        if schema.id:
            ids[schema.id] = schema.name or schema.physicalName
        for prop in schema.properties or []:
            if prop.id:
                ids[prop.id] = prop.name
    return ids


def _parse_reference(ref: str, ids: dict[str, str]) -> tuple[str, str] | None:
    """Split a shorthand (`table.column`) or fully qualified (`schema/<id>/properties/<id>`) reference."""
    if "/" in ref:
        segments = ref.split("#")[-1].strip("/").split("/")
        if len(segments) < 4:
            return None
        return ids.get(segments[1], segments[1]), ids.get(segments[-1], segments[-1])
    model, _, field = ref.partition(".")
    return (model, field) if field else None


def _resolve(rel, schema_name: str, prop_name: str | None, ids: dict[str, str]):
    """Normalize a relationship to (from_model, from_fields, to_model, to_fields); None if unusable."""
    if (rel.type or "foreignKey") != "foreignKey":
        return None
    sources = [f"{schema_name}.{prop_name}"] if prop_name else rel.from_
    targets = rel.to
    if not sources or not targets:
        return None
    sources = [sources] if isinstance(sources, str) else sources
    targets = [targets] if isinstance(targets, str) else targets
    froms = [_parse_reference(ref, ids) for ref in sources]
    tos = [_parse_reference(ref, ids) for ref in targets]
    if None in froms or None in tos:
        return None
    return froms[0][0], [f for _, f in froms], tos[0][0], [f for _, f in tos]


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
        indicators += "🆔"
    if fk:
        indicators += "🔗"
    return f"\t{name}{indicators} {field_type}\n"
