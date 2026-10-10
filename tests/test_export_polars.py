import ast

import pytest
from open_data_contract_standard.model import (
    CustomProperty,
    MapDefinition,
    OpenDataContractStandard,
    SchemaObject,
    SchemaProperty,
)
from typer.testing import CliRunner

from datacontract.cli import app
from datacontract.export.polars_exporter import PolarsList, PolarsStruct, PolarsType, to_polars, to_polars_type


def test_cli():
    runner = CliRunner()
    result = runner.invoke(app, ["export", "polars", "./fixtures/polars/export/datacontract.odcs.yaml"])
    assert result.exit_code == 0
    assert result.stdout == expected_str


def _contract(*schemas: SchemaObject) -> OpenDataContractStandard:
    return OpenDataContractStandard(
        apiVersion="v3.1.0", kind="DataContract", id="test", version="1.0.0", status="active", schema=list(schemas)
    )


@pytest.mark.parametrize(
    "prop, expected",
    [
        # the width a physical type names is kept
        (SchemaProperty(name="f", physicalType="int32", logicalType="integer"), PolarsType("pl.Int32")),
        (SchemaProperty(name="f", physicalType="INT64", logicalType="integer"), PolarsType("pl.Int64")),
        (SchemaProperty(name="f", physicalType="tinyint", logicalType="integer"), PolarsType("pl.Int8")),
        (SchemaProperty(name="f", physicalType="smallint", logicalType="integer"), PolarsType("pl.Int16")),
        (SchemaProperty(name="f", physicalType="bigint unsigned", logicalType="integer"), PolarsType("pl.UInt64")),
        (SchemaProperty(name="f", physicalType="uint8", logicalType="integer"), PolarsType("pl.UInt8")),
        (SchemaProperty(name="f", physicalType="float32", logicalType="number"), PolarsType("pl.Float32")),
        (SchemaProperty(name="f", physicalType="double precision", logicalType="number"), PolarsType("pl.Float64")),
        (SchemaProperty(name="f", physicalType="varchar(255)", logicalType="string"), PolarsType("pl.String")),
        (SchemaProperty(name="f", physicalType="bytea"), PolarsType("pl.Binary")),
        # int8 is 64 bits in Postgres and DuckDB but 8 in ClickHouse, so the logical type decides
        (SchemaProperty(name="f", physicalType="int8", logicalType="integer"), PolarsType("pl.Int64")),
        # an unknown physical type falls back to the logical type
        (SchemaProperty(name="f", physicalType="geography", logicalType="string"), PolarsType("pl.String")),
        # the integer and number formats of ODCS name the width when no physical type does
        (SchemaProperty(name="f", logicalType="integer", logicalTypeOptions={"format": "i8"}), PolarsType("pl.Int8")),
        (
            SchemaProperty(name="f", logicalType="integer", logicalTypeOptions={"format": "u64"}),
            PolarsType("pl.UInt64"),
        ),
        (
            SchemaProperty(name="f", logicalType="integer", logicalTypeOptions={"format": "i128"}),
            PolarsType("pl.Int128"),
        ),
        (
            SchemaProperty(name="f", logicalType="number", logicalTypeOptions={"format": "f32"}),
            PolarsType("pl.Float32"),
        ),
        (SchemaProperty(name="f", logicalType="integer"), PolarsType("pl.Int64")),
        (SchemaProperty(name="f", logicalType="number"), PolarsType("pl.Float64")),
        (SchemaProperty(name="f", logicalType="boolean"), PolarsType("pl.Boolean")),
        (SchemaProperty(name="f", logicalType="date"), PolarsType("pl.Date")),
        (SchemaProperty(name="f", logicalType="time"), PolarsType("pl.Time")),
        # decimals
        (
            SchemaProperty(name="f", physicalType="decimal(10,2)", logicalType="number"),
            PolarsType("pl.Decimal(precision=10, scale=2)"),
        ),
        (
            SchemaProperty(name="f", physicalType="NUMERIC(18)", logicalType="number"),
            PolarsType("pl.Decimal(precision=18, scale=0)"),
        ),
        (
            SchemaProperty(name="f", physicalType="NUMBER(38, 0)", logicalType="integer"),
            PolarsType("pl.Decimal(precision=38, scale=0)"),
        ),
        (SchemaProperty(name="f", physicalType="decimal", logicalType="number"), PolarsType("pl.Decimal()")),
        (
            SchemaProperty(
                name="f",
                physicalType="decimal",
                logicalType="number",
                customProperties=[
                    CustomProperty(property="precision", value="12"),
                    CustomProperty(property="scale", value="4"),
                ],
            ),
            PolarsType("pl.Decimal(precision=12, scale=4)"),
        ),
        (
            SchemaProperty(
                name="f", logicalType="number", customProperties=[CustomProperty(property="scale", value=2)]
            ),
            PolarsType("pl.Decimal(scale=2)"),
        ),
        # timestamps: the unit follows the precision, the zone the physical type or the timezone option
        (SchemaProperty(name="f", logicalType="timestamp"), PolarsType('pl.Datetime(time_unit="us")')),
        (
            SchemaProperty(name="f", logicalType="timestamp", logicalTypeOptions={"timezone": True}),
            PolarsType('pl.Datetime(time_unit="us", time_zone="UTC")'),
        ),
        (
            SchemaProperty(
                name="f",
                logicalType="timestamp",
                logicalTypeOptions={"timezone": True, "defaultTimezone": "Europe/Berlin"},
            ),
            PolarsType('pl.Datetime(time_unit="us", time_zone="Europe/Berlin")'),
        ),
        (
            SchemaProperty(name="f", physicalType="timestamp(3)", logicalType="timestamp"),
            PolarsType('pl.Datetime(time_unit="ms")'),
        ),
        (
            SchemaProperty(name="f", physicalType="TIMESTAMP(6) WITH TIME ZONE", logicalType="timestamp"),
            PolarsType('pl.Datetime(time_unit="us", time_zone="UTC")'),
        ),
        (
            SchemaProperty(
                name="f",
                physicalType="timestamp_ntz(9)",
                logicalType="timestamp",
                logicalTypeOptions={"timezone": True},
            ),
            PolarsType('pl.Datetime(time_unit="ns")'),
        ),
        # nested types
        (SchemaProperty(name="f", logicalType="array"), PolarsList(inner=PolarsType("pl.String"))),
        (
            SchemaProperty(
                name="f",
                logicalType="array",
                items=SchemaProperty(name="i", logicalType="integer", logicalTypeOptions={"format": "i16"}),
            ),
            PolarsList(inner=PolarsType("pl.Int16")),
        ),
        (SchemaProperty(name="f", logicalType="object"), PolarsStruct(fields=())),
        (
            SchemaProperty(
                name="f",
                logicalType="map",
                map=MapDefinition(
                    key=SchemaProperty(logicalType="string"), value=SchemaProperty(logicalType="boolean")
                ),
            ),
            PolarsList(
                inner=PolarsStruct(fields=(("key", PolarsType("pl.String")), ("value", PolarsType("pl.Boolean"))))
            ),
        ),
        (
            SchemaProperty(
                name="f", logicalType="vector", logicalTypeOptions={"dimensions": 4, "elementType": "float64"}
            ),
            PolarsType("pl.Array(pl.Float64, 4)"),
        ),
        (
            SchemaProperty(
                name="f", logicalType="vector", logicalTypeOptions={"dimensions": 8, "elementType": "binary"}
            ),
            PolarsType("pl.Array(pl.Boolean, 8)"),
        ),
        (
            SchemaProperty(
                name="f", logicalType="vector", logicalTypeOptions={"dimensions": 2, "elementType": "bfloat16"}
            ),
            PolarsType("pl.Array(pl.Float32, 2)"),
        ),
        (SchemaProperty(name="f", physicalType="halfvec(768)"), PolarsType("pl.Array(pl.Float16, 768)")),
        (SchemaProperty(name="f"), PolarsType("pl.Null")),
    ],
)
def test_to_polars_type(prop, expected):
    assert to_polars_type(prop) == expected


def test_a_decimal_wider_than_polars_can_hold_is_refused():
    prop = SchemaProperty(name="amount", physicalType="numeric(50,10)", logicalType="number")

    with pytest.raises(RuntimeError) as excinfo:
        to_polars_type(prop)

    assert "at most 38 digits" in str(excinfo.value) and "'amount'" in str(excinfo.value)


def test_schema_names_become_valid_unique_variables():
    names = ["line-items", "1st", "class", "pl", "line_items"]

    code = to_polars(_contract(*[SchemaObject(name=name) for name in names]))

    assert code.splitlines()[2::2] == [
        "line_items = pl.Schema({})",
        "_1st = pl.Schema({})",
        "class_ = pl.Schema({})",
        "pl_2 = pl.Schema({})",
        "line_items_2 = pl.Schema({})",
    ]


def test_field_names_are_quoted_as_python_strings():
    names = ['say "hi"', "back\\slash", "line\nbreak", "Größe"]

    code = to_polars(_contract(SchemaObject(name="t", properties=[SchemaProperty(name=n) for n in names])))

    schema = ast.parse(code).body[1].value.args[0]
    assert [ast.literal_eval(key) for key in schema.keys] == names


def test_schema_name_selects_one_schema():
    contract = _contract(SchemaObject(name="orders"), SchemaObject(name="customers"))

    assert to_polars(contract, "customers") == "import polars as pl\n\ncustomers = pl.Schema({})"

    with pytest.raises(RuntimeError) as excinfo:
        to_polars(contract, "missing")
    assert "Available schemas: ['orders', 'customers']" in str(excinfo.value)


expected_str = """import polars as pl

orders = pl.Schema(
    {
        "order_id": pl.String,
        "order_timestamp": pl.Datetime(time_unit="us", time_zone="UTC"),
        "delivery_timestamp": pl.Datetime(time_unit="ns"),
        "order_total": pl.Decimal(precision=10, scale=2),
        "quantity": pl.Int32,
        "weight_kg": pl.Float32,
        "discount_rate": pl.Float32,
        "item_count": pl.UInt16,
        "tags": pl.List(pl.String),
        "line_items": pl.List(
            pl.Struct(
                {
                    "sku": pl.String,
                    "units": pl.Int16,
                }
            )
        ),
        "address": pl.Struct(
            {
                "city": pl.String,
                "zipcode": pl.Int64,
            }
        ),
    }
)

customers = pl.Schema(
    {
        "id": pl.UInt64,
        "attributes": pl.List(
            pl.Struct(
                {
                    "key": pl.String,
                    "value": pl.Int64,
                }
            )
        ),
        "embedding": pl.Array(pl.Float32, 3),
        "signed_up_on": pl.Date,
    }
)
"""
