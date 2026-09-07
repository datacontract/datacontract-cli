import logging
import os
import sys

import openpyxl
import yaml
from open_data_contract_standard.model import OpenDataContractStandard
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.export.excel_exporter import export_to_excel_bytes
from datacontract.imports.excel_importer import import_excel_as_odcs, parse_port
from datacontract.model.workbook import resolve_cell_value

# logging.basicConfig(level=logging.DEBUG, force=True)


def test_cli():
    runner = CliRunner()
    result = runner.invoke(
        app,
        [
            "import",
            "excel",
            "--source",
            "./fixtures/excel/shipments-odcs.xlsx",
        ],
    )
    assert result.exit_code == 0
    assert "kind: DataContract" in result.stdout


def test_import_excel_odcs():
    """Conformance pair from the template repository: the workbook imports to exactly the expected YAML"""
    result = import_excel_as_odcs("./fixtures/excel/shipments-odcs.xlsx")
    expected_datacontract = read_file("fixtures/excel/shipments-odcs.yaml")
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected_datacontract)


def test_import_pre_3_2_workbook():
    """A workbook made with the templateVersion 1 layout (per-type server blocks, no child sheets) still imports"""
    result = import_excel_as_odcs("./fixtures/excel/shipments-odcs-template-v1.xlsx")
    expected_datacontract = read_file("fixtures/excel/shipments-odcs-template-v1.yaml")
    assert yaml.safe_load(result.to_yaml()) == yaml.safe_load(expected_datacontract)


def test_sheet_wins_over_inline_pair(tmp_path, caplog):
    """The same custom property inline and on the Custom Properties sheet: a warning, and the sheet's value is taken"""
    odcs = _contract("""
support:
- channel: slack
  customProperties:
  - property: sla
    value: 24h
""")
    path = tmp_path / "conflict.xlsx"
    path.write_bytes(export_to_excel_bytes(odcs))
    workbook = openpyxl.load_workbook(path)
    sheet = workbook["Custom Properties"]
    sheet.append(["Support", "slack", "sla", "48h"])
    workbook.save(path)

    with caplog.at_level(logging.WARNING):
        result = import_excel_as_odcs(str(path))
    assert [(p.property, p.value) for p in result.support[0].customProperties] == [("sla", "48h")]
    assert "the sheet wins" in caplog.text


def test_unresolvable_element_reference_is_dropped(tmp_path, caplog):
    path = tmp_path / "dangling.xlsx"
    path.write_bytes(export_to_excel_bytes(_contract("support:\n- channel: slack\n")))
    workbook = openpyxl.load_workbook(path)
    workbook["Custom Properties"].append(["Support", "teams", "sla", "48h"])
    workbook.save(path)

    with caplog.at_level(logging.WARNING):
        result = import_excel_as_odcs(str(path))
    assert result.support[0].customProperties is None
    assert "references Support 'teams', which does not exist" in caplog.text


def test_resolve_cell_value():
    assert resolve_cell_value("true") is True
    assert resolve_cell_value("007") == 7
    assert resolve_cell_value("3.10") == 3.1
    assert resolve_cell_value(42) == 42
    assert resolve_cell_value("hello") == "hello"
    assert resolve_cell_value("true", "Text") == "true"
    assert resolve_cell_value("007", "Text") == "007"
    assert resolve_cell_value('["a", 1]', "JSON") == ["a", 1]
    assert resolve_cell_value('{"a": 1}', "JSON") == {"a": 1}
    assert resolve_cell_value("") is None


def _contract(body: str):
    return OpenDataContractStandard.from_string(
        "apiVersion: v3.2.0\nkind: DataContract\nid: c\nname: c\nversion: 1.0.0\nstatus: draft\n" + body
    )


def read_file(file):
    if not os.path.exists(file):
        print(f"The file '{file}' does not exist.")
        sys.exit(1)
    with open(file, "r") as file:
        file_content = file.read()
    return file_content


def test_parse_port_keeps_variable_references():
    assert parse_port(5432) == 5432
    assert parse_port(5432.0) == 5432
    assert parse_port(" 5432 ") == 5432
    assert parse_port("${DB_PORT:-5432}") == "${DB_PORT:-5432}"
    assert parse_port("") is None
    assert parse_port(None) is None
