import logging

from open_data_contract_standard.model import OpenDataContractStandard

from datacontract.data_contract import DataContract
from datacontract.imports.odcs_helper import create_odcs, create_property, create_schema_object, report_unmapped_types


def _odcs(*schema_objects) -> OpenDataContractStandard:
    odcs = create_odcs()
    odcs.schema_ = list(schema_objects)
    return odcs


def test_lists_every_unmapped_property_and_fills_the_fallback(caplog):
    odcs = _odcs(
        create_schema_object(
            name="orders",
            properties=[
                create_property(name="id", logical_type="integer", physical_type="INTEGER"),
                create_property(name="amount", logical_type=None, physical_type="DECIMAL(10,2)"),
                create_property(
                    name="address",
                    logical_type="object",
                    physical_type="STRUCT",
                    properties=[create_property(name="geo", logical_type=None, physical_type="GEOMETRY")],
                ),
            ],
        )
    )

    with caplog.at_level(logging.WARNING):
        report_unmapped_types(odcs, fallback="string")

    assert caplog.messages == [
        "2 columns have no defined mapping to logicalType and will be imported as string:\n"
        "amount (DECIMAL(10,2)), address.geo (GEOMETRY)\n"
        "You may propose an updated mapping on GitHub: https://github.com/datacontract/datacontract-cli/issues"
    ]
    properties = {p.name: p for p in odcs.schema_[0].properties}
    assert properties["amount"].logicalType == "string"
    assert properties["address"].properties[0].logicalType == "string"
    assert properties["id"].logicalType == "integer"


def test_without_fallback_the_property_stays_untyped_and_names_are_qualified_per_schema(caplog):
    odcs = _odcs(
        create_schema_object(name="a", properties=[create_property(name="x", logical_type=None, physical_type="T1")]),
        create_schema_object(name="b", properties=[create_property(name="y", logical_type="string")]),
    )

    with caplog.at_level(logging.WARNING):
        report_unmapped_types(odcs)

    assert caplog.messages[0].startswith(
        "1 column has no defined mapping to logicalType and will be imported without a logicalType:\na.x (T1)\n"
    )
    assert odcs.schema_[0].properties[0].logicalType is None


def test_caps_the_listing_at_five(caplog):
    odcs = _odcs(
        create_schema_object(
            name="t",
            properties=[create_property(name=f"c{i}", logical_type=None, physical_type="T") for i in range(7)],
        )
    )

    with caplog.at_level(logging.WARNING):
        report_unmapped_types(odcs, fallback="string")

    assert "c0 (T), c1 (T), c2 (T), c3 (T), c4 (T) and 2 others.\n" in caplog.messages[0]


def test_silent_when_everything_is_mapped(caplog):
    odcs = _odcs(create_schema_object(name="t", properties=[create_property(name="c", logical_type="string")]))

    with caplog.at_level(logging.WARNING):
        report_unmapped_types(odcs, fallback="string")

    assert caplog.messages == []


def test_sql_import_warns_and_leaves_the_property_untyped(caplog, tmp_path):
    ddl = tmp_path / "t.sql"
    ddl.write_text("CREATE TABLE t (shape GEOMETRY, id INT);")

    with caplog.at_level(logging.WARNING):
        result = DataContract.import_from_source("sql", str(ddl), dialect="postgres")

    assert "will be imported without a logicalType:\nshape (GEOMETRY)\n" in caplog.text
    properties = {p.name: p for p in result.schema_[0].properties}
    assert properties["shape"].logicalType is None
    assert properties["shape"].physicalType == "GEOMETRY"
