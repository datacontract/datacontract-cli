"""Tests for the Power BI .pbit / .bim importer."""

import io
import json
import zipfile

import pytest
import yaml

from datacontract.imports.powerbi_importer import import_powerbi_from_file

BIM_FIXTURE = "fixtures/powerbi/model.bim"
PBIT_FIXTURE = "fixtures/powerbi/Artificial Intelligence Sample.pbit"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_pbit(bim_dict: dict, encoding: str = "utf-16-le") -> bytes:
    """Create an in-memory .pbit (ZIP) containing a DataModelSchema entry."""
    raw = json.dumps(bim_dict).encode(encoding)
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("DataModelSchema", raw)
    return buf.getvalue()


def _write_pbit(tmp_path, bim_dict: dict) -> str:
    path = tmp_path / "model.pbit"
    path.write_bytes(_make_pbit(bim_dict))
    return str(path)


# ---------------------------------------------------------------------------
# BIM file import
# ---------------------------------------------------------------------------


def test_import_bim_model_name():
    result = import_powerbi_from_file(BIM_FIXTURE)
    assert result.name == "model"
    assert result.id == "model"


def test_import_bim_server():
    result = import_powerbi_from_file(BIM_FIXTURE)
    assert len(result.servers) == 1
    server = result.servers[0]
    assert server.type == "custom"
    assert server.server == "powerbi"


def test_import_bim_tables_sorted():
    result = import_powerbi_from_file(BIM_FIXTURE)
    names = [s.name for s in result.schema_]
    assert names == sorted(names, key=str.lower)


def test_import_bim_expected_tables():
    result = import_powerbi_from_file(BIM_FIXTURE)
    names = {s.name for s in result.schema_}
    # DateTableTemplate is hidden but should still be imported with hidden tag
    assert "Sales" in names
    assert "Date" in names
    assert "DateTableTemplate" in names


def test_import_bim_table_description():
    result = import_powerbi_from_file(BIM_FIXTURE)
    sales = next(s for s in result.schema_ if s.name == "Sales")
    assert sales.description == "Transactional sales data"


def test_import_bim_hidden_table_tagged():
    result = import_powerbi_from_file(BIM_FIXTURE)
    hidden = next(s for s in result.schema_ if s.name == "DateTableTemplate")
    assert hidden.tags is not None
    assert "hidden" in hidden.tags


def test_import_bim_local_data_table_excluded(tmp_path):
    """Tables whose name starts with LocalDateTable_ must be skipped entirely."""
    import json

    with open(BIM_FIXTURE, encoding="utf-8-sig") as f:
        bim_dict = json.load(f)

    bim_dict["model"]["tables"].append(
        {
            "name": "LocalDateTable_abc123",
            "columns": [{"name": "Col1", "dataType": "string", "columnType": "data"}],
            "partitions": [{"name": "p", "source": {"type": "m", "expression": ""}}],
        }
    )

    bim_path = tmp_path / "model.bim"
    bim_path.write_text(json.dumps(bim_dict), encoding="utf-8")
    result = import_powerbi_from_file(str(bim_path))

    names = {s.name for s in result.schema_}
    assert "LocalDateTable_abc123" not in names


def test_import_bim_local_data_table_relationship_excluded(tmp_path):
    """Relationships referencing a LocalDateTable_ table must be skipped."""
    import json

    with open(BIM_FIXTURE, encoding="utf-8-sig") as f:
        bim_dict = json.load(f)

    bim_dict["model"]["tables"].append(
        {
            "name": "LocalDateTable_xyz",
            "columns": [{"name": "Key", "dataType": "int64", "columnType": "data"}],
            "partitions": [{"name": "p", "source": {"type": "m", "expression": ""}}],
        }
    )
    bim_dict["model"]["relationships"].append(
        {
            "name": "Sales_LocalDateTable",
            "fromTable": "LocalDateTable_xyz",
            "fromColumn": "Key",
            "toTable": "Sales",
            "toColumn": "OrderID",
            "fromCardinality": "many",
            "toCardinality": "one",
        }
    )

    bim_path = tmp_path / "model.bim"
    bim_path.write_text(json.dumps(bim_dict), encoding="utf-8")
    result = import_powerbi_from_file(str(bim_path))

    sales = next(s for s in result.schema_ if s.name == "Sales")
    rel_sources = [r.from_ for r in (sales.relationships or [])]
    assert not any("LocalDateTable_xyz" in s for s in rel_sources)


# ---------------------------------------------------------------------------
# Columns
# ---------------------------------------------------------------------------


def test_import_bim_rowNumber_column_excluded():
    result = import_powerbi_from_file(BIM_FIXTURE)
    sales = next(s for s in result.schema_ if s.name == "Sales")
    col_names = [p.name for p in sales.properties]
    assert "RowNumber" not in col_names


def test_import_bim_column_types():
    result = import_powerbi_from_file(BIM_FIXTURE)
    sales = next(s for s in result.schema_ if s.name == "Sales")
    props = {p.name: p for p in sales.properties}

    assert props["OrderID"].logicalType == "integer"
    assert props["OrderDate"].logicalType == "timestamp"
    assert props["SalesAmount"].logicalType == "number"
    assert props["Discount"].logicalType == "number"


def test_import_bim_required_column():
    result = import_powerbi_from_file(BIM_FIXTURE)
    sales = next(s for s in result.schema_ if s.name == "Sales")
    order_id = next(p for p in sales.properties if p.name == "OrderID")
    assert order_id.required is True


def test_import_bim_nullable_column_not_required():
    result = import_powerbi_from_file(BIM_FIXTURE)
    sales = next(s for s in result.schema_ if s.name == "Sales")
    amount = next(p for p in sales.properties if p.name == "SalesAmount")
    assert amount.required is None


def test_import_bim_column_description():
    result = import_powerbi_from_file(BIM_FIXTURE)
    sales = next(s for s in result.schema_ if s.name == "Sales")
    order_id = next(p for p in sales.properties if p.name == "OrderID")
    assert order_id.description == "Unique order identifier"


def test_import_bim_hidden_column_custom_property():
    result = import_powerbi_from_file(BIM_FIXTURE)
    sales = next(s for s in result.schema_ if s.name == "Sales")
    discount = next(p for p in sales.properties if p.name == "Discount")
    cp_keys = {cp.property for cp in (discount.customProperties or [])}
    assert "isHidden" in cp_keys


# ---------------------------------------------------------------------------
# Calculated columns
# ---------------------------------------------------------------------------


def test_import_bim_calculated_column_physical_type():
    result = import_powerbi_from_file(BIM_FIXTURE)
    sales = next(s for s in result.schema_ if s.name == "Sales")
    margin = next(p for p in sales.properties if p.name == "GrossMargin")
    assert margin.physicalType == "calculated column"


def test_import_bim_calculated_column_dax_expression():
    result = import_powerbi_from_file(BIM_FIXTURE)
    sales = next(s for s in result.schema_ if s.name == "Sales")
    margin = next(p for p in sales.properties if p.name == "GrossMargin")
    assert margin.transformLogic is not None
    assert "SalesAmount" in margin.transformLogic


def test_import_bim_calculated_column_list_expression(tmp_path):
    """A calculated column whose DAX is stored as a list of strings is joined into one expression."""
    bim = {
        "model": {
            "tables": [
                {
                    "name": "T",
                    "columns": [
                        {
                            "name": "Calc",
                            "dataType": "double",
                            "columnType": "calculated",
                            "expression": ["SalesAmount", " * ", "0.1"],
                        }
                    ],
                }
            ]
        }
    }
    bim_path = tmp_path / "model.bim"
    bim_path.write_text(json.dumps(bim), encoding="utf-8")

    result = import_powerbi_from_file(str(bim_path))
    calc = result.schema_[0].properties[0]
    assert calc.transformLogic == "SalesAmount * 0.1"


# ---------------------------------------------------------------------------
# Measures
# ---------------------------------------------------------------------------


def test_import_bim_measures_present():
    result = import_powerbi_from_file(BIM_FIXTURE)
    sales = next(s for s in result.schema_ if s.name == "Sales")
    measure_names = {p.name for p in sales.properties if p.physicalType == "measure"}
    assert "Total Sales" in measure_names
    assert "YTD Sales" in measure_names
    assert "Sales MoM %" in measure_names


def test_import_bim_measure_dax_expression():
    result = import_powerbi_from_file(BIM_FIXTURE)
    sales = next(s for s in result.schema_ if s.name == "Sales")
    total_sales = next(p for p in sales.properties if p.name == "Total Sales")
    assert total_sales.transformLogic is not None
    assert total_sales.transformLogic == "SUM(Sales[SalesAmount])"


def test_import_bim_measure_description():
    result = import_powerbi_from_file(BIM_FIXTURE)
    sales = next(s for s in result.schema_ if s.name == "Sales")
    total_sales = next(p for p in sales.properties if p.name == "Total Sales")
    assert total_sales.description == "Sum of all sales amounts"


def test_import_bim_measure_display_folder():
    result = import_powerbi_from_file(BIM_FIXTURE)
    sales = next(s for s in result.schema_ if s.name == "Sales")
    ytd = next(p for p in sales.properties if p.name == "YTD Sales")
    folder_cp = next((cp for cp in (ytd.customProperties or []) if cp.property == "displayFolder"), None)
    assert folder_cp is not None
    assert folder_cp.value == "Time Intelligence"


def test_import_bim_measure_multiline_dax():
    result = import_powerbi_from_file(BIM_FIXTURE)
    sales = next(s for s in result.schema_ if s.name == "Sales")
    mom = next(p for p in sales.properties if p.name == "Sales MoM %")
    assert mom.transformLogic is not None
    assert "DATEADD" in mom.transformLogic


def test_import_bim_measure_list_expression(tmp_path):
    """A measure whose DAX is stored as a list of strings is joined with newlines."""
    bim = {
        "model": {
            "tables": [
                {
                    "name": "T",
                    "columns": [{"name": "c", "dataType": "int64", "columnType": "data"}],
                    "measures": [{"name": "M", "expression": ["VAR x = 1", "RETURN x"]}],
                }
            ]
        }
    }
    bim_path = tmp_path / "model.bim"
    bim_path.write_text(json.dumps(bim), encoding="utf-8")

    result = import_powerbi_from_file(str(bim_path))
    measure = next(p for p in result.schema_[0].properties if p.name == "M")
    assert measure.transformLogic == "VAR x = 1\nRETURN x"


def test_import_bim_measure_inferred_number_type():
    result = import_powerbi_from_file(BIM_FIXTURE)
    sales = next(s for s in result.schema_ if s.name == "Sales")
    total_sales = next(p for p in sales.properties if p.name == "Total Sales")
    assert total_sales.logicalType == "number"


def test_import_bim_hidden_measure_custom_property():
    result = import_powerbi_from_file(BIM_FIXTURE)
    sales = next(s for s in result.schema_ if s.name == "Sales")
    flag = next(p for p in sales.properties if p.name == "Is Top Customer Flag")
    cp_keys = {cp.property for cp in (flag.customProperties or [])}
    assert "isHidden" in cp_keys


# ---------------------------------------------------------------------------
# Hierarchies
# ---------------------------------------------------------------------------


def test_import_bim_hierarchy_physical_type():
    result = import_powerbi_from_file(BIM_FIXTURE)
    date_table = next(s for s in result.schema_ if s.name == "Date")
    hier = next(p for p in date_table.properties if p.name == "Calendar")
    assert hier.physicalType == "hierarchy"
    assert hier.logicalType == "object"


def test_import_bim_hierarchy_levels():
    result = import_powerbi_from_file(BIM_FIXTURE)
    date_table = next(s for s in result.schema_ if s.name == "Date")
    hier = next(p for p in date_table.properties if p.name == "Calendar")
    level_names = [lv.name for lv in (hier.properties or [])]
    assert level_names == ["Year", "Quarter", "Month", "Date"]


def test_import_bim_hierarchy_level_column_ref():
    result = import_powerbi_from_file(BIM_FIXTURE)
    date_table = next(s for s in result.schema_ if s.name == "Date")
    hier = next(p for p in date_table.properties if p.name == "Calendar")
    year_level = next(lv for lv in hier.properties if lv.name == "Year")
    col_ref_cp = next((cp for cp in (year_level.customProperties or []) if cp.property == "columnRef"), None)
    assert col_ref_cp is not None
    assert col_ref_cp.value == "Year"


def test_import_bim_hierarchy_description():
    result = import_powerbi_from_file(BIM_FIXTURE)
    date_table = next(s for s in result.schema_ if s.name == "Date")
    hier = next(p for p in date_table.properties if p.name == "Calendar")
    assert hier.description == "Standard calendar drill-down hierarchy"


# ---------------------------------------------------------------------------
# Relationships
# ---------------------------------------------------------------------------


def test_import_bim_no_relationship_on_date_table():
    result = import_powerbi_from_file(BIM_FIXTURE)
    date_table = next(s for s in result.schema_ if s.name == "Date")
    assert not date_table.relationships


# ---------------------------------------------------------------------------
# IDs
# ---------------------------------------------------------------------------


def test_import_bim_table_id():
    result = import_powerbi_from_file(BIM_FIXTURE)
    sales = next(s for s in result.schema_ if s.name == "Sales")
    assert sales.id == "Sales_id"


def test_import_bim_column_id():
    result = import_powerbi_from_file(BIM_FIXTURE)
    sales = next(s for s in result.schema_ if s.name == "Sales")
    order_id = next(p for p in sales.properties if p.name == "OrderID")
    assert order_id.id == "OrderID_id"


def test_import_bim_measure_id():
    result = import_powerbi_from_file(BIM_FIXTURE)
    sales = next(s for s in result.schema_ if s.name == "Sales")
    total_sales = next(p for p in sales.properties if p.name == "Total Sales")
    assert total_sales.id == "Total_Sales_id"


def test_import_bim_relationship_ids_use_name_convention():
    result = import_powerbi_from_file(BIM_FIXTURE)
    sales = next(s for s in result.schema_ if s.name == "Sales")
    assert sales.relationships is not None
    assert len(sales.relationships) == 1
    rel = sales.relationships[0]
    assert rel.type == "foreignKey"
    assert rel.from_ == "Sales.OrderDate"
    assert rel.to == "Date.Date"


# ---------------------------------------------------------------------------
# Physical types
# ---------------------------------------------------------------------------


def test_import_bim_table_physical_type():
    result = import_powerbi_from_file(BIM_FIXTURE)
    sales = next(s for s in result.schema_ if s.name == "Sales")
    assert sales.physicalType == "table"


def test_import_bim_calculated_table_physical_type():
    result = import_powerbi_from_file(BIM_FIXTURE)
    date_table = next(s for s in result.schema_ if s.name == "Date")
    assert date_table.physicalType == "calculated table"


# ---------------------------------------------------------------------------
# .pbit (ZIP) loading
# ---------------------------------------------------------------------------


def test_import_pbit_from_zip(tmp_path):

    result = import_powerbi_from_file(PBIT_FIXTURE)

    assert result is not None
    names = {s.name for s in result.schema_}
    assert "Accounts" in names
    assert "Campaigns" in names
    assert "Case Calendar" in names
    assert "Cases" in names
    assert "Contacts" in names
    assert "Industries" in names


def test_import_pbit_missing_data_model_schema(tmp_path):
    """A .pbit without DataModelSchema should raise a clear DataContractException."""
    from datacontract.model.exceptions import DataContractException

    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("Report/Layout", "{}")
    pbit_path = tmp_path / "no_schema.pbit"
    pbit_path.write_bytes(buf.getvalue())

    with pytest.raises(DataContractException, match="DataModelSchema"):
        import_powerbi_from_file(str(pbit_path))


def test_import_bad_extension_raises(tmp_path):
    from datacontract.model.exceptions import DataContractException

    bad_file = tmp_path / "model.csv"
    bad_file.write_text("col1,col2")

    with pytest.raises(DataContractException, match="Unsupported file extension"):
        import_powerbi_from_file(str(bad_file))


def test_import_missing_file_raises():
    from datacontract.model.exceptions import DataContractException

    with pytest.raises(DataContractException, match="File not found"):
        import_powerbi_from_file("nonexistent/path/model.bim")


# ---------------------------------------------------------------------------
# YAML round-trip
# ---------------------------------------------------------------------------


def test_import_bim_yaml_is_valid():
    result = import_powerbi_from_file(BIM_FIXTURE)
    yaml_str = result.to_yaml()
    parsed = yaml.safe_load(yaml_str)
    assert parsed["kind"] == "DataContract"
    assert parsed["apiVersion"] == "v3.1.0"
    assert any(s["name"] == "Sales" for s in parsed["schema"])
