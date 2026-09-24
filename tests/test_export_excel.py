import io
import logging
import os
import re
import tempfile
from pathlib import Path

import openpyxl
import pytest
import yaml
from open_data_contract_standard.model import OpenDataContractStandard
from typer.testing import CliRunner

import datacontract
import datacontract.model.workbook as workbook_module
from datacontract.cli import app
from datacontract.export import excel_exporter
from datacontract.export.excel_exporter import export_to_excel_bytes
from datacontract.imports import excel_importer
from datacontract.imports.excel_importer import import_excel_as_odcs

BUNDLED_TEMPLATE_DIR = Path(datacontract.__file__).parent / "templates" / "excel"


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
                "--no-inline-references",
                "./fixtures/excel/full-odcs-3.2.yaml",
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
    with open("./fixtures/excel/full-odcs-3.2.yaml", "r") as f:
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

    with open("./fixtures/excel/full-odcs-3.2.yaml", "r") as f:
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
                "--no-inline-references",
                "./fixtures/excel/full-odcs-3.2.yaml",
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
    with open("./fixtures/excel/full-odcs-3.2.yaml", "r") as f:
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

        assert yaml.safe_load(imported_odcs.to_yaml()) == yaml.safe_load(original_odcs.to_yaml()), (
            "Reimported ODCS should match original"
        )

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

    headers = [c.value for c in workbook["Support"][4]]
    first = [c.value for c in workbook["Support"][3]].index("Custom Properties")
    assert headers[first:] == ["pii", "count", "ratio", "plain"]
    assert [c.value for c in workbook["Support"][5]][first:] == [False, 42, 3.5, "hello"]

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


def test_sla_value_keeps_its_type(tmp_path):
    """A text SLA value stays text; a number stays a number"""
    odcs = _contract("""
slaProperties:
- property: deliveryTime
  value: "12:30"
- property: accountCode
  value: "01234"
- property: availability
  value: 99.9
""")
    imported, _ = _roundtrip(odcs, tmp_path)
    assert [sla.value for sla in imported.slaProperties] == ["12:30", "01234", 99.9]


def test_schema_logical_type_round_trips(tmp_path):
    """A schema object keeps its logical type, and an unset one stays unset"""
    odcs = _contract(
        "schema:\n- name: files\n  logicalType: blob\n- name: rows\n- name: table\n  logicalType: object\n"
    )
    imported, _ = _roundtrip(odcs, tmp_path)
    assert [schema.logicalType for schema in imported.schema_] == ["blob", None, "object"]


def test_schema_logical_type_a_template_cannot_hold_warns(tmp_path, caplog):
    """The v3.0 template has no cell for it, so a blob schema object is reported as dropped rather than read back as an object"""
    odcs = _contract("schema:\n- name: files\n  logicalType: blob\n")
    with caplog.at_level(logging.WARNING):
        imported, _ = _roundtrip(odcs, tmp_path, template=str(BUNDLED_TEMPLATE_DIR / "odcs-template-v3.0.xlsx"))
    assert imported.schema_[0].logicalType == "object"
    assert "schema logical types (1)" in caplog.records[0].message


def test_more_custom_properties_than_the_template_has_columns(tmp_path):
    """A property name takes the next empty column under the group header; beyond that, columns (or server rows) are added"""
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
  - property: d
    value: 4
schema:
- name: orders
  physicalType: table
  logicalType: object
  customProperties:
  - property: a
    value: 1
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
    - property: d
      value: 4
support:
- channel: slack
  customProperties:
  - property: a
    value: 1
  - property: d
    value: 4
- channel: teams
  customProperties:
  - property: d
    value: 5
  - property: e
    value: 6
""")
    imported, workbook = _roundtrip(odcs, tmp_path)
    assert imported.to_yaml() == odcs.to_yaml()
    support = workbook["Support"]
    first = [c.value for c in support[3]].index("Custom Properties")
    assert [c.value for c in support[4]][first:] == ["a", "d", "e"]
    assert [c.value for c in support[5]][first:] == [1, 4, None]
    assert [c.value for c in support[6]][first:] == [None, 5, 6]
    schema = workbook["Schema orders"]
    first = [c.value for c in schema[16]].index("Custom Properties")
    assert [c.value for c in schema[17]][first:] == ["a", "b", "c", "d"]
    servers = workbook["Servers"]
    label = next(
        r
        for r in range(1, servers.max_row + 1)
        if servers.cell(row=r, column=1).value == "Custom Properties (add as needed)"
    )
    assert [servers.cell(row=r, column=2).value for r in range(label + 1, label + 5)] == ["a", "b", "c", "d"]
    assert [servers.cell(row=r, column=3).value for r in range(label + 1, label + 5)] == [1, 2, 3, 4]
    # schema-level custom properties have no inline home
    assert [c.value for c in workbook["Custom Properties"][5]][:4] == ["Schema", "orders", "a", 1]


def test_old_template_export_warns_exactly_once(tmp_path, caplog):
    """Exporting into a pre-3.2 template drops what it cannot hold, with one aggregated warning"""
    with open("./fixtures/excel/full-odcs-3.2.yaml", "r") as f:
        odcs = OpenDataContractStandard.from_string(f.read())

    with caplog.at_level(logging.WARNING):
        imported, workbook = _roundtrip(odcs, tmp_path, template="./fixtures/excel/odcs-template-v1.xlsx")

    warnings = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert warnings[0].startswith("The v3.0.2 Excel template cannot hold the following contract features: ")
    assert "enum values (7)" in warnings[0]
    assert "Consider raising the apiVersion field of the contract" in warnings[0]
    assert "Enum" not in workbook.sheetnames
    # what the old layout can hold still round-trips
    assert imported.schema_[1].properties[0].name == "shipment_id"
    assert imported.servers[0].project == "acme-shipments"
    assert imported.servers[0].host == "warehouse.example.com"  # no per-type block: the legacy custom block
    # the legacy block's field labels are not custom properties: this template has no group header
    assert imported.servers[0].customProperties is None
    assert [p.property for p in imported.customProperties][:2] == ["owner", "retentionDays"]


def test_library_rule_follows_the_template_column(tmp_path):
    """ODCS renamed `rule` to `metric` in v3.1: each template's column maps to the field it is named after"""
    odcs = _contract("""
schema:
- name: orders
  properties:
  - name: id
    logicalType: string
    quality:
    - type: library
      rule: nullValues
      mustBe: 0
""")
    on_v1, _ = _roundtrip(odcs, tmp_path, template="./fixtures/excel/odcs-template-v1.xlsx")
    quality = on_v1.schema_[0].properties[0].quality[0]
    assert (quality.rule, quality.metric) == ("nullValues", None)  # Rule (Library) keeps the deprecated field

    on_bundled, _ = _roundtrip(odcs, tmp_path)
    quality = on_bundled.schema_[0].properties[0].quality[0]
    assert (quality.rule, quality.metric) == (None, "nullValues")  # Metric (Library) upgrades it


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
    source = "".join(Path(module.__file__).read_text() for module in (excel_exporter, excel_importer, workbook_module))
    names = set(
        re.findall(r'[(,] ?"((?:servers|schema|description|price|team|context|instructions)\.[A-Za-z.]+)"', source)
    )
    names |= set(re.findall(r'_by_name(?:_in_sheet)?\(\w+, "([A-Za-z.]+)"', source))
    names |= set(re.findall(r'(?:row_sheet|open_row_sheet)\(\w+, "[^"]+", "([A-Za-z]+)"', source))
    names |= {f"servers.{field}" for field in excel_exporter.SERVER_FIELDS} | {"servers.id"}
    names -= {"servers.custom.", "servers.postgres."}
    workbook = excel_exporter.create_workbook_from_bundled_template()
    defined = set(workbook.defined_names) | {n for sheet in workbook.worksheets for n in sheet.defined_names}
    assert names, "the regexes found nothing"
    assert names <= defined, f"unknown named ranges: {sorted(names - defined)}"


@pytest.mark.parametrize(
    "api_version, expected_sheets, missing_sheets, warns",
    [
        ("v3.0.2", [], ["Relationships", "Enums"], False),
        ("v3.0.0", [], ["Relationships", "Enums"], False),
        ("v3.1.0", ["Relationships"], ["Enums"], False),
        ("v3.2.0", ["Relationships", "Enums"], [], False),
        ("v3.3.0", ["Relationships", "Enums"], [], True),
        (None, ["Relationships", "Enums"], [], False),
    ],
)
def test_bundled_template_follows_the_api_version(api_version, expected_sheets, missing_sheets, warns, caplog):
    with caplog.at_level(logging.WARNING):
        workbook = excel_exporter.create_workbook_from_bundled_template(api_version)
    assert all(sheet in workbook.sheetnames for sheet in expected_sheets)
    assert not any(sheet in workbook.sheetnames for sheet in missing_sheets)
    assert bool([r for r in caplog.records if r.levelno == logging.WARNING]) == warns


def test_export_of_an_older_contract_uses_its_template_and_warns(tmp_path, caplog):
    """A v3.0 contract exports into the v3.0 template: what it cannot hold is dropped, with one warning"""
    with open("./fixtures/excel/full-odcs-3.2.yaml", "r") as f:
        odcs = OpenDataContractStandard.from_string(f.read())
    odcs.apiVersion = "v3.0.2"

    with caplog.at_level(logging.WARNING):
        imported, workbook = _roundtrip(odcs, tmp_path)

    assert "Enums" not in workbook.sheetnames
    warnings = [r.message for r in caplog.records if r.levelno == logging.WARNING]
    assert len(warnings) == 1
    assert warnings[0].startswith("The v3.0.2 Excel template cannot hold the following contract features: ")
    # what the v3.0 layout does hold still round-trips
    assert [s.name for s in imported.schema_] == [s.name for s in odcs.schema_]
    assert imported.slaProperties[0].property == "latency"
