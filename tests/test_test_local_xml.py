"""`datacontract test` against XML files, read through the webbed DuckDB community extension.

The contract is the one `datacontract import xsd` creates from fixtures/import/xsd/orders.xsd,
so these tests also show that an imported XML Schema is ready to test the documents it describes.
"""

from pathlib import Path

import duckdb
import pytest
import yaml
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.data_contract import DataContract

CONTRACT = "fixtures/xml/datacontract.yaml"


def contract(path: str, **schema_changes) -> str:
    data = yaml.safe_load(Path(CONTRACT).read_text())
    data["servers"][0]["path"] = path
    data["schema"][0].update(schema_changes)
    return yaml.safe_dump(data)


def results(run) -> dict:
    return {check.name: check.result.value for check in run.checks}


def test_cli():
    result = CliRunner().invoke(app, ["test", CONTRACT])

    assert result.exit_code == 0, result.output


def test_the_imported_contract_holds_for_valid_documents():
    imported = DataContract.import_from_source("xsd", "fixtures/import/xsd/orders.xsd")
    imported.servers = DataContract(data_contract_file=CONTRACT).get_data_contract().servers

    run = DataContract(data_contract=imported).test()

    assert run.result == "passed", [(c.name, c.reason) for c in run.checks if c.result != "passed"]
    names = results(run)
    # nested objects, repeated elements, attributes, and the text of an element with attributes are all checked
    for name in [
        "Check that field customer.name has no missing values",
        "Check that field line_items.line_item[].sku matches regex pattern ^([A-Z]{3}-[0-9]{4})$",
        "Check that field line_items.line_item[].price.value has a minimum of 0",
        "Check that field line_items.line_item[].price.currency has a max length of 3",
        "Check that field version has no missing values",
        "Check that field status only contains enum values ['pending', 'shipped', 'delivered']",
    ]:
        assert names[name] == "passed", name


def test_every_violation_is_found_and_nothing_else():
    run = DataContract(data_contract_str=contract("fixtures/xml/invalid/*.xml")).test()

    failed = {name for name, result in results(run).items() if result != "passed"}
    assert failed == {
        "Check that field order_id has a max length of 36",
        "Check that field order_timestamp has no missing values",
        "Check that field order_total has a minimum of 0",
        "Check that field status only contains enum values ['pending', 'shipped', 'delivered']",
        "Check that field customer.name has no missing values",
        "Check that field line_items.line_item[].sku matches regex pattern ^([A-Z]{3}-[0-9]{4})$",
        "Check that field line_items.line_item[].quantity is not equal to 1000",
        "Check that field line_items.line_item[].price.value has a minimum of 0",
        "Check that field line_items.line_item[].price.currency has a max length of 3",
        "Check that field category.name has no missing values",
        "Check that field version has no missing values",
    }
    assert run.result == "failed"


def test_a_violation_counts_the_records_that_break_it():
    run = DataContract(data_contract_str=contract("fixtures/xml/invalid/*.xml")).test()

    check = next(
        c
        for c in run.checks
        if c.name == "Check that field status only contains enum values ['pending', 'shipped', 'delivered']"
    )
    assert check.reason == "Actual invalid_count(status) was 1, expected = 0"


def test_an_absent_optional_object_does_not_make_its_required_fields_missing():
    # order-2.xml has no category, whose name is required
    run = DataContract(data_contract_str=contract("fixtures/xml/data/order-2.xml")).test()

    assert results(run)["Check that field category.name has no missing values"] == "passed"


def test_records_inside_a_wrapper_element_with_prefixed_names():
    contract_str = """
apiVersion: v3.2.0
kind: DataContract
id: batch
version: 1.0.0
status: active
servers:
  - server: local
    type: local
    path: fixtures/xml/batch/orders.xml
    format: xml
schema:
  - name: orders
    physicalName: order
    properties:
      - name: order_id
        logicalType: string
        required: true
        unique: true
      - name: order_total
        logicalType: number
        logicalTypeOptions:
          maximum: 20.5
      - name: version
        logicalType: integer
        logicalTypeOptions:
          minimum: 1
    quality:
      - type: sql
        query: SELECT COUNT(*) FROM orders
        mustBe: 3
      - type: sql
        query: SELECT SUM(order_total) FROM orders
        mustBe: 35.75
"""
    run = DataContract(data_contract_str=contract_str).test()

    assert run.result == "passed", [(c.name, c.reason) for c in run.checks if c.result != "passed"]
    assert len(run.checks) == 9


def test_a_record_element_that_is_not_in_the_documents_fails():
    run = DataContract(data_contract_str=contract("fixtures/xml/data/*.xml", physicalName="shipment")).test()

    assert run.result == "failed"
    assert results(run)["Check that field 'order_id' is present"] == "failed"


def test_a_value_of_the_wrong_type_fails_the_run(tmp_path: Path):
    document = (
        Path("fixtures/xml/data/order-2.xml").read_text().replace("<quantity>3</quantity>", "<quantity>many</quantity>")
    )
    (tmp_path / "order.xml").write_text(document)

    run = DataContract(data_contract_str=contract(str(tmp_path / "order.xml"))).test()

    assert run.result == "failed"
    # presence is read as text, so only the checks that need the value report it
    assert results(run)["Check that field 'order_id' is present"] == "passed"
    assert any("'many'" in (c.reason or "") for c in run.checks)


@pytest.mark.parametrize("unique, result", [(True, "failed"), (False, "passed")])
def test_unique_across_files(tmp_path: Path, unique, result):
    for name in ("a.xml", "b.xml"):
        (tmp_path / name).write_text(Path("fixtures/xml/data/order-1.xml").read_text())
    data = yaml.safe_load(contract(str(tmp_path / "*.xml")))
    order_id = next(p for p in data["schema"][0]["properties"] if p["name"] == "order_id")
    order_id["unique"] = unique

    run = DataContract(data_contract_str=yaml.safe_dump(data)).test()

    assert results(run).get("Check that unique field order_id has no duplicate values", "passed") == result


def test_an_element_without_its_attributes_keeps_its_text(tmp_path: Path):
    # Where one price carries no currency, DuckDB infers every price as plain text
    for name in ("order-1.xml", "order-2.xml"):
        (tmp_path / name).write_text(Path(f"fixtures/xml/data/{name}").read_text())
    without_currency = Path("fixtures/xml/data/order-2.xml").read_text().replace(' currency="GBP"', "")
    (tmp_path / "order-3.xml").write_text(without_currency.replace("C-1002", "C-1003"))

    run = DataContract(data_contract_str=contract(str(tmp_path / "*.xml"))).test()

    failed = {name for name, result in results(run).items() if result != "passed"}
    assert failed == {"Check that field line_items.line_item[].price.currency has no missing values"}


@pytest.mark.parametrize(
    "schema_changes",
    [
        {"name": 'o" AS SELECT 1; CREATE MACRO injected() AS 42; CREATE VIEW "z'},
        {"physicalName": 'order" AS SELECT 1; CREATE MACRO injected() AS 42; --'},
    ],
)
def test_names_from_the_contract_are_not_run_as_sql(schema_changes):
    con = duckdb.connect()

    DataContract(data_contract_str=contract("fixtures/xml/data/*.xml", **schema_changes), duckdb_connection=con).test()

    assert con.sql("SELECT * FROM duckdb_functions() WHERE function_name = 'injected'").fetchall() == []


def test_an_element_that_occurs_once_in_every_document_is_still_an_array(tmp_path: Path):
    # order-2.xml has a single line_item, which DuckDB infers as one object rather than a list of one
    (tmp_path / "order.xml").write_text(Path("fixtures/xml/data/order-2.xml").read_text())

    run = DataContract(data_contract_str=contract(str(tmp_path / "order.xml"))).test()

    line_item_checks = {name: result for name, result in results(run).items() if "line_item" in name}
    assert len(line_item_checks) > 10
    assert set(line_item_checks.values()) == {"passed"}, line_item_checks


def test_an_imported_pattern_matches_the_whole_value(tmp_path: Path):
    # XSD patterns are anchored; the sku ABC-0001x would pass an unanchored search for [A-Z]{3}-[0-9]{4}
    document = Path("fixtures/xml/data/order-2.xml").read_text().replace("DEF-1234", "xDEF-1234x")
    (tmp_path / "order.xml").write_text(document)

    run = DataContract(data_contract_str=contract(str(tmp_path / "order.xml"))).test()

    assert (
        results(run)["Check that field line_items.line_item[].sku matches regex pattern ^([A-Z]{3}-[0-9]{4})$"]
        == "failed"
    )
