"""
text_report_renderer — Plain-text renderer for ODCS data contract diffs
----------------------------------------------------------------------
Produces a fixed-width terminal report from a report_data diff dict,
with a Change Summary table and an indented Change Details table.

"""

from __future__ import annotations

from datacontract.reports.common.report_helpers import LIST_CONTAINERS, _flatten_value, _infer_ancestors


class TextContractDiffRenderer:
    """
    Renders a plain-text fixed-width tabular diff report.

    Produces a header block (title, source → target, generated timestamp)
    followed by two sections from the report_data dict:
      - CHANGE SUMMARY  (Field | Change) — changes rolled up to parent level
      - CHANGE DETAILS  (Field | Change | New | Old) — every leaf expanded

    Section titles are framed by ────── separator lines for visual clarity.

    """

    def __init__(self, report_data: dict):
        self.report_data = report_data

    def _val_strs(self, c: dict) -> tuple[str, str]:
        """Return (new_str, old_str) for a detail change entry.

        When both sides are dicts, or one side is a dict and the other a
        scalar, the dict side is flattened to "key: value; ..." pairs and
        the scalar side is rendered with str().  Previously, when exactly
        one side was a dict, the scalar side was silently dropped because
        the flat-pairs branch only joined keys present in the map.
        """
        new_v = c.get("new_value")
        old_v = c.get("old_value")
        if isinstance(new_v, dict) or isinstance(old_v, dict):
            new_pairs = _flatten_value(new_v) if isinstance(new_v, dict) else []
            old_pairs = _flatten_value(old_v) if isinstance(old_v, dict) else []
            all_keys = list(dict.fromkeys([k for k, _ in new_pairs] + [k for k, _ in old_pairs]))
            new_map, old_map = dict(new_pairs), dict(old_pairs)
            # If one side was a scalar, fall back to str() so it is never
            # silently dropped from the rendered output.
            new_str = (
                "; ".join(f"{k}: {new_map[k]}" for k in all_keys if k in new_map)
                if new_pairs
                else (str(new_v) if new_v is not None else "")
            )
            old_str = (
                "; ".join(f"{k}: {old_map[k]}" for k in all_keys if k in old_map)
                if old_pairs
                else (str(old_v) if old_v is not None else "")
            )
        else:
            new_str = str(new_v) if new_v is not None else ""
            old_str = str(old_v) if old_v is not None else ""
        return new_str, old_str

    def _badges(self, counts: dict) -> str:
        parts = []
        if counts["removed"]:
            parts.append(f"[ {counts['removed']} Removed ]")
        if counts["changed"]:
            parts.append(f"[ {counts['changed']} Changed ]")
        if counts["added"]:
            parts.append(f"[ {counts['added']} Added ]")
        return "  ".join(parts)

    def _summary_table(self, changes: list) -> list[str]:
        """Two-column table: Field | Change — no values."""
        field_w = max((len(c["path"]) for c in changes), default=20) + 2
        change_w = len("Removed") + 2
        rows = []
        rows.append(f"{'Field':<{field_w}}Change")
        rows.append("-" * (field_w + change_w))
        for c in changes:
            rows.append(f"{c['path']:<{field_w}}{c['changeType']}")
        return rows

    def _detail_table(self, changes: list, val_w: int = 26, width: int = 80) -> list[str]:
        """Indented four-column table: Field | Change | New | Old."""
        explicit = {c["path"] for c in changes}
        ancestors = sorted(_infer_ancestors(explicit))

        all_entries = sorted(changes + [{"path": a, "_ancestor": True} for a in ancestors], key=lambda x: x["path"])

        # Field column width based on indented label lengths
        def _label(c):
            segs = c["path"].split(".")
            depth = len(segs) - 1
            is_list_item = len(segs) > 1 and segs[-2] in LIST_CONTAINERS
            return "  " * depth + ("- " if is_list_item else "") + segs[-1]

        field_w = max((_label(c) for c in all_entries), key=len, default="Field")
        field_w = len(field_w) + 2
        change_w = len("Removed") + 2

        rows = []
        rows.append(f"{'Field':<{field_w}}{'Change':<{change_w}}{'New':<{val_w}}Old")
        rows.append("-" * 100)

        for c in all_entries:
            label = _label(c)
            if c.get("_ancestor"):
                rows.append(label)
                continue
            change_type = c["changeType"]
            new_str, old_str = self._val_strs(c)

            # Handle wrapping for long values
            def wrap_value(val_str, max_width):
                if len(val_str) <= max_width:
                    return [val_str]
                # Split the value into multiple lines
                lines = []
                current_line = ""
                words = val_str.split()
                for word in words:
                    if len(current_line) + len(word) + 1 <= max_width:
                        if current_line:
                            current_line += " " + word
                        else:
                            current_line = word
                    else:
                        if current_line:
                            lines.append(current_line)
                        current_line = word
                if current_line:
                    lines.append(current_line)
                return lines

            new_lines = wrap_value(new_str, val_w - 2)
            old_lines = wrap_value(old_str, val_w - 2)
            max_lines = max(len(new_lines), len(old_lines))

            for i in range(max_lines):
                new_val = new_lines[i] if i < len(new_lines) else ""
                old_val = old_lines[i] if i < len(old_lines) else ""
                label_to_use = label if i == 0 else ""
                change_to_use = change_type if i == 0 else ""
                rows.append(f"{label_to_use:<{field_w}}{change_to_use:<{change_w}}{new_val:<{val_w}}{old_val}")
        return rows

    def render(self) -> str:
        report_data = self.report_data
        if not report_data["summary"]["changes"]:
            return "No changes detected."

        h = report_data["header"]
        s_counts = report_data["summary"]["counts"]
        s_chgs = report_data["summary"]["changes"]
        d_chgs = report_data["detail"]["changes"]

        s_total = s_counts["added"] + s_counts["removed"] + s_counts["changed"]

        width = 100

        lines = []

        # ── Header ──────────────────────────────────────────────────────────
        lines.append("=" * width)
        lines.append(h["title"].center(width))
        lines.append("")  # Blank line after title

        # Handle subtitle wrapping for long file paths
        def wrap_subtitle(text, max_width):
            """Wrap subtitle text to fit within max_width."""
            if len(text) <= max_width:
                return [text]

            words = text.split()
            lines = []
            current_line = ""

            for word in words:
                if len(current_line) + len(word) + 1 <= max_width:
                    if current_line:
                        current_line += " " + word
                    else:
                        current_line = word
                else:
                    if current_line:
                        lines.append(current_line)
                    current_line = word

            if current_line:
                lines.append(current_line)
            return lines

        subtitle_lines = wrap_subtitle(h["subtitle"], width - 4)  # Leave some padding
        for subtitle_line in subtitle_lines:
            lines.append(subtitle_line.ljust(width))

        lines.append("")  # Blank line before timestamp

        if h.get("generated_at"):
            lines.append(f"Generated: {h['generated_at']}".ljust(width))
        lines.append("=" * width)
        lines.append("")

        # ── Summary ─────────────────────────────────────────────────────────
        summary_title = f"  CHANGE SUMMARY  ·  {s_total} change(s)  {self._badges(s_counts)}"
        lines.append("─" * width)
        lines.append(summary_title)
        lines.append("─" * width)
        lines.append("")
        lines.extend(self._summary_table(s_chgs))
        lines.append("")

        # ── Change Details ───────────────────────────────────────────────────
        lines.append("─" * width)
        lines.append("  CHANGE DETAILS")
        lines.append("─" * width)
        lines.append("")
        lines.extend(self._detail_table(d_chgs, val_w=30, width=width))
        lines.append("")

        return "\n".join(lines)
