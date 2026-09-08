import logging

import yaml
from open_data_contract_standard.model import (
    OpenDataContractStandard,
    SchemaObject,
    SchemaProperty,
    Server,
    ServiceLevelAgreementProperty,
)

from datacontract.export.sodacl_check_builder import _retention_value_to_seconds, check_property_type, create_checks
from datacontract.export.sodacl_exporter import SodaExporter
from datacontract.lint.resolve import resolve_data_contract_from_location


def test_export_sodacl():
    expected = """
checks for line_items:
  - row_count > 10:
      name: Have at lease 10 line items
checks for orders:
  - schema:
      name: orders__order_id__field_is_present
      fail:
        when required column missing:
          - order_id
  - schema:
      name: orders__order_id__field_type
      fail:
        when wrong column type:
          order_id: string
  - missing_count(order_id) = 0:
      name: orders__order_id__field_required
  - schema:
      name: orders__order_timestamp__field_is_present
      fail:
        when required column missing:
          - order_timestamp
  - schema:
      name: orders__order_timestamp__field_type
      fail:
        when wrong column type:
          order_timestamp: timestamp
  - missing_count(order_timestamp) = 0:
      name: orders__order_timestamp__field_required
  - schema:
      name: orders__processed_timestamp__field_is_present
      fail:
        when required column missing:
          - processed_timestamp
  - schema:
      name: orders__processed_timestamp__field_type
      fail:
        when wrong column type:
          processed_timestamp: timestamp
  - missing_count(processed_timestamp) = 0:
      name: orders__processed_timestamp__field_required
  - schema:
      name: orders__order_total__field_is_present
      fail:
        when required column missing:
          - order_total
  - schema:
      name: orders__order_total__field_type
      fail:
        when wrong column type:
          order_total: integer
  - orders__order_total__quality_sql_0 between 1000 and 49900:
      name: orders__order_total__quality_sql_0
      orders__order_total__quality_sql_0 query: |
        SELECT quantile_cont(order_total, 0.95) AS percentile_95
        FROM orders
  - row_count > 10
  - orders_servicelevel_retention < 31536000:
      name: orders__processed_timestamp__servicelevel_retention
      orders_servicelevel_retention expression: TIMESTAMPDIFF(SECOND, MIN(processed_timestamp), CURRENT_TIMESTAMP)
  - freshness(order_timestamp) < 24h:
      name: orders__order_timestamp__servicelevel_freshness
"""

    data_contract = resolve_data_contract_from_location("./fixtures/sodacl/datacontract.odcs.yaml")

    exporter = SodaExporter(export_format="sodacl")
    result = exporter.export(data_contract, "all", None, "auto", None)

    assert yaml.safe_load(expected) == yaml.safe_load(result)


def test_multiple_servicelevel_promises_get_distinct_check_keys():
    """Each promise needs its own key, matching the engine check path (#1515)."""
    contract = OpenDataContractStandard(
        version="1",
        kind="DataContract",
        apiVersion="v3.1.0",
        id="x",
        schema=[
            SchemaObject(
                name="events",
                properties=[
                    SchemaProperty(name="ts", logicalType="timestamp"),
                    SchemaProperty(name="updated", logicalType="timestamp"),
                ],
            )
        ],
        slaProperties=[
            ServiceLevelAgreementProperty(property="freshness", element="events.ts", value=48, unit="h"),
            ServiceLevelAgreementProperty(property="freshness", element="events.updated", value=2, unit="h"),
            ServiceLevelAgreementProperty(property="retention", element="events.ts", value=1, unit="y"),
            ServiceLevelAgreementProperty(property="retention", element="events.updated", value=2, unit="y"),
        ],
    )

    checks = create_checks(contract, Server(server="s", type="snowflake"))

    freshness_keys = [c.key for c in checks if c.type == "servicelevel_freshness"]
    retention_keys = [c.key for c in checks if c.type == "servicelevel_retention"]
    assert freshness_keys == ["events__ts__servicelevel_freshness", "events__updated__servicelevel_freshness"]
    assert retention_keys == ["events__ts__servicelevel_retention", "events__updated__servicelevel_retention"]


def test_export_sodacl_numeric_retention():
    """Test that numeric retention values with unit (ODCS style) are handled correctly.

    Regression test for https://github.com/datacontract/datacontract-cli/issues/1033
    """
    data_contract = resolve_data_contract_from_location("./fixtures/sodacl/datacontract_numeric_retention.odcs.yaml")

    exporter = SodaExporter(export_format="sodacl")
    result = exporter.export(data_contract, "all", None, "auto", None)
    parsed = yaml.safe_load(result)

    # 3 years in seconds = 3 * 365 * 24 * 60 * 60 = 94608000
    checks = parsed["checks for orders"]
    retention_check = None
    for check in checks:
        for key in check:
            if "servicelevel_retention" in key:
                retention_check = check
                break

    assert retention_check is not None, "Retention check should be generated for numeric value + unit"
    assert any("< 94608000" in str(k) for k in retention_check.keys()), (
        f"Expected retention of 94608000 seconds (3 years), got: {retention_check}"
    )


def test_retention_value_to_seconds_numeric():
    """Test _retention_value_to_seconds with numeric values and various units."""
    assert _retention_value_to_seconds(3, "y") == 3 * 365 * 24 * 60 * 60
    assert _retention_value_to_seconds(3, "years") == 3 * 365 * 24 * 60 * 60
    assert _retention_value_to_seconds(6, "months") == 6 * 30 * 24 * 60 * 60
    assert _retention_value_to_seconds(90, "days") == 90 * 24 * 60 * 60
    assert _retention_value_to_seconds(90, "d") == 90 * 24 * 60 * 60
    assert _retention_value_to_seconds(24, "h") == 24 * 60 * 60
    assert _retention_value_to_seconds(30, "minutes") == 30 * 60
    assert _retention_value_to_seconds(3600, "s") == 3600


def test_retention_value_to_seconds_iso8601():
    """Test _retention_value_to_seconds with ISO 8601 duration strings."""
    assert _retention_value_to_seconds("P1Y", None) == 365 * 24 * 60 * 60
    assert _retention_value_to_seconds("P30D", None) == 30 * 24 * 60 * 60
    assert _retention_value_to_seconds("P6M", None) == 6 * 30 * 24 * 60 * 60
    assert _retention_value_to_seconds("PT24H", None) == 24 * 60 * 60


def test_retention_value_to_seconds_none():
    """Test _retention_value_to_seconds with None value."""
    assert _retention_value_to_seconds(None, None) is None


def test_check_property_type_refuses_none_expected_type(caplog):
    """If expected_type is None, check_property_type should log a warning and return None."""
    with caplog.at_level(logging.WARNING, logger="datacontract.export.sodacl_check_builder"):
        result = check_property_type("model", "field", None)
    assert result is None
    assert any("None" in r.message and "field" in r.message for r in caplog.records)


def test_create_checks_uses_unmapped_physical_type_verbatim(caplog):
    """An unmapped physicalType is used verbatim in the SodaCL check with a warning."""
    contract = OpenDataContractStandard(
        version="1.0.0",
        kind="DataContract",
        apiVersion="v3.1.0",
        id="t",
        name="t",
    )
    schema = SchemaObject(name="m")
    schema.properties = [SchemaProperty(name="f", physicalType="UnknownType", logicalType="string")]
    contract.schema_ = [schema]
    server = Server(server="s", type="databricks")
    with caplog.at_level(logging.WARNING, logger="datacontract.export.sql_type_converter"):
        checks = create_checks(contract, server)
    type_checks = [c for c in checks if c.type == "field_type"]
    assert len(type_checks) == 1, "Type check should be emitted with verbatim physicalType"
    assert "UnknownType" in type_checks[0].implementation
    # Warning logged so users notice the dialect can't translate the type.
    assert any("UnknownType" in r.message for r in caplog.records)
