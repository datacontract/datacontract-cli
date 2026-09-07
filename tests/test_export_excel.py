import io
import logging
import os
import re
import tempfile
from pathlib import Path

import openpyxl
from open_data_contract_standard.model import OpenDataContractStandard
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.export import excel_exporter
from datacontract.export.excel_exporter import export_to_excel_bytes
from datacontract.imports import excel_importer
from datacontract.imports.excel_importer import import_excel_as_odcs


def test_cli_export_excel():
    """Test Excel export via CLI"""
    runner = CliRunner()

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_file:
        tmp_path = tmp_file.name

    try:
        result = runner.invoke(
            app,
            [
                "export",
                "excel",
                "./fixtures/excel/shipments-odcs.yaml",
                "--output",
                tmp_path,
            ],
        )
        assert result.exit_code == 0
        assert os.path.exists(tmp_path)

        # Verify the file is a valid Excel file
        workbook = openpyxl.load_workbook(tmp_path)
        assert "Fundamentals" in workbook.sheetnames
        assert "Quality" in workbook.sheetnames
        assert "Schema shipments" in workbook.sheetnames
        workbook.close()

    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def test_export_excel_odcs():
    """Test Excel export from ODCS object"""
    # Load the test fixture
    with open("./fixtures/excel/shipments-odcs.yaml", "r") as f:
        odcs = OpenDataContractStandard.from_string(f.read())

    # Export to Excel
    excel_bytes = export_to_excel_bytes(odcs)

    # Verify it's valid Excel data
    assert len(excel_bytes) > 0

    # Load the Excel to verify structure
    workbook = openpyxl.load_workbook(io.BytesIO(excel_bytes))

    # Check required sheets exist
    expected_sheets = [
        "Fundamentals",
        "Quality",
        "Schema shipments",
        "Support",
        "Team",
        "Roles",
        "SLA",
        "Servers",
        "Custom Properties",
    ]

    for sheet_name in expected_sheets:
        assert sheet_name in workbook.sheetnames, f"Missing sheet: {sheet_name}"

    workbook.close()


def test_export_excel_uses_bundled_template(monkeypatch):
    """Export works offline: the default template ships with the CLI, it is not downloaded"""

    def fail(*args, **kwargs):
        raise AssertionError("Excel export must not download the template")

    monkeypatch.setattr(excel_exporter.requests, "get", fail)

    with open("./fixtures/excel/shipments-odcs.yaml", "r") as f:
        odcs = OpenDataContractStandard.from_string(f.read())

    excel_bytes = export_to_excel_bytes(odcs)

    workbook = openpyxl.load_workbook(io.BytesIO(excel_bytes))
    assert "Fundamentals" in workbook.sheetnames
    assert "Schema shipments" in workbook.sheetnames
    workbook.close()


def test_cli_export_excel_with_custom_template():
    """Test Excel export via CLI with a custom template"""
    runner = CliRunner()

    # Build a custom template: the bundled one plus a marker sheet
    template = excel_exporter.create_workbook_from_bundled_template()
    template.create_sheet("Custom Marker")
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as template_file:
        template_path = template_file.name
    template.save(template_path)
    template.close()

    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_file:
        tmp_path = tmp_file.name

    try:
        result = runner.invoke(
            app,
            [
                "export",
                "excel",
                "./fixtures/excel/shipments-odcs.yaml",
                "--template",
                template_path,
                "--output",
                tmp_path,
            ],
        )
        assert result.exit_code == 0

        workbook = openpyxl.load_workbook(tmp_path)
        assert "Custom Marker" in workbook.sheetnames
        assert "Schema shipments" in workbook.sheetnames
        workbook.close()

    finally:
        for path in (template_path, tmp_path):
            if os.path.exists(path):
                os.unlink(path)


def test_excel_roundtrip():
    """Test that export then import produces equivalent data"""
    # Load original ODCS
    with open("./fixtures/excel/shipments-odcs.yaml", "r") as f:
        original_odcs = OpenDataContractStandard.from_string(f.read())

    # Export to Excel bytes
    excel_bytes = export_to_excel_bytes(original_odcs)

    # Save to temporary file for import
    with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp_file:
        tmp_file.write(excel_bytes)
        tmp_path = tmp_file.name

    try:
        # Import back from Excel
        imported_odcs = import_excel_as_odcs(tmp_path)

        assert imported_odcs.to_yaml() == original_odcs.to_yaml(), "Reimported ODCS should match original"

    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def _contract(body: str) -> OpenDataContractStandard:
    return OpenDataContractStandard.from_string(
        "apiVersion: v3.2.0\nkind: DataContract\nid: c\nname: c\nversion: 1.0.0\nstatus: draft\n" + body
    )


def _roundtrip(odcs: OpenDataContractStandard, tmp_path, template=None):
    path = tmp_path / "export.xlsx"
    path.write_bytes(export_to_excel_bytes(odcs, template))
    return import_excel_as_odcs(str(path)), openpyxl.load_workbook(path)


def test_inline_or_sheet_by_round_trip_of_the_value(tmp_path):
    """A custom property is inline only when its value survives a plain cell; otherwise it goes to the sheet, typed"""
    odcs = _contract("""
support:
- channel: slack
  customProperties:
  - property: pii
    value: false
  - property: count
    value: 42
  - property: ratio
    value: 3.5
  - property: plain
    value: hello
  - property: empty
    value: null
  - property: flag
    value: 'true'
  - property: zip
    value: '007'
  - property: version
    value: '3.10'
  - property: whole
    value: 1.0
  - property: regions
    value: [eu, us]
  - property: nested
    value: {a: 1}
  - property: described
    value: x
    description: with a description
""")
    imported, workbook = _roundtrip(odcs, tmp_path)

    support_row = [c.value for c in workbook["Support"][5]]
    inline = [support_row[i] for i, h in enumerate([c.value for c in workbook["Support"][4]]) if h == "Custom Property"]
    assert inline == ["pii", "count", "ratio", "plain", "empty"]

    sheet_rows = [
        [c.value for c in row][:5] for row in workbook["Custom Properties"].iter_rows(min_row=5) if row[2].value
    ]
    assert sheet_rows == [
        ["Support", "slack", "flag", "true", "Text"],
        ["Support", "slack", "zip", "007", "Text"],
        ["Support", "slack", "version", "3.10", "Text"],
        ["Support", "slack", "whole", "1.0", "JSON"],
        ["Support", "slack", "regions", '["eu", "us"]', "JSON"],
        ["Support", "slack", "nested", '{"a": 1}', "JSON"],
        ["Support", "slack", "described", "x", None],
    ]
    assert imported.support[0].model_dump() == odcs.support[0].model_dump()


def test_more_inline_pairs_than_the_template_has(tmp_path):
    """Export adds pair columns (row sheets), pair rows (schema block, servers) as the contract needs"""
    odcs = _contract("""
servers:
- server: prod
  type: postgresql
  host: db
  customProperties:
  - property: a
    value: 1
  - property: b
    value: 2
  - property: c
    value: 3
schema:
- name: orders
  physicalType: table
  logicalType: object
  customProperties:
  - property: a
    value: 1
  - property: b
    value: 2
  properties:
  - name: id
    logicalType: string
    customProperties:
    - property: a
      value: 1
    - property: b
      value: 2
    - property: c
      value: 3
support:
- channel: slack
  customProperties:
  - property: a
    value: 1
  - property: b
    value: 2
""")
    imported, workbook = _roundtrip(odcs, tmp_path)
    assert imported.to_yaml() == odcs.to_yaml()
    assert [c.value for c in workbook["Support"][4]].count("Custom Property") == 2
    assert [c.value for c in workbook["Schema orders"]["A"]].count("Custom Property") == 2
    assert workbook["Schema orders"].defined_names["schema.properties"].attr_text == "'Schema orders'!$A$20:$AZ$983"
    assert [c.value for c in workbook["Servers"]["B"]].count("Custom Property") == 3
    assert workbook["Custom Properties"]["C6"].value is None


def test_old_template_export_warns_exactly_once(tmp_path, caplog):
    """Exporting into a templateVersion 1 template drops what it cannot hold, with one aggregated warning"""
    with open("./fixtures/excel/shipments-odcs.yaml", "r") as f:
        odcs = OpenDataContractStandard.from_string(f.read())

    with caplog.at_level(logging.WARNING):
        imported, workbook = _roundtrip(odcs, tmp_path, template="./fixtures/excel/odcs-template-v1.xlsx")

    warnings = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert warnings[0].startswith("Custom template (templateVersion 1) cannot hold: ")
    assert "enum values (5)" in warnings[0]
    assert "Upgrade to templateVersion 2 to keep them." in warnings[0]
    assert "Enum" not in workbook.sheetnames
    # what the old layout can hold still round-trips
    assert imported.schema_[0].properties[0].name == "shipment_id"
    assert imported.servers[0].project == "acme_shipments_prod"
    assert imported.servers[1].host == "trino.example.com"  # no per-type block: the legacy custom block
    assert [p.property for p in imported.customProperties][:2] == ["owner", "additionalField"]


def test_unreferenceable_element_warns_and_drops_its_rich_custom_properties(tmp_path, caplog):
    odcs = _contract("""
schema:
- name: orders
  quality:
  - type: sql
    query: SELECT 1
    customProperties:
    - property: owner
      value: qa
      description: rich, so it needs the sheet
""")
    with caplog.at_level(logging.WARNING):
        imported, workbook = _roundtrip(odcs, tmp_path)
    assert [r.message for r in caplog.records] == [
        "Cannot reference quality rule of schema orders in the workbook: it has no id; "
        "its custom properties were dropped. Give it an id."
    ]
    assert imported.schema_[0].quality[0].customProperties is None


def test_code_only_uses_named_ranges_the_bundled_template_has():
    """Every named range the exporter and importer look up by string exists in the bundled template"""
    source = "".join(
        Path(module.__file__).read_text()
        for module in (excel_exporter, excel_importer, __import__("datacontract.model.workbook").model.workbook)
    )
    names = set(
        re.findall(r'[(,] ?"((?:servers|schema|description|price|team|context|instructions)\.[A-Za-z.]+)"', source)
    )
    names |= set(re.findall(r'_by_name(?:_in_sheet)?\(\w+, "([A-Za-z.]+)"', source))
    names |= set(re.findall(r'(?:row_sheet|open_row_sheet)\(\w+, "[^"]+", "([A-Za-z]+)"', source))
    names |= {f"servers.{field}" for field in excel_exporter.SERVER_FIELDS} | {"servers.id", "templateVersion"}
    names -= {"servers.custom.", "servers.postgres."}
    workbook = excel_exporter.create_workbook_from_bundled_template()
    defined = set(workbook.defined_names) | {n for sheet in workbook.worksheets for n in sheet.defined_names}
    assert names, "the regexes found nothing"
    assert names <= defined, f"unknown named ranges: {sorted(names - defined)}"
