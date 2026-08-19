import os
from pathlib import Path

from typer.testing import CliRunner

from datacontract.cli import app


def test_cli():
    runner = CliRunner()
    result = runner.invoke(app, ["export", "mermaid", "./fixtures/export/datacontract.odcs.yaml"])
    assert result.exit_code == 0


def test_cli_with_output(tmp_path: Path):
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "mermaid",
            "./fixtures/export/datacontract.odcs.yaml",
            "--output",
            tmp_path / "datacontract.mermaid",
        ],
    )
    assert result.exit_code == 0
    assert os.path.exists(tmp_path / "datacontract.mermaid")


def test_mermaid_structure(tmp_path: Path):
    datacontract_file = "fixtures/export/datacontract.odcs.yaml"
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "mermaid",
            datacontract_file,
            "--output",
            tmp_path / "datacontract.mermaid",
        ],
    )
    assert result.exit_code == 0

    with open(tmp_path / "datacontract.mermaid") as file:
        content = file.read()

    # Check structure
    assert "erDiagram" in content
    assert "orders" in content
    assert "order_id" in content
    assert "order_total" in content
    assert "order_status" in content


def test_mermaid_sanitizes_html_dangerous_characters():
    """to_mermaid output is embedded `| safe` in the HTML export, so no token
    (model name, field name, or field type) may carry `<`/`>` that could break
    out of the <pre class="mermaid"> block."""
    from open_data_contract_standard.model import OpenDataContractStandard, SchemaObject, SchemaProperty

    from datacontract.export.mermaid_exporter import to_mermaid

    contract = OpenDataContractStandard(
        apiVersion="v3.0.2",
        kind="DataContract",
        id="x",
        version="1.0.0",
        status="active",
        schema=[
            SchemaObject(
                name="orders</pre><script>alert(1)</script>",
                logicalType="object",
                properties=[
                    SchemaProperty(
                        name="id</pre><img src=x onerror=alert(1)>",
                        logicalType="string",
                        physicalType="varchar<svg onload=alert(1)>",
                    )
                ],
            )
        ],
    )

    diagram = to_mermaid(contract)

    assert diagram is not None
    assert "<" not in diagram
    assert ">" not in diagram
