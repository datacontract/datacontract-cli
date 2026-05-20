"""In-memory enrichment of ODCS properties from their semantic concepts.

A contract may carry only `name`, `physicalName`, and
`authoritativeDefinitions[type=semantics]` on a property — no inline
`logicalType` / `description` / `examples` / `businessName`. That's the
"lean YAML" model: concept-level metadata lives in the semantic concept
and is resolved on demand. For readers that need those fields (type and
required checks in `datacontract test`, exports that need a column type,
etc.) this module walks the contract, resolves each semantic URL once,
and fills the in-memory property fields.

The source contract on disk is never touched. Inline values on the
property always win over the concept's; only fields that are missing
locally are inherited.

Resolution failures (no network, no key, untrusted host, 404, malformed
response) are silent — the field stays None and the caller degrades
exactly as it does today. That keeps this an additive change.
"""

from open_data_contract_standard.model import OpenDataContractStandard

from datacontract.integration.entropy_data import resolve_semantic_definition


def _first_semantic_url(prop) -> str | None:
    """Return the first `authoritativeDefinitions[type=semantics]` URL, if any."""
    defs = getattr(prop, "authoritativeDefinitions", None) or []
    for d in defs:
        if getattr(d, "type", None) == "semantics":
            url = getattr(d, "url", None)
            if url:
                return url
    return None


def _apply_concept(prop, concept: dict) -> None:
    """Merge selected concept fields into `prop` when the property lacks them.

    Mapping (concept → ODCS property attribute):
      data_type     → logicalType
      description   → description
      examples      → examples
      business_name → businessName

    Inline values are never overwritten. `examples` is treated as missing
    when it's None or an empty list.
    """
    if getattr(prop, "logicalType", None) is None and concept.get("data_type"):
        prop.logicalType = concept["data_type"]
    if getattr(prop, "description", None) is None and concept.get("description"):
        prop.description = concept["description"]
    if not getattr(prop, "examples", None) and concept.get("examples"):
        prop.examples = list(concept["examples"])
    if getattr(prop, "businessName", None) is None and concept.get("business_name"):
        prop.businessName = concept["business_name"]


def enrich_in_place(data_contract: OpenDataContractStandard, *, ssl_verification: bool = True) -> None:
    """Resolve semantic refs on every property and fill missing fields in place.

    Walks every schema and every property. For each property carrying a
    semantic authoritativeDefinition, resolves the URL once (cached) and
    applies the concept to the property's in-memory attributes. Properties
    without a semantic ref, and contracts without a schema, are skipped.

    Idempotent. Safe to call multiple times against the same in-memory
    contract: every merge is conditional on the target field being unset.
    """
    if data_contract is None or data_contract.schema_ is None:
        return
    for schema_obj in data_contract.schema_:
        for prop in schema_obj.properties or []:
            url = _first_semantic_url(prop)
            if not url:
                continue
            concept = resolve_semantic_definition(url, ssl_verification=ssl_verification)
            if concept:
                _apply_concept(prop, concept)
