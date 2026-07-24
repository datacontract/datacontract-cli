from open_data_contract_standard.model import (
    OpenDataContractStandard,
    SchemaObject,
    SchemaProperty,
    Server,
)

from datacontract.engines.checks.check_spec import MetricType
from datacontract.engines.checks.create_checks import create_checks


def _checks(*props: SchemaProperty):
    schema = SchemaObject(name="ORDERS", physicalType="table", properties=list(props))
    dc = OpenDataContractStandard(version="1", kind="DataContract", apiVersion="v3.1.0", id="x", schema=[schema])
    return create_checks(dc, Server(server="s", type="postgres"))


def _of_type(checks, check_type):
    return [c for c in checks if c.type == check_type]


def test_primary_key_generates_not_null_and_uniqueness():
    checks = _checks(SchemaProperty(name="order_id", primaryKey=True))

    required = _of_type(checks, "field_primary_key_required")
    unique = _of_type(checks, "field_primary_key_unique")

    assert len(required) == 1
    assert required[0].field == "order_id"
    assert required[0].metric == MetricType.MISSING_COUNT

    assert len(unique) == 1
    assert unique[0].field == "order_id"
    assert unique[0].metric == MetricType.DUPLICATE_COUNT
    assert unique[0].columns == ["order_id"]


def test_primary_key_does_not_duplicate_required_and_unique_checks():
    """A property may declare all three; it should not produce two of each check."""
    checks = _checks(SchemaProperty(name="order_id", primaryKey=True, required=True, unique=True))

    assert len(_of_type(checks, "field_required")) == 1
    assert len(_of_type(checks, "field_unique")) == 1
    assert _of_type(checks, "field_primary_key_required") == []
    assert _of_type(checks, "field_primary_key_unique") == []


def test_composite_primary_key_is_unique_as_a_tuple():
    """Members of a composite key are not individually unique."""
    checks = _checks(
        SchemaProperty(name="line_no", primaryKey=True, primaryKeyPosition=2),
        SchemaProperty(name="order_id", primaryKey=True, primaryKeyPosition=1),
    )

    # no per-column uniqueness
    assert _of_type(checks, "field_primary_key_unique") == []

    # but every member must still be populated
    assert {c.field for c in _of_type(checks, "field_primary_key_required")} == {"order_id", "line_no"}

    composite = _of_type(checks, "primary_key_unique")
    assert len(composite) == 1
    assert composite[0].field is None
    assert composite[0].metric == MetricType.DUPLICATE_COUNT
    # ordered by primaryKeyPosition, not by declaration order
    assert composite[0].columns == ["order_id", "line_no"]


def test_composite_primary_key_uses_physical_names():
    checks = _checks(
        SchemaProperty(name="order_id", physicalName="ORDER_ID", primaryKey=True, primaryKeyPosition=1),
        SchemaProperty(name="line_no", physicalName="LINE_NO", primaryKey=True, primaryKeyPosition=2),
    )

    composite = _of_type(checks, "primary_key_unique")
    assert composite[0].columns == ["ORDER_ID", "LINE_NO"]


def test_no_primary_key_generates_no_primary_key_checks():
    checks = _checks(SchemaProperty(name="amount", required=True))

    assert _of_type(checks, "field_primary_key_required") == []
    assert _of_type(checks, "field_primary_key_unique") == []
    assert _of_type(checks, "primary_key_unique") == []
