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
slaProperties[].customProperties[]       CustomProperty -> .property
slaProperties[].authoritativeDefinitions[] AuthoritativeDefinition -> .url
schema[].properties[].enum[]             EnumValue      -> .value (or .id)
schema[]/properties[].synonyms[]         Synonym        -> .synonym (or .id)
schema[]/properties[].relationships[]    Relationship   -> .id, else from:to
schema[]/properties[].quality[]          DataQuality    -> .name, else position; re-keyed by normalize_pair
context.verifiedStatements[]             VerifiedStatement -> .question (or .id)
context.constraints[]                    Constraint     -> .constraint (or .id)
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

import re

_POSITIONAL_KEY = re.compile(r"\[\d+\]")
# What a quality rule checks, as opposed to its thresholds and arguments.
_CHECK_FIELDS = ("type", "metric", "rule", "query", "engine", "implementation")


def _normalize_by(items: list[dict], key_field: str) -> dict:
    """Key a list of dicts by a named field, omitting the key field from the value.

    Falls back to the list index, as `[i]`, if the key field is absent on an item.
    (Not `__pos_i__`: DeepDiff skips `__*__` keys as private by default.)
    """
    result = {}
    for i, item in enumerate(items):
        key = item.get(key_field, f"[{i}]")
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
        key = item.get("url") or item.get("id") or f"[{i}]"
        result[key] = item
    return result


def _normalize_keyed(items: list[dict], *keys: str) -> dict:
    """Key a list of dicts by the first of ``keys`` an item carries, keeping the key in the value.

    Falls back to the list index if none of the key fields is present.
    """
    result = {}
    for i, item in enumerate(items):
        key = next((str(item[k]) for k in keys if item.get(k) is not None), None) or f"[{i}]"
        result[key] = item
    return result


def _normalize_context(context) -> object:
    """Key the lists of a context block; a plain-string context is returned unchanged."""
    if not isinstance(context, dict):
        return context
    entry = dict(context)
    if isinstance(entry.get("verifiedStatements"), list):
        entry["verifiedStatements"] = _normalize_keyed(entry["verifiedStatements"], "id", "question")
    if isinstance(entry.get("constraints"), list):
        entry["constraints"] = _normalize_keyed(entry["constraints"], "id", "constraint")
    return entry


def _normalize_relationships(items: list[dict], schema_level: bool = True) -> dict:
    """Key relationships by their id (ODCS v3.2.0), else by a stable composite key.

    Schema-level: from:to composite. Property-level: to only.
    Falls back to positional index if key fields are absent.
    """
    result = {}
    for i, item in enumerate(items):
        if item.get("id"):
            key = str(item["id"])
        elif schema_level:
            from_val = str(item.get("from", ""))
            to_val = str(item.get("to", ""))
            key = f"{from_val}:{to_val}" if (from_val or to_val) else f"[{i}]"
        else:
            to_val = item.get("to")
            key = str(to_val) if to_val else f"[{i}]"
        result[key] = item
    return result


def _normalize_quality(items: list[dict]) -> dict:
    """Key DataQuality items by name (with positional fallback)."""
    result = {}
    for i, item in enumerate(items):
        key = item.get("name") or f"[{i}]"
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
    if "synonyms" in entry and isinstance(entry["synonyms"], list):
        entry["synonyms"] = _normalize_keyed(entry["synonyms"], "id", "synonym")
    if "enum" in entry and isinstance(entry["enum"], list):
        entry["enum"] = _normalize_keyed(entry["enum"], "id", "value")
    if "context" in entry:
        entry["context"] = _normalize_context(entry["context"])
    return entry


def _normalize_properties(properties: list[dict]) -> dict:
    """Recursively key SchemaProperty lists by .name."""
    result = {}
    for prop in properties:
        key = prop.get("name", prop.get("id", str(prop)))
        entry = {k: v for k, v in prop.items() if k != "name"}
        entry = _normalize_property_children(entry)
        entry = _normalize_schema_fields(entry, schema_level=False)
        result[key] = entry
    return result


def _normalize_property_children(entry: dict) -> dict:
    """Recurse into the nested property definitions of a property: properties, items, map key and value."""
    if "properties" in entry and isinstance(entry["properties"], list):
        entry["properties"] = _normalize_properties(entry["properties"])
    if isinstance(entry.get("items"), dict):
        entry["items"] = _normalize_schema_fields(
            _normalize_property_children(dict(entry["items"])), schema_level=False
        )
    if isinstance(entry.get("map"), dict):
        entry["map"] = {
            side: _normalize_schema_fields(_normalize_property_children(dict(definition)), schema_level=False)
            if isinstance(definition, dict)
            else definition
            for side, definition in entry["map"].items()
        }
    return entry


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
        sla_properties = _normalize_by(out["slaProperties"], "property")
        for entry in sla_properties.values():
            if isinstance(entry.get("customProperties"), list):
                entry["customProperties"] = _normalize_by(entry["customProperties"], "property")
            if isinstance(entry.get("authoritativeDefinitions"), list):
                entry["authoritativeDefinitions"] = _normalize_auth_defs(entry["authoritativeDefinitions"])
        out["slaProperties"] = sla_properties

    if "context" in out:
        out["context"] = _normalize_context(out["context"])

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


def normalize_pair(v1: dict, v2: dict) -> tuple[dict, dict]:
    """Normalize two versions of a contract, giving each quality rule the same key in both."""
    n1, n2 = normalize(v1), normalize(v2)
    _pair_owners(n1.get("schema"), n2.get("schema"))
    return n1, n2


def _pair_owners(owners1, owners2):
    """Pair the quality rules of the schema objects or properties present in both versions, recursively."""
    if not isinstance(owners1, dict) or not isinstance(owners2, dict):
        return
    for key in owners1.keys() & owners2.keys():
        owner1, owner2 = owners1[key], owners2[key]
        if not isinstance(owner1, dict) or not isinstance(owner2, dict):
            continue
        if isinstance(owner1.get("quality"), dict) and isinstance(owner2.get("quality"), dict):
            owner1["quality"], owner2["quality"] = _pair_quality(owner1["quality"], owner2["quality"])
        _pair_owners(owner1.get("properties"), owner2.get("properties"))
        _pair_owners(owner1.get("map"), owner2.get("map"))
        if isinstance(owner1.get("items"), dict) and isinstance(owner2.get("items"), dict):
            _pair_owners({"items": owner1["items"]}, {"items": owner2["items"]})


def _pair_quality(rules1: dict, rules2: dict) -> tuple[dict, dict]:
    """Re-key two versions of a quality list so that a rule carries the same key in both.

    A rule pairs by id, then by name, then by what it checks, then, if nameless on both sides, by position.
    """
    side1, side2 = (
        [(key, None if _POSITIONAL_KEY.fullmatch(key) else key, rule) for key, rule in rules.items()]
        for rules in (rules1, rules2)
    )
    pairs: dict[int, int] = {}  # index in side2 -> index in side1
    paired1: set[int] = set()
    for tier in range(4):
        for j, (_, name2, rule2) in enumerate(side2):
            if j in pairs:
                continue
            for i, (_, name1, rule1) in enumerate(side1):
                if i in paired1:
                    continue
                if (
                    (tier == 0 and rule1.get("id") is not None and rule1.get("id") == rule2.get("id"))
                    or (tier == 1 and name1 is not None and name1 == name2)
                    or (tier == 2 and all(rule1.get(field) == rule2.get(field) for field in _CHECK_FIELDS))
                    or (tier == 3 and name1 is None and name2 is None)
                ):
                    pairs[j] = i
                    paired1.add(i)
                    break

    # Paired nameless rules take their position from the side that also has unpaired nameless rules, so no key clashes.
    positions_from_v1 = any(name is None and i not in paired1 for i, (_, name, _) in enumerate(side1))
    out1 = {key: rule for i, (key, _, rule) in enumerate(side1) if i not in paired1}
    out2 = {}
    for j, (key2, name2, rule2) in enumerate(side2):
        if j not in pairs:
            out2[key2] = rule2
            continue
        key1, name1, rule1 = side1[pairs[j]]
        if name1 != name2:
            # normalize strips the name, so put it back for the diff to report the rename.
            rule1 = {**rule1, "name": name1} if name1 else rule1
            rule2 = {**rule2, "name": name2} if name2 else rule2
        shared = name2 or name1 or (key1 if positions_from_v1 else key2)
        out1[shared], out2[shared] = rule1, rule2
    return out1, out2
