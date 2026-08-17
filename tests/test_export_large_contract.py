"""Every exporter runs against a contract that uses the whole ODCS type system.

fixtures/export/datacontract.large.odcs.yaml carries all seven logical types,
nested objects two levels deep, arrays of a scalar and of an object, and two
schemas. Exporters branch on logical type and recurse into properties/items, so
those paths stay unreachable with a contract of flat string and integer columns.

This is deliberately a breadth check rather than an assertion on any one
exporter's output: the per-format tests own their formatting, while this one
catches an exporter that falls over on a type it has never been handed.
"""

import pytest

from datacontract.data_contract import DataContract
from datacontract.export.exporter import ExportFormat

FIXTURE = "fixtures/export/datacontract.large.odcs.yaml"

# Exporters that need more than a contract to run at all, and so cannot say
# anything about type handling here.
NEEDS_MORE_THAN_A_CONTRACT = {
    "custom": "requires a --template argument",
    "bigquery": "requires a bigquery server in the contract",
    "dqx": "requires quality definitions of its own shape (fails on the small fixture too)",
}

FORMATS = [
    pytest.param(
        fmt,
        marks=pytest.mark.xfail(
            strict=True,
            reason="the sqlalchemy exporter rejects the `object` logical type: RuntimeError: Unsupported field type object",
        ),
    )
    if fmt == "sqlalchemy"
    else fmt
    for fmt in (f.value for f in ExportFormat)
    if fmt not in NEEDS_MORE_THAN_A_CONTRACT
]


@pytest.mark.parametrize("export_format", FORMATS)
def test_every_exporter_handles_the_full_type_system(export_format):
    data_contract = DataContract(data_contract_file=FIXTURE)

    try:
        result = data_contract.export(export_format=export_format)
    except Exception as e:
        # Several exporters emit one schema at a time and say so; that is a
        # legitimate answer to a two-schema contract, so retry as they ask.
        # (iceberg raises a bare Exception rather than RuntimeError.)
        if "schema-name" not in str(e) and "one model at a time" not in str(e):
            raise
        result = data_contract.export(export_format=export_format, schema_name="orders")

    assert result, f"{export_format} produced no output"
