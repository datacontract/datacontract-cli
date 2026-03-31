"""
Core report builder and pipeline orchestrator for contract diffs
"""

from __future__ import annotations

import re
from datetime import datetime, timezone

from datacontract.reports.diff.diff import ContractDiff


class ContractDiffReport:
    """
    Entry-point class for generating ODCS diff reports from the command line.
    Owns the build_report_data() pipeline and delegates rendering to the appropriate
    renderer based on the requested format.
    """

    # Maps DeepDiff keys to the canonical change type strings used in report_data.
    CHANGE_TYPE_MAP = {
        "dictionary_item_added": "Added",
        "dictionary_item_removed": "Removed",
        "values_changed": "Changed",
        "type_changes": "Changed",
        "iterable_item_added": "Added",
        "iterable_item_removed": "Removed",
    }

    def build_report_data(self, diff_result: dict, source_label: str = "v1", target_label: str = "v2") -> dict:
        """Produce a JSON-serialisable dict with all data needed to render
        the full report.

        Both summary.changes and detail.changes share the same shape:
          {
            "path":       str,   # dot-separated field path
            "changeType": str,   # Added | Removed | Changed
            "old_value":  any,   # present for Changed/Removed; absent otherwise
            "new_value":  any,   # present for Changed/Added; absent otherwise
          }

        Summary rollup rules (detail always shows full leaf paths):
          - Scalar Changed leaf      → rolled up to parent (logicalType → field)
          - Scalar Added/Removed leaf → rolled up to parent (businessName Added → field Added)
          - Mixed Add+Remove on same parent → single entry with changeType Changed
          - Dict Added/Removed (whole object) → stays at its own path, not rolled up
          - List string item (tag)   → rolled up to the tags parent in summary;
            in detail the tag value is the final path segment (tags.pii Removed)
        """

        # ── detail: fully expand added/removed dicts into individual entries ─
        def _expand_to_entries(obj, change_type, base_segs):
            """Recursively flatten a dict value into individual leaf entries.

            obj is always a dict: call sites guard with isinstance(payload, dict)
            and recursive calls only descend into isinstance(v, dict) branches.
            """
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
            change_type = self.CHANGE_TYPE_MAP.get(deepdiff_key)
            if not change_type:
                continue
            for raw_path, payload in items.items():
                segs = re.findall(r"\['([^']+)'\]", raw_path)
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
                    # For iterable scalar items (e.g. tags), use the value itself as
                    # the final path segment — "tags.pii Removed" is clearer than
                    # "tags Removed (old_value: pii)"
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
            "changed": sum(1 for c in detail_changes if c["changeType"] == "Changed"),
        }

        # ── summary: scalar changes rolled up to parent ───────────────────────
        summary_groups: dict[tuple, dict] = {}
        for deepdiff_key, items in diff_result.items():
            change_type = self.CHANGE_TYPE_MAP.get(deepdiff_key)
            if not change_type:
                continue
            for raw_path, payload in items.items():
                segs = re.findall(r"\['([^']+)'\]", raw_path)
                is_iterable = deepdiff_key in ("iterable_item_added", "iterable_item_removed")
                # Scalar Changed: roll leaf up to parent (e.g. order_id.logicalType → order_id)
                is_scalar_change = (
                    change_type == "Changed"
                    and isinstance(payload, dict)
                    and "old_value" in payload
                    and not isinstance(payload.get("old_value"), dict)
                    and not isinstance(payload.get("new_value"), dict)
                )
                # Scalar Added/Removed leaf: also roll up to parent so that
                # adding businessName and removing description on the same field
                # both collapse to the parent (order_id) rather than appearing
                # as separate Added/Removed entries in the summary.
                is_scalar_leaf = (
                    change_type in ("Added", "Removed") and not isinstance(payload, dict) and not is_iterable
                )
                if is_iterable and isinstance(payload, str):
                    # Tag additions/removals: roll up to the parent tags path
                    # e.g. tags.pii → summary shows tags (Added/Removed)
                    display_segs = tuple(segs)
                elif (is_scalar_change or is_scalar_leaf) and len(segs) > 1:
                    display_segs = tuple(segs[:-1])
                else:
                    display_segs = tuple(segs)
                if display_segs not in summary_groups:
                    summary_groups[display_segs] = {"changeType": change_type}
                else:
                    if summary_groups[display_segs]["changeType"] != change_type:
                        summary_groups[display_segs]["changeType"] = "Changed"

        summary_changes = []
        for segs, data in sorted(summary_groups.items(), key=lambda x: ".".join(x[0])):
            summary_changes.append({"path": ".".join(segs), "changeType": data["changeType"]})

        summary_counts = {
            "added": sum(1 for c in summary_changes if c["changeType"] == "Added"),
            "removed": sum(1 for c in summary_changes if c["changeType"] == "Removed"),
            "changed": sum(1 for c in summary_changes if c["changeType"] == "Changed"),
        }

        return {
            "source_label": source_label,
            "target_label": target_label,
            "header": {
                "title": "ODCS Data Contract Diff",
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

    VALID_FORMATS = ("text", "html")

    def generate(
        self,
        v1_path: str,
        v2_path: str,
        fmt: str = "text",
        output_path: str | None = None,
    ) -> None:
        """Generate a diff report for two ODCS contract files.

        Args:
            v1_path:     path to the source (before) contract YAML
            v2_path:     path to the target (after) contract YAML
            fmt:         output format — "text" (default) or "html"
            output_path: file path to write the report to. If None (default),
                         the report is written to stdout.

        Raises:
            ValueError:  if fmt is not "text" or "html"
            FileNotFoundError: if v1_path or v2_path does not exist
        """
        import os

        if fmt not in self.VALID_FORMATS:
            raise ValueError(f"Invalid format {fmt!r}. Must be one of: {', '.join(self.VALID_FORMATS)}")

        for label, path in (("v1_path", v1_path), ("v2_path", v2_path)):
            if not os.path.exists(path):
                raise FileNotFoundError(f"{label} does not exist: {path!r}")

        from datacontract.reports.diff.html_contract_diff_renderer import HtmlContractDiffRenderer
        from datacontract.reports.diff.text_contract_diff_renderer import TextContractDiffRenderer

        contracts_diff = ContractDiff().generate(v1_path, v2_path)
        report_data = self.build_report_data(
            diff_result=contracts_diff,
            source_label=v1_path,
            target_label=v2_path,
        )

        if fmt == "html":
            content = HtmlContractDiffRenderer(report_data=report_data).render()
        else:
            content = TextContractDiffRenderer(report_data=report_data).render()

        if output_path:
            with open(output_path, "w", encoding="utf-8") as f:
                f.write(content)
        else:
            print(content)
