"""
helpers — Shared helpers for ODCS diff reports
-------------------------------------------------
Provides constants and utility functions consumed by reports

"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# LIST_CONTAINERS
# ---------------------------------------------------------------------------
#
# A "list container" is an ODCS field that holds a named list of objects
# (e.g. schema, servers, properties).
#
# Renderers use LIST_CONTAINERS to decide how to present each change:
#
#   • If the immediate parent key of a changed node is a list container (e.g.
#     the parent key is "properties" or "schema"), the node is a named list
#     item and should be rendered with a "- " prefix:
#
#         schema
#           - orders          ← list item, parent "schema" is a LIST_CONTAINER
#               physicalName  ← field inside the item, no prefix
#
#   • If the parent key is NOT a list container the node is a plain scalar or
#     nested object field, rendered with indentation only (no dash).
#
# This distinction drives consistent, human-readable output in both the
# plain-text and HTML renderers: list items visually read as entries in a
# collection, while scalar fields read as attributes of their parent object.


def _derive_list_containers() -> frozenset[str]:
    """Derive the set of ODCS container keys that hold lists of model objects.

    Reflects over every Pydantic model class in open_data_contract_standard.model
    and collects field names whose type annotation is list[<ModelClass>].  The
    resulting frozenset is the authoritative source for which normalised dict keys
    represent list containers — no separate maintenance or drift-guard needed.

    The one manual addition is "team": the Pydantic model types that field as the
    Team object, but the ODCS spec allows the deprecated list[TeamMember] form at
    runtime, which ContractDiff._normalize() handles explicitly.

    The schema_ → schema alias is applied to match the normalised key emitted by
    ContractDiff._normalize() (Pydantic uses schema_ to avoid shadowing the
    built-in, but the serialised/normalised key is always "schema").
    """
    import inspect

    from open_data_contract_standard import model as _odcs_model

    model_classes = {
        name
        for name, cls in inspect.getmembers(_odcs_model, inspect.isclass)
        if hasattr(cls, "model_fields")
    }
    keys: set[str] = set()
    for name in model_classes:
        cls = getattr(_odcs_model, name)
        for fname, field in cls.model_fields.items():
            ann = str(field.annotation)
            if "list" in ann.lower() and any(m in ann for m in model_classes):
                keys.add("schema" if fname == "schema_" else fname)

    # Deprecated list[TeamMember] form: the Pydantic model types `team` as a Team
    # object, so reflection won't pick it up, but _normalize() supports the raw
    # list form for backwards compatibility.
    keys.add("team")

    return frozenset(keys)


LIST_CONTAINERS: frozenset[str] = _derive_list_containers()


def _infer_ancestors(explicit_paths: set[str]) -> set[str]:
    """Return the set of ancestor dot-paths not already in explicit_paths.

    Used by both text and HTML renderers to insert spacer rows above grouped
    entries so that the table hierarchy is visible even when only a leaf
    field changed.

    Example:
        explicit = {"schema.orders.properties.amount"}
        → ancestors = {"schema", "schema.orders", "schema.orders.properties"}
    """
    ancestors: set[str] = set()
    for path in explicit_paths:
        segs = path.split(".")
        for i in range(1, len(segs)):
            anc = ".".join(segs[:i])
            if anc not in explicit_paths:
                ancestors.add(anc)
    return ancestors


def _flatten_value(val: Any, prefix: str = "") -> list[tuple[str, str]]:
    """Recursively flatten a dict value into (label, str_value) pairs.

    When a whole object is Added or Removed (e.g. a new schema object or a
    removed server), the diff payload is a nested dict rather than a single
    scalar. Without flattening, a renderer would have to either print a raw
    dict (ugly) or recurse itself. _flatten_value does that recursion once,
    producing a flat list of dot-separated label/value pairs that any renderer
    can iterate over directly to emit clean "key: value" lines.

    Only dict values are descended into; non-dict inputs return an empty list.

    Example:
        _flatten_value({"logicalType": "string", "required": True})
        → [("logicalType", "string"), ("required", "True")]

        _flatten_value({"quality": {"mustBeGreaterThan": 0}})
        → [("quality.mustBeGreaterThan", "0")]
    """
    items = []
    if isinstance(val, dict):
        for k, v in val.items():
            label = f"{prefix}{k}"
            if isinstance(v, dict):
                items.extend(_flatten_value(v, prefix=f"{label}."))
            else:
                items.append((label, str(v)))
    return items
