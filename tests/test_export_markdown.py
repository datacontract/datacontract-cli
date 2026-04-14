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
            "./fixtures/markdown/export/datacontract.yaml",
            "--format",
            "markdown",
        ],
    )
    assert result.exit_code == 0
    assert result.output.startswith("# urn:datacontract:checkout:orders-latest")


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
