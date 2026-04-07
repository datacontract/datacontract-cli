import yaml

from datacontract.engines.data_contract_checks import _retention_value_to_seconds
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
      name: servicelevel_retention
      orders_servicelevel_retention expression: TIMESTAMPDIFF(SECOND, MIN(processed_timestamp), CURRENT_TIMESTAMP)
  - freshness(order_timestamp) < 24h:
      name: servicelevel_freshness
"""

    data_contract = resolve_data_contract_from_location("./fixtures/sodacl/datacontract.odcs.yaml")

    exporter = SodaExporter(export_format="sodacl")
    result = exporter.export(data_contract, "all", None, "auto", None)

    assert yaml.safe_load(expected) == yaml.safe_load(result)


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
