import yaml
from datacontract_specification.model import DataContractSpecification
from open_data_contract_standard.model import OpenDataContractStandard
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.export.markdown_exporter import to_markdown
from datacontract.imports.dcs_importer import convert_dcs_to_odcs

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "export",
            "markdown",
            "./fixtures/markdown/export/datacontract.yaml",
        ],
    )
    assert result.exit_code == 0
    assert result.stdout.startswith("# urn:datacontract:checkout:orders-latest")


def test_to_markdown():
    dcs = DataContractSpecification.from_file("fixtures/markdown/export/datacontract.yaml")
    data_contract = convert_dcs_to_odcs(dcs)
    result = to_markdown(data_contract)

    with open("fixtures/markdown/export/expected.md", "r") as file:
        assert result == file.read()


def test_pipe_chars_escaped_in_table_cells():
    """Regression test for #832: pipe chars in extra field values should be escaped when inside table cells."""
    contract_yaml = """
id: test-pipe-escape
schema:
  - name: orders
    properties:
      - name: order_id
        logicalType: string
        config:
          mapping: "a | b | c"
"""
    contract = OpenDataContractStandard.model_validate(yaml.safe_load(contract_yaml))
    result = to_markdown(contract)

    # Find the table row for order_id
    lines = [line for line in result.split("\n") if "order_id" in line and line.startswith("|")]
    assert lines, "order_id table row not found"
    row = lines[0]
    # The row must have exactly 4 pipe chars as table delimiters (| col1 | col2 | col3 |)
    assert row.count("|") == 4, f"Expected 4 pipe delimiters in row, got {row.count('|')}: {row!r}"


def test_transform_logic_rendered_as_code_span():
    contract_yaml = """
id: test-transform-logic
schema:
  - name: orders
    properties:
      - name: status
        logicalType: string
        transformLogic: "CASE WHEN s = 'Y' THEN \\"open\\" ELSE a || `b` END"
"""
    contract = OpenDataContractStandard.model_validate(yaml.safe_load(contract_yaml))
    result = to_markdown(contract)

    row = next(line for line in result.split("\n") if line.startswith("|") and " status " in line)
    assert "**transformLogic:** `` CASE WHEN s = 'Y' THEN \"open\" ELSE a \\|\\| `b` END ``" in row
    # the pipes inside the code span must not add table delimiters (| col1 | col2 | col3 |)
    assert row.count("|") - row.count("\\|") == 4


def test_mermaid_diagram_after_servers_only_when_requested():
    contract = OpenDataContractStandard.model_validate(
        yaml.safe_load(
            """
id: test-mermaid
servers:
  - server: prod
    type: postgres
schema:
  - name: orders
    properties:
      - name: order_id
        logicalType: string
        primaryKey: true
"""
        )
    )

    assert "```mermaid" not in to_markdown(contract)

    result = to_markdown(contract, mermaid=True)
    assert "## Entity Relationship Diagram\n```mermaid\nerDiagram\n" in result
    assert result.index("## Servers") < result.index("## Entity Relationship Diagram") < result.index("## Schema")


def test_cli_mermaid_option():
    runner = CliRunner()
    result = runner.invoke(app, ["export", "markdown", "./fixtures/markdown/export/datacontract.yaml", "--mermaid"])
    assert result.exit_code == 0
    assert "```mermaid" in result.stdout


def test_team_without_name_is_left_out():
    contract = OpenDataContractStandard.model_validate(
        yaml.safe_load("""
id: orders
team:
  members:
    - username: alice
""")
    )
    assert "**team:**" not in to_markdown(contract)
