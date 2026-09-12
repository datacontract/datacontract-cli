from open_data_contract_standard.model import (
    OpenDataContractStandard,
    SchemaObject,
    SchemaProperty,
    Server,
)

from datacontract.engines.checks.check_spec import MetricType
from datacontract.engines.checks.create_checks import create_checks


def _contract(prop: SchemaProperty, server_type: str, fmt: str | None = None):
    schema = SchemaObject(name="USERS", physicalType="table", properties=[prop])
    dc = OpenDataContractStandard(version="1", kind="DataContract", apiVersion="v3.1.0", id="x", schema=[schema])
    server = Server(server="s", type=server_type, format=fmt)
    return create_checks(dc, server)


def _type_check(checks):
    return next(
        (c for c in checks if c.metric in (MetricType.FIELD_TYPE, MetricType.FIELD_PHYSICAL_TYPE)),
        None,
    )


def test_physicaltype_preferred_on_database_backend():
    prop = SchemaProperty(name="user_id", physicalType="uniqueidentifier", logicalType="string")
    check = _type_check(_contract(prop, "sqlserver"))
    assert check.metric == MetricType.FIELD_PHYSICAL_TYPE
    assert check.expected_physical_type == "uniqueidentifier"
    # logicalType is carried for the fallback path.
    assert check.expected_schema_property is not None


def test_logicaltype_used_when_no_physicaltype():
    prop = SchemaProperty(name="user_name", logicalType="string")
    check = _type_check(_contract(prop, "sqlserver"))
    assert check.metric == MetricType.FIELD_TYPE


def test_physicaltype_not_checked_on_file_backend():
    # File sources have no meaningful native platform type, so a declared
    # physicalType falls through to the logicalType category check.
    prop = SchemaProperty(name="user_id", physicalType="uniqueidentifier", logicalType="string")
    check = _type_check(_contract(prop, "local", fmt="parquet"))
    assert check.metric == MetricType.FIELD_TYPE
