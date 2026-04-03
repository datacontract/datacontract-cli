"""
html_base_renderer — Shared HTML rendering utilities for ODCS reports
--------------------------------------------------------------------

This module provides common HTML rendering functions and base classes used by
ODCS report renderers. It includes CSS styling, HTML escaping, formatting
utilities, and base renderer classes.

NOTE: The functions in this module are tested indirectly through the HTML renderer tests.

"""

from __future__ import annotations

import html
from typing import Any

from datacontract.reports.common.report_helpers import LIST_CONTAINERS, _infer_ancestors  # noqa: F401 — re-exported


def _css() -> str:
    """Return the shared stylesheet for all ODCS HTML diff reports.

    Defined as a function so it can carry a docstring. Called once at
    module load time; the result is cached in _CSS for use in _render_shell().

    Covers: CSS reset, design tokens (colour, typography), header, badges,
    section titles, diff table layout and column widths, and change-type pills.
    Single source of truth — imported by both HtmlContractDiffRenderer and
    HtmlContractClassificationRenderer via HtmlContractBaseRenderer._render_shell().
    """
    return """
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&family=IBM+Plex+Sans:wght@300;400;500;600&display=swap');

*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

:root {
  --bg:        #f6f8fa;
  --surface:   #ffffff;
  --border:    #d0d7de;
  --text:      #24292f;
  --muted:     #6e7781;
  --error:     #cf222e;
  --error-bg:  #fff0ee;
  --warning:   #9a6700;
  --warning-bg:#fff8c5;
  --info:      #0969da;
  --info-bg:   #ddf4ff;
  --success:   #1a7f37;
  --success-bg:#dafbe1;
  --mono:      'IBM Plex Mono', monospace;
  --sans:      'IBM Plex Sans', sans-serif;
}

body {
  background: var(--bg);
  color: var(--text);
  font-family: var(--sans);
  font-size: 14px;
  line-height: 1.6;
  padding: 40px 24px;
  min-height: 100vh;
}

.container { max-width: 1040px; margin: 0 auto; }

/* Header */
.header {
  display: flex; align-items: flex-start;
  justify-content: space-between;
  border-bottom: 1px solid var(--border);
  padding-bottom: 24px; margin-bottom: 32px; gap: 16px;
}
.header-left h1 { font-size: 20px; font-weight: 600; letter-spacing: -0.3px; }
.header-left .subtitle { font-size: 12px; color: var(--muted); margin-top: 4px; font-family: var(--mono); }
.badges { display: flex; gap: 8px; flex-wrap: wrap; margin-top: 2px; }
.badge {
  font-size: 11px; font-family: var(--mono);
  padding: 3px 10px; border-radius: 20px; font-weight: 500; border: 1px solid;
}
.badge.error   { color: var(--error);   background: var(--error-bg);   border-color: #ffcecb; }
.badge.warning { color: var(--warning); background: var(--warning-bg); border-color: #d4a72c; }
.badge.info    { color: var(--info);    background: var(--info-bg);    border-color: #80ccff; }
.badge.success { color: var(--success); background: var(--success-bg); border-color: #aceebb; }

/* Section */
.section { margin-bottom: 32px; }
.section-title {
  font-size: 13px; font-weight: 600; letter-spacing: 0.04em;
  text-transform: uppercase; color: var(--text); margin-bottom: 12px;
}

/* Diff table */
.diff-table {
  width: 100%; border-collapse: collapse;
  font-family: var(--mono); font-size: 12px;
  background: var(--surface); border: 1px solid var(--border);
  border-radius: 8px; overflow: hidden;
}
.diff-table th {
  text-align: left; padding: 8px 14px;
  font-size: 10px; font-weight: 600; letter-spacing: 0.06em;
  text-transform: uppercase; color: #444c56;
  background: #e6eaf0; border-bottom: 2px solid #c8d0da;
}
.diff-table td { padding: 6px 14px; border-bottom: 1px solid var(--border); vertical-align: top; }
.diff-table tr:last-child td { border-bottom: none; }
/* Ultra-compact field and change columns, reduced padding for new/old */
.diff-table th:nth-child(1),
.diff-table td:nth-child(1) {
  width: 25%; /* field column - very compact */
}
.diff-table th:nth-child(2),
.diff-table td:nth-child(2) {
  width: 5%; /* change column - ultra minimal */
}
.diff-table th:nth-child(3),
.diff-table th:nth-child(4),
.diff-table td:nth-child(3),
.diff-table td:nth-child(4) {
  width: 35%; /* new and old columns - maximum space */
  padding-left: 8px;
  padding-right: 8px;
}
.diff-table .key  { color: var(--text); }
.diff-table .old  { color: var(--error); text-decoration: line-through; opacity: 0.8; }
.diff-table .new  { color: var(--success); }
/* monospace indent: each level = 2ch, dash+space = 2ch so children align exactly */
  .diff-table .path  { font-family: inherit; }

/* Pills */
.pill {
  display: inline-flex; align-items: center; gap: 4px;
  font-size: 10px; font-weight: 500; padding: 2px 8px;
  border-radius: 12px; border: 1px solid; white-space: nowrap;
}
.pill.added   { color: var(--success); background: var(--success-bg); border-color: #aceebb; }
.pill.removed { color: var(--error);   background: var(--error-bg);   border-color: #ffcecb; }
.pill.changed { color: var(--warning); background: var(--warning-bg); border-color: #d4a72c; }

"""


# Cached at module load — _render_shell() references this directly.
_CSS = _css()


# ---------------------------------------------------------------------------
# Low-level HTML helpers — module-level functions
#
# Rule: anything a subclass does NOT need to call or override lives here
# as a plain module-level function. These produce small, composable HTML
# fragments (a string, a span, a <td>) and are imported directly by renderers.
# ---------------------------------------------------------------------------

def e(s: Any) -> str:
    """HTML-escape a value."""
    return html.escape(str(s))


def format_value(val: Any) -> str:
    """Format a cell value for display in the diff table.

    dict   → key summary span:  { key1, key2, ... }
    scalar → HTML-escaped string (no truncation — let HTML wrap naturally)
    None   → empty string
    """
    if val is None:
        return ""
    if isinstance(val, dict):
        keys = list(val.keys())
        summary = f"{{ {', '.join(keys[:4])}{'...' if len(keys) > 4 else ''} }}"
        return f'<span class="obj">{e(summary)}</span>'
    return e(str(val))


def pill(change_type: str) -> str:
    """Render a coloured change-type pill span.

    Accepts 'added', 'removed', or 'changed'. Unknown types are capitalised
    and rendered with the 'changed' CSS class.
    """
    label = {"added": "Added", "removed": "Removed", "changed": "Changed"}.get(
        change_type, change_type.capitalize()
    )
    css = change_type if change_type in ("added", "removed", "changed") else "changed"
    return f'<span class="pill {css}">{label}</span>'


def path_td(key: str, depth: int, is_list_item: bool) -> str:
    """Build a depth-indented <td> for the path column.

    depth        — number of ancestor segments; drives the padding-left calc
    is_list_item — True when the immediate parent is a LIST_CONTAINER,
                   causing a "- " prefix so the item reads as a list entry
    """
    pad = f"padding-left:calc(14px + {depth * 2}ch)"
    label = f"- {e(key)}" if is_list_item else e(key)
    return f'<td class="path" style="{pad}"><span class="key">{label}</span></td>'


def _expand_dict(dot_path: str, val: object) -> list[tuple[str, Any]]:
    """Recursively expand a dict payload into (child_dot_path, value) pairs.

    The first entry is always (dot_path, None) — the parent row placeholder.
    Subsequent entries are leaf descendants with their scalar values.
    Non-dict val is treated as a leaf: returns [(dot_path, val)].

    Used by both renderers to expand whole-object Added/Removed payloads
    into individual indented child rows.
    """
    if not isinstance(val, dict):
        return [(dot_path, val)]
    rows: list[tuple[str, Any]] = [(dot_path, None)]
    for k, v in val.items():
        rows.extend(_expand_dict(f"{dot_path}.{k}", v))
    return rows


class HtmlContractBaseRenderer:
    """
    Shared fragment renderers for ODCS HTML reports.
    
    Renderers inherit from this class to reuse the header, change-summary, and HTML-shell
    fragments without duplicating markup or CSS.

    Design rule — what belongs on the class vs at module level:
        On the class  — anything a subclass needs to call or could override:
                        _render_header_html(), _render_summary_html(), _render_shell()
        Module-level  — everything else: small composable primitives (_e, _pill,
                        _path_td, _format_value, _expand_dict) that are used
                        inside the class methods and imported directly by renderers.
                        These don't need self and have no subclass-override use case.

    """

    @staticmethod
    def _render_header_html(title: str, subtitle: str, generated_at: str) -> str:
        """Render the <div class="header"> block.

        Mirrors the exact whitespace of the original HtmlContractDiffRenderer
        so the golden-file test is unaffected.
        """
        return f"""
        <div class="header">
          <div class="header-left">
            <h1>{e(title)}</h1>
            <div class="subtitle">{e(subtitle)}</div>
            <div class="subtitle" style="margin-top:4px;">Generated: {e(generated_at)}</div>
          </div>
        </div>"""

    @staticmethod
    def _render_summary_html(total: int, badges_html: str) -> str:
        """Render the Change Summary section header + badge row.

        Does not include a detail table — callers append their own content
        below the badges if needed.
        """
        return f"""
        <div class="section">
          <div class="section-title">Change Summary &nbsp;·&nbsp; {total} change(s)</div>
          {badges_html}"""

    @staticmethod
    def _render_shell(page_title: str, source_label: str, target_label: str, body: str) -> str:
        """Wrap body in a complete <!DOCTYPE html> document using _CSS."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{e(page_title)} — {e(source_label)} → {e(target_label)}</title>
<style>{_CSS}</style>
</head>
<body>
<div class="container">
  {body}
</div>
</body>
</html>"""
