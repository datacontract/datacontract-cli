import ibis.expr.datatypes as dt
from open_data_contract_standard.model import SchemaProperty

from datacontract.engines.checks.type_normalize import schema_property_matches
from datacontract.engines.ibis.dtype_category import (
    ibis_dtype_category,
    ibis_dtype_to_schema_property,
)


def test_uuid_maps_to_string_category():
    # SQL Server `uniqueidentifier` columns surface as ibis UUID; they must be
    # treated as strings, not "other" (regression for #1354).
    assert ibis_dtype_category(dt.UUID()) == "string"


def test_uuid_dtype_to_schema_property_is_string():
    prop = ibis_dtype_to_schema_property(dt.UUID())
    assert prop is not None
    assert prop.logicalType == "string"


def test_uuid_column_matches_string_contract_property():
    # A property declared as logicalType string (physicalType uniqueidentifier)
    # must match a column ibis reports as UUID.
    expected = SchemaProperty(logicalType="string", physicalType="uniqueidentifier")
    actual = ibis_dtype_to_schema_property(dt.UUID())
    assert schema_property_matches(expected, actual)
