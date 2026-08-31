import os
from pathlib import Path

from typer.testing import CliRunner

from datacontract.cli import app

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(app, ["export", "html", "./fixtures/export/datacontract.odcs.yaml"])
    assert result.exit_code == 0


def test_cli_with_output(tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "html",
            "./fixtures/export/datacontract.odcs.yaml",
            "--output",
            tmp_path / "datacontract.html",
        ],
    )
    assert result.exit_code == 0
    assert os.path.exists(tmp_path / "datacontract.html")


def test_schemas_are_rendered():
    """Regression test for #880: schemas should render in the ODCS HTML template."""
    runner = CliRunner()
    result = runner.invoke(app, ["export", "html", "./fixtures/export/datacontract.odcs.yaml"])
    assert result.exit_code == 0
    # The schema name 'orders' and a property name 'order_id' should appear in the output
    assert "orders" in result.output
    assert "order_id" in result.output


# A contract whose author-controlled fields carry XSS payloads. logicalType is
# constrained to an enum by the ODCS schema, so the payloads live in the fields
# that are not: name, description, physicalName, physicalType.
_XSS_CONTRACT = """\
apiVersion: v3.0.2
kind: DataContract
id: xss-probe
name: "Orders <script>alert('name')</script>"
version: 1.0.0
status: active
description:
  purpose: "<img src=x onerror=alert('purpose')>"
schema:
  - name: "orders</pre><script>alert('model')</script>"
    logicalType: object
    physicalName: orders
    description: "</td></script><script>alert('table')</script>"
    properties:
      - name: "order_id</pre><img src=x onerror=alert('field')>"
        logicalType: string
        physicalType: "varchar</pre><svg onload=alert('type')>"
        description: "<svg onload=alert('col')>"
"""

# Raw HTML that must never reach the output verbatim, or it executes.
_EXECUTABLE_TAGS = [
    "<script>alert",
    "<img src=x onerror=alert",
    "<svg onload=alert",
    "</pre><script",
    "</pre><img",
    "</pre><svg",
]


def _export_html(tmp_path: Path, contract_yaml: str) -> str:
    contract_file = tmp_path / "datacontract.yaml"
    contract_file.write_text(contract_yaml)
    output_file = tmp_path / "datacontract.html"
    result = CliRunner().invoke(app, ["export", "html", str(contract_file), "--output", str(output_file)])
    assert result.exit_code == 0, result.output
    return output_file.read_text()


def test_html_export_escapes_field_values(tmp_path: Path):
    """Regression: contract fields must be HTML-escaped, not rendered as live markup.

    Autoescape was silently disabled because select_autoescape got the string
    "html" (iterated per character) instead of a sequence, so every field was a
    stored-XSS sink.
    """
    html = _export_html(tmp_path, _XSS_CONTRACT)
    for tag in _EXECUTABLE_TAGS:
        assert tag not in html, f"unescaped payload in output: {tag!r}"
    # Autoescape is actually on: the payload survives as escaped text.
    assert "&lt;script&gt;alert" in html


def test_html_export_renders_partials_as_html(tmp_path: Path):
    """Partials must render as real HTML, not escaped text.

    Enabling autoescape re-escapes render_partial output unless partials are
    registered with markup=True.
    """
    html = _export_html(tmp_path, _XSS_CONTRACT)
    assert "<section" in html
    assert "&lt;section" not in html


def test_html_export_neutralizes_mermaid_injection(tmp_path: Path):
    """The Mermaid diagram is emitted `| safe`, so its tokens must be sanitized
    of characters that could break out of the <pre class="mermaid"> block."""
    html = _export_html(tmp_path, _XSS_CONTRACT)
    start = html.index('<pre class="mermaid">')
    end = html.index("</pre>", start)
    mermaid_block = html[start + len('<pre class="mermaid">') : end]
    # `<`/`>` are what let a token form `</pre>` or a fresh tag and break out of
    # the block; the `"` wrappers around entity names are fixed Mermaid syntax,
    # not user input, and are inert inside <pre>.
    for ch in "<>":
        assert ch not in mermaid_block, f"dangerous char {ch!r} reached the mermaid block"


def test_html_export_mermaid_relationship_renders(tmp_path: Path):
    """A legitimate diagram must keep its Mermaid arrow syntax unescaped."""
    contract = """\
apiVersion: v3.0.2
kind: DataContract
id: legit
name: Orders
version: 1.0.0
status: active
schema:
  - name: orders
    logicalType: object
    properties:
      - name: customer_id
        logicalType: string
        relationships:
          - to: customers.id
  - name: customers
    logicalType: object
    properties:
      - name: id
        logicalType: string
        primaryKey: true
"""
    html = _export_html(tmp_path, contract)
    diagram_start = html.index("erDiagram")
    diagram_block = html[diagram_start : html.index("</pre>", diagram_start)]
    # Arrow syntax reaches the browser literally, not HTML-escaped.
    assert "||--o{" in diagram_block
    assert "&gt;" not in diagram_block
