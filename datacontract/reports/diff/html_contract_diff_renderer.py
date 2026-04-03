"""
html_report_renderer — HTML renderer for ODCS data contract diffs
-----------------------------------------------------------------
Produces a self-contained HTML diff report from a report_data diff dict,
including a Change Summary section and a Change Details table with
depth-based indentation.

"""

from __future__ import annotations

from datacontract.reports.common.html_base_renderer import (
    _CSS,  # noqa: F401 — re-exported for any callers that import it directly
    HtmlContractBaseRenderer,
    _infer_ancestors,
    e,
    format_value,
    path_td,
    pill,
)
from datacontract.reports.common.report_helpers import LIST_CONTAINERS

# Re-export the primitives that tests import directly from this module.
# Moving them to html_base_renderer is an internal refactor; the public
# import surface of html_report_renderer is unchanged.
__all__ = [
    "HtmlContractDiffRenderer",
    "e",
    "format_value", 
    "path_td",
    "pill",
    "_render_detail_rows",
]


def _render_detail_rows(changes: list) -> list[str]:
    """Build all <tr> rows for the Change Details table.

    Ancestor spacer rows are inferred from the change paths so that
    the table hierarchy is visible even when only a leaf field changed.
    """
    explicit = {c["path"] for c in changes}
    ancestors: list[str] = sorted(_infer_ancestors(explicit))

    all_entries = sorted(
        changes + [{"path": a, "_ancestor": True} for a in ancestors],
        key=lambda x: x["path"],
    )

    rows = []
    for c in all_entries:
        segs = c["path"].split(".")
        key = segs[-1]
        depth = len(segs) - 1
        is_list_item = len(segs) > 1 and segs[-2] in LIST_CONTAINERS
        td = path_td(key, depth, is_list_item)

        if c.get("_ancestor"):
            rows.append(f"<tr>{td}<td></td><td></td><td></td></tr>")
            continue

        change_type = c["changeType"].lower()
        pill_html = pill(change_type)
        old_v = c.get("old_value")
        new_v = c.get("new_value")

        if old_v is None and new_v is None:
            rows.append(f"<tr>{td}<td>{pill_html}</td><td></td><td></td></tr>")
        else:
            old_html = format_value(old_v) if old_v is not None else ""
            new_html = format_value(new_v) if new_v is not None else ""
            rows.append(
                f'<tr>{td}<td>{pill_html}</td><td class="new">{new_html}</td><td class="old">{old_html}</td></tr>'
            )

    return rows


class HtmlContractDiffRenderer(HtmlContractBaseRenderer):
    """
    Renders a self-contained HTML diff report from a report_data diff dict.

    Produces a header (title, source → target, generated timestamp), a
    Change Summary section with badge counts, and a Change Details table
    with depth-based indentation and colour-coded change-type pills.

    Shared CSS, helper functions, and base fragment renderers are inherited
    from HtmlContractBaseRenderer (html_base_renderer.py).

    """

    def __init__(self, report_data: dict):
        self.report_data = report_data

    # ---- header ----

    def _render_header(self, report_data: dict) -> str:
        h = report_data["header"]
        return self._render_header_html(
            title=h["title"],
            subtitle=h["subtitle"],
            generated_at=h.get("generated_at", ""),
        )

    # ---- change summary section ----

    def _render_summary_section(self, report_data: dict) -> str:
        counts = report_data["summary"]["counts"]
        changes = report_data["summary"]["changes"]

        badges = []
        if counts["removed"]:
            badges.append(f'<span class="badge error">{counts["removed"]} Removed</span>')
        if counts["changed"]:
            badges.append(f'<span class="badge warning">{counts["changed"]} Changed</span>')
        if counts["added"]:
            badges.append(f'<span class="badge success">{counts["added"]} Added</span>')
        badges_html = f'<div class="badges" style="margin:16px 0;">{"".join(badges)}</div>'

        rows = []
        for ch in changes:
            pill_html = pill(ch["changeType"].lower())
            rows.append(f'<tr><td class="path">{e(ch["path"])}</td><td>{pill_html}</td></tr>')

        total = counts["added"] + counts["removed"] + counts["changed"]
        summary_header = self._render_summary_html(total, badges_html)
        return f"""{summary_header}
          <table class="diff-table">
            <thead><tr><th>field</th><th>change</th></tr></thead>
            <tbody>{"".join(rows)}</tbody>
          </table>
        </div>"""

    def _render_diff_table(self, report_data: dict) -> str:
        changes = report_data["detail"]["changes"]
        rows = _render_detail_rows(changes)

        return f"""
        <div class="section">
          <div class="section-title">Change Details</div>
          <table class="diff-table">
            <thead>
              <tr><th>field</th><th>change</th><th>new</th><th>old</th></tr>
            </thead>
            <tbody>{"".join(rows)}</tbody>
          </table>
        </div>"""

    def render(self) -> str:
        report_data = self.report_data
        body = "".join([
            self._render_header(report_data),
            "\n  ",
            self._render_summary_section(report_data),
            "\n  ",
            self._render_diff_table(report_data),
        ])
        return self._render_shell(
            page_title="ODCS Diff",
            source_label=report_data["source_label"],
            target_label=report_data["target_label"],
            body=body,
        )
