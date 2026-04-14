"""
normalize — ODCS contract normalization
----------------------------------------
Converts named lists in a contract dict to dicts keyed by their natural key,
so DeepDiff can match items semantically rather than by position.

DeepDiff matches list items by position by default, which produces
incorrect diffs when items are added/removed mid-list. Keying by the
natural key gives stable, semantically correct paths and meaningful
field names in the output:

    schema.orders.properties.order_id.logicalType        Changed
    rather than
    schema[0].properties[1].logicalType                  Changed

Example (schema list, inserting "customers" before "orders"):

    Before normalization — schema is a list of dicts:
        "schema": [
            {"name": "orders",    "physicalType": "table", "properties": [...]},
            {"name": "customers", "physicalType": "view",  "properties": [...]},
        ]

    After normalization — schema is a dict keyed by name, with the key field stripped:
        "schema": {
            "orders":    {"physicalType": "table", "properties": {...}},
            "customers": {"physicalType": "view",  "properties": {...}},
        }

    Without normalization, DeepDiff matches by position and reports a spurious change:
        "values_changed": {"root['schema'][0]['name']": {"old": "orders", "new": "customers"}}

    With normalization, DeepDiff matches by key and reports correctly:
        "dictionary_item_added":   {"root['schema']['customers']": {...}}
        "dictionary_item_removed": {"root['schema']['orders']": {...}}

# NOTE: Natural keys are hardcoded here because the open-data-contract-standard
# Pydantic models don't yet expose them. The planned fix is to add a __natural_key__
# class var or Field annotation to each model upstream, then replace this table with
# a single reflection-based loop that derives both the list containers and their
# natural keys from the model metadata.

Current hardcoded natural keys:
schema[]                                SchemaObject   -> .name     (required: [name])
schema[].properties[]                   SchemaProperty -> .name     (required: [name], recursive)
slaProperties[]                          SLAProperty    -> .property
servers[]                                Server         -> .server
servers[].roles[]                        Role           -> .role
servers[].customProperties[]             CustomProperty -> .property
support[]                                SupportItem    -> .channel
roles[]                                  Role           -> .role
team.members[]                           TeamMember     -> .username
authoritativeDefinitions[]               AuthoritativeDefinition -> .url
description.authoritativeDefinitions[]   AuthoritativeDefinition -> .url
description.customProperties[]           CustomProperty -> .property
"""


def _normalize_by(items: list[dict], key_field: str) -> dict:
    """Key a list of dicts by a named field, omitting the key field from the value.

    Falls back to the list index if the key field is absent on an item.
    """
    result = {}
    for i, item in enumerate(items):
        key = item.get(key_field, f"__pos_{i}__")
        result[key] = {k: v for k, v in item.items() if k != key_field}
    return result


def _normalize_auth_defs(items: list[dict]) -> dict:
    """Key authoritativeDefinitions by url with id and positional fallback.

    Unlike _normalize_by, the key (url) is retained in the value dict because
    AuthoritativeDefinition has no single required key — url is only inferred,
    so stripping it would lose data when the positional fallback fires.
    """
    result = {}
    for i, item in enumerate(items):
        key = item.get("url") or item.get("id") or f"__pos_{i}__"
        result[key] = item
    return result


def _normalize_relationships(items: list[dict], schema_level: bool = True) -> dict:
    """Key relationships by a stable composite key.

    Schema-level: from:to composite. Property-level: to only.
    Falls back to positional index if key fields are absent.
    """
    result = {}
    for i, item in enumerate(items):
        if schema_level:
            from_val = str(item.get("from", ""))
            to_val = str(item.get("to", ""))
            key = f"{from_val}:{to_val}" if (from_val or to_val) else f"__pos_{i}__"
        else:
            to_val = item.get("to")
            key = str(to_val) if to_val else f"__pos_{i}__"
        result[key] = item
    return result


def _normalize_quality(items: list[dict]) -> dict:
    """Key DataQuality items by name (with positional fallback)."""
    result = {}
    for i, item in enumerate(items):
        key = item.get("name") or f"__pos_{i}__"
        entry = {k: v for k, v in item.items() if k != "name"}
        if "customProperties" in entry and isinstance(entry["customProperties"], list):
            entry["customProperties"] = _normalize_by(entry["customProperties"], "property")
        if "authoritativeDefinitions" in entry and isinstance(entry["authoritativeDefinitions"], list):
            entry["authoritativeDefinitions"] = _normalize_auth_defs(entry["authoritativeDefinitions"])
        result[key] = entry
    return result


def _normalize_schema_fields(entry: dict, *, schema_level: bool) -> dict:
    """Normalize nested list fields shared by SchemaObject and SchemaProperty."""
    if "quality" in entry and isinstance(entry["quality"], list):
        entry["quality"] = _normalize_quality(entry["quality"])
    if "customProperties" in entry and isinstance(entry["customProperties"], list):
        entry["customProperties"] = _normalize_by(entry["customProperties"], "property")
    if "authoritativeDefinitions" in entry and isinstance(entry["authoritativeDefinitions"], list):
        entry["authoritativeDefinitions"] = _normalize_auth_defs(entry["authoritativeDefinitions"])
    if "relationships" in entry and isinstance(entry["relationships"], list):
        entry["relationships"] = _normalize_relationships(entry["relationships"], schema_level=schema_level)
    return entry


def _normalize_properties(properties: list[dict]) -> dict:
    """Recursively key SchemaProperty lists by .name."""
    result = {}
    for prop in properties:
        key = prop.get("name", prop.get("id", str(prop)))
        entry = {k: v for k, v in prop.items() if k != "name"}
        if "properties" in entry and isinstance(entry["properties"], list):
            entry["properties"] = _normalize_properties(entry["properties"])
        entry = _normalize_schema_fields(entry, schema_level=False)
        result[key] = entry
    return result


def normalize(contract: dict) -> dict:
    """Convert named lists to dicts keyed by their natural key field.

    See headers comments for more details.

    """
    out = dict(contract)

    if "schema" in out and isinstance(out["schema"], list):
        normalized_schema = {}
        for tbl in out["schema"]:
            key = tbl.get("name", tbl.get("id", str(tbl)))
            entry = {k: v for k, v in tbl.items() if k != "name"}
            if "properties" in entry and isinstance(entry["properties"], list):
                entry["properties"] = _normalize_properties(entry["properties"])
            entry = _normalize_schema_fields(entry, schema_level=True)
            normalized_schema[key] = entry
        out["schema"] = normalized_schema

    if "slaProperties" in out and isinstance(out["slaProperties"], list):
        out["slaProperties"] = _normalize_by(out["slaProperties"], "property")

    if "servers" in out and isinstance(out["servers"], list):
        normalized_servers = {}
        for s in out["servers"]:
            if not s.get("server"):
                continue
            key = s["server"]
            entry = {k: v for k, v in s.items() if k != "server"}
            if "roles" in entry and isinstance(entry["roles"], list):
                entry["roles"] = _normalize_by(entry["roles"], "role")
            if "customProperties" in entry and isinstance(entry["customProperties"], list):
                entry["customProperties"] = _normalize_by(entry["customProperties"], "property")
            normalized_servers[key] = entry
        out["servers"] = normalized_servers

    if "support" in out and isinstance(out["support"], list):
        out["support"] = _normalize_by(out["support"], "channel")

    if "roles" in out and isinstance(out["roles"], list):
        out["roles"] = _normalize_by(out["roles"], "role")

    if "customProperties" in out and isinstance(out["customProperties"], list):
        out["customProperties"] = _normalize_by(out["customProperties"], "property")

    if "team" in out:
        team = out["team"]
        if isinstance(team, dict) and "members" in team and isinstance(team["members"], list):
            out["team"] = {**team, "members": _normalize_by(team["members"], "username")}
        elif isinstance(team, list):
            out["team"] = _normalize_by(team, "username")

    if "authoritativeDefinitions" in out and isinstance(out["authoritativeDefinitions"], list):
        out["authoritativeDefinitions"] = _normalize_auth_defs(out["authoritativeDefinitions"])

    if "description" in out and isinstance(out["description"], dict):
        desc = out["description"]
        normalized_desc = dict(desc)
        if "authoritativeDefinitions" in desc and isinstance(desc["authoritativeDefinitions"], list):
            normalized_desc["authoritativeDefinitions"] = _normalize_auth_defs(desc["authoritativeDefinitions"])
        if "customProperties" in desc and isinstance(desc["customProperties"], list):
            normalized_desc["customProperties"] = _normalize_by(desc["customProperties"], "property")
        out["description"] = normalized_desc

    return out
