"""
changelog — ODCS contract changelog builder
---------------------------------------------
Provides two public functions:
  diff()            — normalise two ODCS contract dicts and return a raw DeepDiff dict
  build_changelog() — transform a raw DeepDiff dict into structured summary + detail data
                      ready to be rendered as a changelog report.
"""

import json
import re
from datetime import datetime, timezone

from deepdiff import DeepDiff
from open_data_contract_standard.model import OpenDataContractStandard

from datacontract.changelog.normalize import normalize


def diff(v1: dict, v2: dict) -> dict:
    """Return the DeepDiff result as a plain dict.

    ignore_order=True   - dict key ordering is irrelevant
    verbose_level=2     - include old/new values, not just paths
    """
    n1 = normalize(v1)
    n2 = normalize(v2)
    result = DeepDiff(n1, n2, ignore_order=True, verbose_level=2)
    return json.loads(result.to_json())


_CHANGE_TYPE_MAP = {
    "dictionary_item_added": "Added",
    "dictionary_item_removed": "Removed",
    "values_changed": "Updated",
    "type_changes": "Updated",
    "iterable_item_added": "Added",
    "iterable_item_removed": "Removed",
}


def build_changelog(
    source: OpenDataContractStandard,
    source_file: str | None,
    other: OpenDataContractStandard,
    other_file: str | None,
) -> dict:
    """Produce a JSON-serialisable changelog dict by diffing two ODCS contracts."""
    source_label = source_file or "v1"
    target_label = other_file or "v2"
    diff_result = diff(
        source.model_dump(exclude_none=True, by_alias=True),
        other.model_dump(exclude_none=True, by_alias=True),
    )
    return _build_changelog_from_diff(diff_result, source_label=source_label, target_label=target_label)


def _build_changelog_from_diff(diff_result: dict, source_label: str = "v1", target_label: str = "v2") -> dict:
    """Produce a JSON-serialisable dict with all data needed to render
    the full changelog.

    Both summary.changes and detail.changes share the same shape:
      {
        "path":       str,   # dot-separated field path
        "changeType": str,   # Added | Removed | Updated
        "old_value":  any,   # present for Changed/Removed; absent otherwise
        "new_value":  any,   # present for Changed/Added; absent otherwise
      }

    Summary rollup rules (detail always shows full leaf paths):
      - Scalar Changed leaf      → rolled up to parent (logicalType → field)
      - Scalar Added/Removed leaf → rolled up to parent (businessName Added → field Added)
      - Mixed Add+Remove on same parent → single entry with changeType Updated
      - Dict Added/Removed (whole object) → stays at its own path, not rolled up
      - List string item (tag)   → rolled up to the tags parent in summary;
        in detail the tag value is the final path segment (tags.pii Removed)
    """

    def _expand_to_entries(obj, change_type, base_segs):
        entries = []
        for k, v in obj.items():
            segs = base_segs + [k]
            if isinstance(v, dict):
                entry = {"path": ".".join(segs), "changeType": change_type}
                entries.append(entry)
                entries.extend(_expand_to_entries(v, change_type, segs))
            else:
                entry = {"path": ".".join(segs), "changeType": change_type}
                if change_type == "Added":
                    entry["new_value"] = v
                else:
                    entry["old_value"] = v
                entries.append(entry)
        return entries

    detail_changes = []
    for deepdiff_key, items in diff_result.items():
        change_type = _CHANGE_TYPE_MAP.get(deepdiff_key)
        if not change_type:
            continue
        for raw_path, payload in items.items():
            # match ['key'] or ["key"]
            segs = re.findall(r"""(?:\['([^']+)'\]|\["([^"]+)"\])""", raw_path)
            segs = [group[0] if group[0] else group[1] for group in segs]
            is_iterable = deepdiff_key in ("iterable_item_added", "iterable_item_removed")
            if isinstance(payload, dict) and "old_value" in payload:
                entry = {
                    "path": ".".join(segs),
                    "changeType": change_type,
                    "old_value": payload["old_value"],
                    "new_value": payload["new_value"],
                }
                detail_changes.append(entry)
            elif change_type in ("Added", "Removed") and isinstance(payload, dict):
                detail_changes.append({"path": ".".join(segs), "changeType": change_type})
                detail_changes.extend(_expand_to_entries(payload, change_type, segs))
            elif is_iterable and isinstance(payload, str):
                entry = {"path": ".".join(segs + [payload]), "changeType": change_type}
                detail_changes.append(entry)
            else:
                entry = {"path": ".".join(segs), "changeType": change_type}
                if change_type == "Added":
                    entry["new_value"] = payload
                else:
                    entry["old_value"] = payload
                detail_changes.append(entry)

    detail_changes.sort(key=lambda x: x["path"])

    detail_counts = {
        "added": sum(1 for c in detail_changes if c["changeType"] == "Added"),
        "removed": sum(1 for c in detail_changes if c["changeType"] == "Removed"),
        "updated": sum(1 for c in detail_changes if c["changeType"] == "Updated"),
    }

    summary_groups: dict[tuple, dict] = {}
    for deepdiff_key, items in diff_result.items():
        change_type = _CHANGE_TYPE_MAP.get(deepdiff_key)
        if not change_type:
            continue
        for raw_path, payload in items.items():
            segs = re.findall(r"""(?:\['([^']+)'\]|\["([^"]+)"\])""", raw_path)
            segs = [group[0] if group[0] else group[1] for group in segs]
            is_iterable = deepdiff_key in ("iterable_item_added", "iterable_item_removed")
            is_scalar_change = (
                change_type == "Updated"
                and isinstance(payload, dict)
                and "old_value" in payload
                and not isinstance(payload.get("old_value"), dict)
                and not isinstance(payload.get("new_value"), dict)
            )
            is_scalar_leaf = change_type in ("Added", "Removed") and not isinstance(payload, dict) and not is_iterable
            if is_iterable and isinstance(payload, str):
                display_segs = tuple(segs)
            elif (is_scalar_change or is_scalar_leaf) and len(segs) > 1:
                display_segs = tuple(segs[:-1])
            else:
                display_segs = tuple(segs)
            if display_segs not in summary_groups:
                summary_groups[display_segs] = {"changeType": change_type}
            else:
                if summary_groups[display_segs]["changeType"] != change_type:
                    summary_groups[display_segs]["changeType"] = "Updated"

    summary_changes = []
    for segs, data in sorted(summary_groups.items(), key=lambda x: ".".join(x[0])):
        summary_changes.append({"path": ".".join(segs), "changeType": data["changeType"]})

    summary_counts = {
        "added": sum(1 for c in summary_changes if c["changeType"] == "Added"),
        "removed": sum(1 for c in summary_changes if c["changeType"] == "Removed"),
        "updated": sum(1 for c in summary_changes if c["changeType"] == "Updated"),
    }

    return {
        "source_label": source_label,
        "target_label": target_label,
        "header": {
            "title": "ODCS Data Contract Changelog",
            "subtitle": f"{source_label} \u2192 {target_label}",
            "generated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        },
        "summary": {
            "counts": summary_counts,
            "changes": summary_changes,
        },
        "detail": {
            "counts": detail_counts,
            "changes": detail_changes,
        },
    }
