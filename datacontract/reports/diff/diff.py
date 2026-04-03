"""
diff — ODCS data contract diff engine
------------------------------------------
Semantic diff of two data contract YAML files.

Normalization — planned improvement:
Natural keys are hardcoded from the ODCS JSON Schema required declarations.
The long-term fix is to encode these natural keys directly in the ODCS JSON Schema
(as an x-natural-key extension) and carry that through to the upstream 
open-data-contract-standard Pydantic models (via a __natural_key__ class var or 
Field annotation). This would collapse the helper methods and key table into 
a single reflection-based loop. See NOTE below for exact upstream change required.

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

import json
import sys

import yaml
from deepdiff import DeepDiff
from open_data_contract_standard.model import OpenDataContractStandard


class ContractDiff:
    """
    Encapsulates the full ODCS contract diff pipeline.
    """

    @staticmethod
    def _load_contract(path: str) -> dict:
        """Parse, validate via Pydantic, and return a normalised dict.

        Uses yaml.safe_load directly rather than from_file() to avoid a bug
        where from_file() passes the file path through Python's compile/exec
        machinery, causing SyntaxError on YAML values that look like octal
        integer literals (e.g. ids ending in -001).

        model_dump(exclude_none=True, by_alias=True):
          - exclude_none  - strips absent optional fields so they don't
                            produce false diffs against fields that are
                            explicitly set to their default
          - by_alias      - emits "schema" not "schema_", "from" not "from_", etc.
        """
        with open(path, encoding="utf-8") as f:
            raw = yaml.safe_load(f)
        contract = OpenDataContractStandard.model_validate(raw)
        return contract.model_dump(exclude_none=True, by_alias=True)

    @staticmethod
    def _normalize_properties(properties: list[dict]) -> dict:
        """Recursively key SchemaProperty lists by .name.

        Each property entry is passed through _normalize_schema_fields with
        schema_level=False to handle its nested lists, then properties[] is
        recursed into for nested object types.
        """
        result = {}
        for prop in properties:
            key = prop.get("name", prop.get("id", str(prop)))
            entry = {k: v for k, v in prop.items() if k != "name"}
            if "properties" in entry and isinstance(entry["properties"], list):
                entry["properties"] = ContractDiff._normalize_properties(entry["properties"])
            entry = ContractDiff._normalize_schema_fields(entry, schema_level=False)
            result[key] = entry
        return result

    @staticmethod
    def _normalize_schema_fields(entry: dict, *, schema_level: bool) -> dict:
        """Normalize nested list fields shared by SchemaObject and SchemaProperty.

        Called for every schema entry at both levels, avoiding repetition of the
        same 4-field block. The only behavioural difference between the two levels
        is the schema_level flag passed to _normalize_relationships:

            SchemaObject   (schema_level=True)  — from:to composite key
            SchemaProperty (schema_level=False) — to key only (from is implicit)

        Fields normalized:
            quality[]               DataQuality    -> .name  (via _normalize_quality)
            customProperties[]      CustomProperty -> .property
            authoritativeDefinitions[] AuthoritativeDefinition -> .url
            relationships[]         Relationship   -> from:to or to
        """
        if "quality" in entry and isinstance(entry["quality"], list):
            entry["quality"] = ContractDiff._normalize_quality(entry["quality"])
        if "customProperties" in entry and isinstance(entry["customProperties"], list):
            entry["customProperties"] = ContractDiff._normalize_by(entry["customProperties"], "property")
        if "authoritativeDefinitions" in entry and isinstance(entry["authoritativeDefinitions"], list):
            entry["authoritativeDefinitions"] = ContractDiff._normalize_auth_defs(entry["authoritativeDefinitions"])
        if "relationships" in entry and isinstance(entry["relationships"], list):
            entry["relationships"] = ContractDiff._normalize_relationships(
                entry["relationships"], schema_level=schema_level
            )
        return entry

    @staticmethod
    def _normalize_quality(items: list[dict]) -> dict:
        """Key DataQuality items by name (with positional fallback), then
        normalize nested lists within each quality rule:

            customProperties[]         CustomProperty         -> .property
            authoritativeDefinitions[] AuthoritativeDefinition -> .url
        """
        result = {}
        for i, item in enumerate(items):
            key = item.get("name") or f"__pos_{i}__"
            entry = {k: v for k, v in item.items() if k != "name"}
            if "customProperties" in entry and isinstance(entry["customProperties"], list):
                entry["customProperties"] = ContractDiff._normalize_by(entry["customProperties"], "property")
            if "authoritativeDefinitions" in entry and isinstance(entry["authoritativeDefinitions"], list):
                entry["authoritativeDefinitions"] = ContractDiff._normalize_auth_defs(entry["authoritativeDefinitions"])
            result[key] = entry
        return result

    @staticmethod
    def _normalize_auth_defs(items: list[dict]) -> dict:
        """Key authoritativeDefinitions by url with id and positional fallback.

        The ODCS schema declares no required fields on AuthoritativeDefinition, but
        url is the most semantically stable identifier — it uniquely identifies the
        external reference. Falls back to id then positional index if url is absent.

        Unlike _normalize_by, the key (url) is retained in the value dict because
        AuthoritativeDefinition has no single required key — url is only inferred,
        so stripping it would lose data when the positional fallback fires.
        """
        result = {}
        for i, item in enumerate(items):
            key = item.get("url") or item.get("id") or f"__pos_{i}__"
            result[key] = item
        return result

    @staticmethod
    def _normalize_relationships(items: list[dict], schema_level: bool = True) -> dict:
        """Key relationships by a stable composite key.

        Schema-level (RelationshipSchemaLevel): from:to composite — both required.
        Property-level (RelationshipPropertyLevel): to only — from is implicit.
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

    @staticmethod
    def _normalize_by(items: list[dict], key_field: str) -> dict:
        """Key a list of dicts by a named field, omitting the key field from the value.

        Falls back to the list index if the key field is absent on an item.
        """
        result = {}
        for i, item in enumerate(items):
            key = item.get(key_field, f"__pos_{i}__")
            result[key] = {k: v for k, v in item.items() if k != key_field}
        return result

    @staticmethod
    def _normalize(contract: dict) -> dict:
        """Convert named lists to dicts keyed by their natural key field.

        DeepDiff matches list items by position by default, which produces
        incorrect diffs when items are added/removed mid-list. Keying by the
        natural key gives stable, semantically correct paths.

        Example — v1 has schema: [orders, customers]; v2 removes orders:
            By position: DeepDiff sees orders changed to customers and customers
                         removed — both wrong.
            By name key: DeepDiff correctly sees orders removed and customers
                         unchanged.

        Natural keys are hardcoded from the ODCS JSON Schema required declarations.
        See NOTE in the module header for a future improvement path and the complete
        list of hardcoded keys.

        # NOTE: Natural keys are hardcoded here because the open-data-contract-standard
        # Pydantic models don't yet expose them. The planned fix is to add a __natural_key__
        # class var or Field annotation to each model upstream, then replace this table with
        # a single reflection-based loop. (LIST_CONTAINERS in report_helpers.py already uses
        # reflection to derive which fields are list containers; natural keys are the
        # remaining gap.)
        """
        out = dict(contract)

        if "schema" in out and isinstance(out["schema"], list):
            normalized_schema = {}
            for tbl in out["schema"]:
                key = tbl.get("name", tbl.get("id", str(tbl)))
                entry = {k: v for k, v in tbl.items() if k != "name"}
                if "properties" in entry and isinstance(entry["properties"], list):
                    entry["properties"] = ContractDiff._normalize_properties(entry["properties"])
                entry = ContractDiff._normalize_schema_fields(entry, schema_level=True)
                normalized_schema[key] = entry
            out["schema"] = normalized_schema

        if "slaProperties" in out and isinstance(out["slaProperties"], list):
            out["slaProperties"] = ContractDiff._normalize_by(out["slaProperties"], "property")

        if "servers" in out and isinstance(out["servers"], list):
            normalized_servers = {}
            for s in out["servers"]:
                if not s.get("server"):
                    continue
                key = s["server"]
                entry = {k: v for k, v in s.items() if k != "server"}
                if "roles" in entry and isinstance(entry["roles"], list):
                    entry["roles"] = ContractDiff._normalize_by(entry["roles"], "role")
                if "customProperties" in entry and isinstance(entry["customProperties"], list):
                    entry["customProperties"] = ContractDiff._normalize_by(entry["customProperties"], "property")
                normalized_servers[key] = entry
            out["servers"] = normalized_servers

        if "support" in out and isinstance(out["support"], list):
            out["support"] = ContractDiff._normalize_by(out["support"], "channel")

        if "roles" in out and isinstance(out["roles"], list):
            out["roles"] = ContractDiff._normalize_by(out["roles"], "role")

        if "customProperties" in out and isinstance(out["customProperties"], list):
            out["customProperties"] = ContractDiff._normalize_by(out["customProperties"], "property")

        # team can be a Team object (v3.1.0+) or deprecated array of TeamMember
        if "team" in out:
            team = out["team"]
            if isinstance(team, dict) and "members" in team and isinstance(team["members"], list):
                out["team"] = {**team, "members": ContractDiff._normalize_by(team["members"], "username")}
            elif isinstance(team, list):
                # deprecated array form — normalize by username as best effort
                out["team"] = ContractDiff._normalize_by(team, "username")

        if "authoritativeDefinitions" in out and isinstance(out["authoritativeDefinitions"], list):
            out["authoritativeDefinitions"] = ContractDiff._normalize_auth_defs(out["authoritativeDefinitions"])

        if "description" in out and isinstance(out["description"], dict):
            desc = out["description"]
            normalized_desc = dict(desc)
            if "authoritativeDefinitions" in desc and isinstance(desc["authoritativeDefinitions"], list):
                normalized_desc["authoritativeDefinitions"] = ContractDiff._normalize_auth_defs(
                    desc["authoritativeDefinitions"]
                )
            if "customProperties" in desc and isinstance(desc["customProperties"], list):
                normalized_desc["customProperties"] = ContractDiff._normalize_by(desc["customProperties"], "property")
            out["description"] = normalized_desc

        return out

    def _diff(self, v1: dict, v2: dict) -> dict:
        """Return the DeepDiff result as a plain dict.

        ignore_order=True   - dict key ordering is irrelevant
        verbose_level=2     - include old/new values, not just paths
        """
        n1 = self._normalize(v1)
        n2 = self._normalize(v2)
        result = DeepDiff(n1, n2, ignore_order=True, verbose_level=2)
        return json.loads(result.to_json())

    def generate(self, v1_path: str, v2_path: str) -> dict:
        """Load, normalise, and diff two ODCS contract YAML files.

        Returns a plain dict of DeepDiff results — the input expected by
        ContractDiffReport.build_report_data().

        Args:
            v1_path: path to the source (before) contract YAML
            v2_path: path to the target (after) contract YAML
        """
        v1 = self._load_contract(v1_path)
        v2 = self._load_contract(v2_path)
        return self._diff(v1, v2)


if __name__ == "__main__":
    from datacontract.reports.diff.contract_diff_report import ContractDiffReport

    _positional = []
    _output_path = None
    _fmt = "text"
    _it = iter(sys.argv[1:])
    for _a in _it:
        if _a in ("--output", "-o"):
            _output_path = next(_it, None)
        elif _a == "--html":
            _fmt = "html"
        elif not _a.startswith("--"):
            _positional.append(_a)
    if len(_positional) != 2:
        print("Usage: python diff.py <v1.yaml> <v2.yaml> [--html] [--output <file>]")
        sys.exit(1)
    ContractDiffReport().generate(
        v1_path=_positional[0],
        v2_path=_positional[1],
        fmt=_fmt,
        output_path=_output_path,
    )
